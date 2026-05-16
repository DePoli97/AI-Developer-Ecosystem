"""
model_router - heuristic router that picks the right model for the job.

Why this exists:
    Production LLM apps often run the same code path against many models.
    The naive default is "always sonnet"; the right answer is "haiku for
    easy tasks, sonnet for the rest, opus only when complexity demands it".
    This module formalises that decision as a small set of composable
    scorers plus an escalation policy. Drop it in front of any LLM call
    and watch your bill drop without changing your prompts.

Public API:
    Router(tiers, *, scorers, escalator=None)
        .choose(task) -> RouteDecision
        .record_outcome(task, decision, outcome) -> None

    Built-in scorers:
        - length_scorer(weight)
        - keyword_complexity_scorer(keywords, weight)
        - explicit_tier_scorer(weight)

    Built-in escalators:
        - low_confidence_escalator(min_confidence, tier_order)

Dependencies:
    standard library only.

Self-test:
    python model_router.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

# Tier conventions (ordered cheap -> capable). Maps to current Anthropic models;
# replace with whatever you use in your stack.
DEFAULT_TIERS = [
    ("haiku",  "claude-haiku-4-5"),
    ("sonnet", "claude-sonnet-4-6"),
    ("opus",   "claude-opus-4-6"),
]


@dataclass
class Task:
    prompt: str
    explicit_tier: str | None = None        # caller override, e.g. "opus"
    metadata: dict = field(default_factory=dict)


@dataclass
class RouteDecision:
    tier: str
    model: str
    complexity_score: float
    reasons: list[str] = field(default_factory=list)


Scorer = Callable[[Task], tuple[float, str]]
Escalator = Callable[["RouteDecision", "Outcome"], "RouteDecision | None"]


@dataclass
class Outcome:
    ok: bool                   # did the call succeed at the task level
    confidence: float = 1.0    # 0..1, app-defined
    failure_reason: str = ""


# ── Scorers ──────────────────────────────────────────────────────────────────

def length_scorer(weight: float = 1.0) -> Scorer:
    """Longer prompts tend to need more capable models."""
    def _score(task: Task) -> tuple[float, str]:
        words = len(task.prompt.split())
        if words < 50:
            s = 0.0
        elif words < 250:
            s = 0.3
        elif words < 1000:
            s = 0.6
        else:
            s = 1.0
        return s * weight, f"length={words}w -> {s:.2f}"
    return _score


_DEFAULT_HARD_KEYWORDS = (
    "prove", "derive", "rigorously", "step by step", "math", "theorem",
    "complex", "reasoning", "multi-step", "edge case", "ambiguous", "subtle",
    "audit", "deeply", "in detail",
)


def keyword_complexity_scorer(
    keywords: tuple[str, ...] = _DEFAULT_HARD_KEYWORDS,
    weight: float = 1.0,
) -> Scorer:
    """Boost score when prompt mentions complexity-indicating phrases."""
    lowered = tuple(k.lower() for k in keywords)
    def _score(task: Task) -> tuple[float, str]:
        text = task.prompt.lower()
        hits = [k for k in lowered if k in text]
        s = min(1.0, 0.25 * len(hits))
        return s * weight, f"keywords={hits}" if hits else "no complexity keywords"
    return _score


def explicit_tier_scorer(weight: float = 100.0) -> Scorer:
    """
    Lets the caller pin a tier via task.explicit_tier. Returns a huge score
    so it dominates everything else, while still being observable as a reason.
    """
    def _score(task: Task) -> tuple[float, str]:
        if not task.explicit_tier:
            return 0.0, ""
        return weight, f"explicit_tier={task.explicit_tier!r}"
    return _score


# ── Escalators ───────────────────────────────────────────────────────────────

def low_confidence_escalator(
    min_confidence: float,
    tier_order: list[str],
) -> Escalator:
    """If outcome.confidence < min_confidence, escalate to the next tier."""
    def _escalate(decision: RouteDecision, outcome: Outcome) -> RouteDecision | None:
        if outcome.ok and outcome.confidence >= min_confidence:
            return None
        try:
            idx = tier_order.index(decision.tier)
        except ValueError:
            return None
        if idx == len(tier_order) - 1:
            return None
        next_tier = tier_order[idx + 1]
        return RouteDecision(
            tier=next_tier,
            model="(set-by-router)",
            complexity_score=decision.complexity_score,
            reasons=[
                *decision.reasons,
                f"escalated: confidence={outcome.confidence:.2f} < {min_confidence}",
            ],
        )
    return _escalate


# ── Router ───────────────────────────────────────────────────────────────────

class Router:
    def __init__(
        self,
        tiers: list[tuple[str, str]] | None = None,
        *,
        scorers: list[Scorer] | None = None,
        thresholds: tuple[float, float] = (0.4, 0.8),
        escalator: Escalator | None = None,
    ) -> None:
        self._tiers = tiers or DEFAULT_TIERS
        if len(self._tiers) < 2:
            raise ValueError("need at least two tiers (cheap and capable)")
        self._scorers = scorers or [
            length_scorer(),
            keyword_complexity_scorer(),
            explicit_tier_scorer(),
        ]
        self._thresholds = thresholds
        self._escalator = escalator

    def _tier_to_model(self, tier: str) -> str:
        for name, model in self._tiers:
            if name == tier:
                return model
        raise KeyError(tier)

    def _tier_order(self) -> list[str]:
        return [t for t, _ in self._tiers]

    def choose(self, task: Task | str) -> RouteDecision:
        if isinstance(task, str):
            task = Task(prompt=task)

        reasons: list[str] = []
        explicit_tier = task.explicit_tier
        score = 0.0
        for scorer in self._scorers:
            s, why = scorer(task)
            if why:
                reasons.append(why)
            score += s

        if explicit_tier and explicit_tier in self._tier_order():
            tier = explicit_tier
        else:
            low, high = self._thresholds
            order = self._tier_order()
            if score >= high:
                tier = order[-1]
            elif score >= low:
                tier = order[min(1, len(order) - 1)]
            else:
                tier = order[0]

        return RouteDecision(
            tier=tier,
            model=self._tier_to_model(tier),
            complexity_score=round(score, 3),
            reasons=reasons,
        )

    def maybe_escalate(self, decision: RouteDecision, outcome: Outcome) -> RouteDecision:
        if not self._escalator:
            return decision
        new_decision = self._escalator(decision, outcome)
        if new_decision is None:
            return decision
        new_decision.model = self._tier_to_model(new_decision.tier)
        return new_decision


# ── Self-test ────────────────────────────────────────────────────────────────

def _self_test() -> int:
    r = Router()

    # Easy short prompt -> haiku
    d = r.choose("what is 2+2")
    assert d.tier == "haiku", d
    assert d.model == "claude-haiku-4-5", d

    # Mid-length prompt without complexity keywords -> sonnet or haiku
    long_prompt = " ".join(["word"] * 300)
    d = r.choose(long_prompt)
    assert d.tier in {"haiku", "sonnet"}, d

    # Complexity keywords push to sonnet
    d = r.choose(Task(prompt="please derive the formula step by step and reason about edge cases"))
    assert d.tier in {"sonnet", "opus"}, d

    # Very long + complexity -> opus
    long_complex = " ".join(["complex reasoning step by step prove"] * 300)
    d = r.choose(long_complex)
    assert d.tier == "opus", d

    # Explicit tier overrides everything
    d = r.choose(Task(prompt="hello", explicit_tier="opus"))
    assert d.tier == "opus", d
    assert any("explicit_tier" in reason for reason in d.reasons), d

    # Escalation
    r2 = Router(escalator=low_confidence_escalator(0.7, ["haiku", "sonnet", "opus"]))
    initial = r2.choose("simple")
    assert initial.tier == "haiku", initial
    escalated = r2.maybe_escalate(initial, Outcome(ok=True, confidence=0.5))
    assert escalated.tier == "sonnet", escalated
    # And again to opus
    escalated2 = r2.maybe_escalate(escalated, Outcome(ok=True, confidence=0.4))
    assert escalated2.tier == "opus", escalated2
    # Opus is terminal
    escalated3 = r2.maybe_escalate(escalated2, Outcome(ok=False, confidence=0.1))
    assert escalated3.tier == "opus", escalated3

    # No escalation when confident
    stable = r2.maybe_escalate(initial, Outcome(ok=True, confidence=0.95))
    assert stable.tier == "haiku", stable

    print("ok: model_router self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())

"""
cost_budget_guard - enforce a per-process USD budget on LLM calls.

Wires together:
    - snippets/python/token_cost_estimator.py

What it does:
    Wraps any callable that returns an object exposing
    `.usage.input_tokens`, `.usage.output_tokens`, and a `.model`
    attribute (matching the Anthropic SDK Response shape). After each
    call, it converts usage to USD using the embedded price table and
    raises BudgetExceeded if the running total goes over the configured
    cap.

Use it to enforce hard limits in scripts that loop over many items, where
a runaway prompt could easily 10x the bill.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).parent
SNIPPETS = HERE.parent / "snippets" / "python"
sys.path.insert(0, str(SNIPPETS))

from token_cost_estimator import estimate_from_tokens  # type: ignore


class BudgetExceeded(Exception):
    pass


@dataclass
class BudgetState:
    spent_usd: float = 0.0
    call_count: int = 0
    cap_usd: float = 0.0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd)


class CostBudgetGuard:
    def __init__(self, cap_usd: float) -> None:
        if cap_usd < 0:
            raise ValueError("cap_usd must be >= 0")
        self.state = BudgetState(cap_usd=cap_usd)

    def call(self, fn: Callable[[], Any]) -> Any:
        if self.state.spent_usd >= self.state.cap_usd:
            raise BudgetExceeded(
                f"budget already at ${self.state.spent_usd:.4f} of "
                f"${self.state.cap_usd:.4f} before call"
            )
        response = fn()
        model = getattr(response, "model", None) or "unknown"
        usage = getattr(response, "usage", None)
        in_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        out_tokens = int(getattr(usage, "output_tokens", 0) or 0)

        estimate = estimate_from_tokens(model, in_tokens, out_tokens)
        cost = estimate.total_usd if estimate.total_usd == estimate.total_usd else 0.0
        self.state.spent_usd += cost
        self.state.call_count += 1
        if self.state.spent_usd > self.state.cap_usd:
            raise BudgetExceeded(
                f"budget exceeded: ${self.state.spent_usd:.4f} > "
                f"${self.state.cap_usd:.4f} after {self.state.call_count} calls"
            )
        return response


def _cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return _self_test()
    print("usage: import CostBudgetGuard from this module; see --self-test")
    return 0


def _self_test() -> int:
    class FakeUsage:
        def __init__(self, i: int, o: int) -> None:
            self.input_tokens = i
            self.output_tokens = o

    class FakeResp:
        def __init__(self, model: str, i: int, o: int) -> None:
            self.model = model
            self.usage = FakeUsage(i, o)

    # Sonnet pricing is roughly $3/M input, $15/M output.
    # 100k input + 50k output ≈ 0.30 + 0.75 = $1.05
    guard = CostBudgetGuard(cap_usd=2.50)
    r1 = guard.call(lambda: FakeResp("claude-sonnet-4-6", 100_000, 50_000))
    assert r1.model == "claude-sonnet-4-6"
    assert guard.state.call_count == 1
    assert 1.0 < guard.state.spent_usd < 1.1, guard.state.spent_usd

    # Second call brings us to ~$2.10, still under cap
    guard.call(lambda: FakeResp("claude-sonnet-4-6", 100_000, 50_000))
    assert guard.state.call_count == 2

    # Third call should push over $3 cap of $2.50
    try:
        guard.call(lambda: FakeResp("claude-sonnet-4-6", 100_000, 50_000))
    except BudgetExceeded as exc:
        assert "exceeded" in str(exc), str(exc)
    else:
        raise AssertionError("expected BudgetExceeded")

    # Once exceeded, the next call is rejected pre-flight
    try:
        guard.call(lambda: FakeResp("claude-sonnet-4-6", 1, 1))
    except BudgetExceeded:
        pass
    else:
        raise AssertionError("expected pre-flight BudgetExceeded")

    # Unknown model: zero cost added (estimate is NaN -> defaults to 0)
    g2 = CostBudgetGuard(cap_usd=1.00)
    g2.call(lambda: FakeResp("claude-future-z", 50_000, 50_000))
    assert g2.state.spent_usd == 0.0

    print("ok: cost_budget_guard self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

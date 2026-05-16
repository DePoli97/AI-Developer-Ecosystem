"""
eval_on_commit - run the minimal eval harness against a prompt registry.

Wires together:
    - snippets/python/minimal_eval_harness.py
    - a tiny in-memory prompt registry to demonstrate the pattern

How to use this in practice:
    1. Keep your prompts as .txt files in a `prompts/` directory.
    2. Keep golden examples in `prompts/golden.json`.
    3. Call this script from a pre-commit hook or GitHub Actions step.
    4. The script exits non-zero on any failed case, blocking the commit.

Self-test runs offline with a fake generate() function.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).parent
SNIPPETS = HERE.parent / "snippets" / "python"
sys.path.insert(0, str(SNIPPETS))

from minimal_eval_harness import (  # type: ignore
    EvalCase, check_contains, check_max_length, check_regex,
    print_report, run_eval,
)


# A tiny "prompt registry" for the demo. In a real repo this loads from disk.
PROMPTS = {
    "summarise_v1": (
        "Summarise the following text in one sentence. Text: {text}"
    ),
    "classify_v1": (
        "Classify the sentiment of this review as positive, negative, or "
        "neutral, returning only the label. Review: {text}"
    ),
}


GOLDEN = [
    {
        "prompt": "summarise_v1",
        "input": {"text": "The new release adds a CLI and three bug fixes."},
        "checks": [
            ("contains", "release"),
            ("max_length", 200),
        ],
    },
    {
        "prompt": "classify_v1",
        "input": {"text": "I love this product. It changed how I work."},
        "checks": [
            ("regex", r"\bpositive\b"),
        ],
    },
    {
        "prompt": "classify_v1",
        "input": {"text": "Terrible. Broke on day one and the support never replied."},
        "checks": [
            ("regex", r"\bnegative\b"),
        ],
    },
]


def _build_checks(spec: list[tuple]) -> list:
    out = []
    for kind, arg in spec:
        if kind == "contains": out.append(check_contains(arg))
        elif kind == "regex": out.append(check_regex(arg))
        elif kind == "max_length": out.append(check_max_length(arg))
        else: raise ValueError(f"unknown check kind: {kind}")
    return out


def build_cases(golden: list[dict]) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for g in golden:
        prompt_tmpl = PROMPTS[g["prompt"]]
        rendered = prompt_tmpl.format(**g["input"])
        cases.append(EvalCase(
            name=f"{g['prompt']}::{g['input'].get('text', '')[:30]}",
            input=rendered,
            checks=_build_checks(g["checks"]),
            tags=[g["prompt"]],
        ))
    return cases


def make_fake_generator():
    """Deterministic fake LLM. Replace with a real client in production."""
    async def generate(text: str) -> str:
        t = text.lower()
        if "summarise" in t:
            return "The release adds a CLI and ships three bug fixes for users."
        if "sentiment" in t:
            if "love" in t or "great" in t: return "positive"
            if "terrible" in t or "broke" in t: return "negative"
            return "neutral"
        return "?"
    return generate


def _cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        return _self_test()

    cases = build_cases(GOLDEN)
    results = run_eval(cases, make_fake_generator())
    return print_report(results)


def _self_test() -> int:
    cases = build_cases(GOLDEN)
    assert len(cases) == 3
    results = run_eval(cases, make_fake_generator())
    assert all(r.ok for r in results), [r.name for r in results if not r.ok]

    # Introduce a regression: replace the generator to produce wrong outputs
    async def broken(text: str) -> str:
        return "I have no idea"
    bad = run_eval(cases, broken)
    assert not all(r.ok for r in bad), "expected at least one failure"

    print("ok: eval_on_commit self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

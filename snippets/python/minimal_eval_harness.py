"""
Minimal eval harness - catch prompt regressions in under 100 lines.

Why this exists:
    Real eval frameworks (Inspect, Promptfoo, LangSmith, OpenAI Evals) are
    great when you have hundreds of cases and a team. For a single
    developer who wants to lock in "the prompt currently solves these
    twelve cases correctly", you want something that fits on one screen
    and runs in CI without buying anything.

    This module is that thing. It supports:
      - test cases declared in plain Python
      - composable checks (exact match, substring, regex, predicate)
      - a single async runner that calls your generate() function
      - a structured report with pass/fail counts and per-case diffs
      - non-zero exit code on failure so it slots into CI

Public API:
    @dataclass class EvalCase
    @dataclass class EvalResult
    check_*(...)              -> Callable[[str], CheckOutcome]
    run_eval(cases, generate) -> list[EvalResult]
    print_report(results)     -> int   # returns exit code

Dependencies:
    standard library only.
"""

from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

Check = Callable[[str], "CheckOutcome"]


@dataclass
class CheckOutcome:
    ok: bool
    message: str = ""


@dataclass
class EvalCase:
    name: str
    input: str
    checks: list[Check]
    tags: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    name: str
    output: str
    outcomes: list[CheckOutcome]

    @property
    def ok(self) -> bool:
        return all(o.ok for o in self.outcomes)


# ── Composable checks ────────────────────────────────────────────────────────

def check_exact(expected: str) -> Check:
    def _check(output: str) -> CheckOutcome:
        return CheckOutcome(
            ok=output.strip() == expected.strip(),
            message=f"expected exact {expected!r}, got {output[:80]!r}",
        )
    return _check


def check_contains(substring: str) -> Check:
    def _check(output: str) -> CheckOutcome:
        return CheckOutcome(
            ok=substring.lower() in output.lower(),
            message=f"missing substring {substring!r}",
        )
    return _check


def check_regex(pattern: str, flags: int = re.IGNORECASE) -> Check:
    rx = re.compile(pattern, flags)
    def _check(output: str) -> CheckOutcome:
        return CheckOutcome(
            ok=bool(rx.search(output)),
            message=f"regex {pattern!r} did not match",
        )
    return _check


def check_predicate(predicate: Callable[[str], bool], label: str) -> Check:
    def _check(output: str) -> CheckOutcome:
        return CheckOutcome(
            ok=bool(predicate(output)),
            message=f"predicate failed: {label}",
        )
    return _check


def check_max_length(max_chars: int) -> Check:
    def _check(output: str) -> CheckOutcome:
        return CheckOutcome(
            ok=len(output) <= max_chars,
            message=f"output {len(output)} chars exceeds limit {max_chars}",
        )
    return _check


# ── Runner ───────────────────────────────────────────────────────────────────

async def _run_one(case: EvalCase, generate: Callable[[str], Awaitable[str]]) -> EvalResult:
    output = await generate(case.input)
    outcomes = [chk(output) for chk in case.checks]
    return EvalResult(name=case.name, output=output, outcomes=outcomes)


async def _run_all(cases: list[EvalCase], generate: Callable[[str], Awaitable[str]]) -> list[EvalResult]:
    return await asyncio.gather(*(_run_one(c, generate) for c in cases))


def run_eval(cases: list[EvalCase], generate: Callable[[str], Awaitable[str]]) -> list[EvalResult]:
    return asyncio.run(_run_all(cases, generate))


def print_report(results: list[EvalResult]) -> int:
    passed = sum(1 for r in results if r.ok)
    total = len(results)
    print(f"\nEval report: {passed}/{total} passed\n")
    for r in results:
        marker = "PASS" if r.ok else "FAIL"
        print(f"  [{marker}] {r.name}")
        if not r.ok:
            for outcome in r.outcomes:
                if not outcome.ok:
                    print(f"         - {outcome.message}")
    return 0 if passed == total else 1


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def fake_generate(text: str) -> str:
        if "capital of France" in text:
            return "The capital of France is Paris."
        if "two plus two" in text:
            return "Four."
        return "I do not know."

    cases = [
        EvalCase(
            name="france_capital",
            input="What is the capital of France?",
            checks=[check_contains("Paris"), check_max_length(80)],
        ),
        EvalCase(
            name="math",
            input="What is two plus two?",
            checks=[check_regex(r"\bfour\b"), check_max_length(20)],
        ),
        EvalCase(
            name="format_test",
            input="What is the capital of France?",
            checks=[check_predicate(lambda s: s.endswith("."), "ends with period")],
        ),
    ]

    results = run_eval(cases, fake_generate)
    sys.exit(print_report(results))

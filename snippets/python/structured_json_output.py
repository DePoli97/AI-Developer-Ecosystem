"""
Robust structured-JSON output extraction for LLM responses.

LLMs frequently emit JSON wrapped in prose, fenced in ```json blocks, with
trailing commas, single quotes, or smart quotes. This module turns that mess
into a validated pydantic model with one call, and gives you a precise reason
when it cannot.

Why this snippet exists:
    Every real agent pipeline ends up writing this. The naive `json.loads`
    on the whole response fails on the first stray sentence; greedy regex
    `\\{.*\\}` matches break on nested objects. The function below walks the
    text with a brace counter so it works on nested structures, then runs a
    small repair pass before validating against a schema.

Requires:
    pip install pydantic>=2.7

Public API:
    extract_json(text)              -> dict | list
    parse_structured(text, Model)   -> Model
    StructuredParseError            -> raised on any failure with .reason

Run the file directly for a self-test:
    python structured_json_output.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)


class StructuredParseError(ValueError):
    """Raised when an LLM response cannot be parsed into the expected shape."""

    def __init__(self, reason: str, raw: str, snippet: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.raw = raw
        self.snippet = snippet


@dataclass(frozen=True)
class _Candidate:
    text: str
    start: int
    end: int


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if they wrap the response."""
    fence = re.search(r"```(?:json|JSON)?\s*\n?(.*?)```", text, flags=re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def _find_json_candidates(text: str) -> list[_Candidate]:
    """Walk the string and return every balanced {...} or [...] region.

    A brace counter is used so nested structures are preserved. Strings and
    escaped quotes are tracked so braces inside string literals don't confuse
    the count.
    """
    candidates: list[_Candidate] = []
    stack: list[tuple[str, int]] = []
    in_string = False
    escape = False
    string_quote = ""

    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == string_quote:
                in_string = False
            continue

        if ch in ('"', "'"):
            in_string = True
            string_quote = ch
            continue

        if ch in "{[":
            stack.append((ch, i))
        elif ch in "}]":
            if not stack:
                continue
            opener, start = stack.pop()
            if (opener, ch) not in (("{", "}"), ("[", "]")):
                continue
            if not stack:
                candidates.append(_Candidate(text=text[start : i + 1], start=start, end=i + 1))

    # Sort by size descending so the largest balanced block wins ties.
    candidates.sort(key=lambda c: -(c.end - c.start))
    return candidates


def _repair(json_text: str) -> str:
    """Apply small, safe repairs that LLMs commonly need.

    - Replace smart quotes with straight quotes.
    - Remove trailing commas before } or ].
    - Convert single-quoted keys/strings to double-quoted (best-effort, only
      when no double quotes are already present in the candidate).
    """
    fixed = (
        json_text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )
    fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)

    if '"' not in fixed and "'" in fixed:
        fixed = fixed.replace("'", '"')

    return fixed


def extract_json(text: str) -> Any:
    """Find and parse the first valid JSON object or array inside ``text``.

    The function tries, in order:
      1. parse the whole string;
      2. strip a single ```json fence and parse that;
      3. walk the string for balanced braces, try each candidate largest-first,
         applying a small repair pass before each attempt.

    Raises StructuredParseError if nothing parses.
    """
    if not text or not text.strip():
        raise StructuredParseError("empty input", raw=text)

    # 1) try the raw payload
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) try after stripping fences
    fenced = _strip_code_fences(text)
    if fenced != text:
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass

    # 3) walk for balanced regions
    haystack = fenced
    last_error: str | None = None
    for cand in _find_json_candidates(haystack):
        try:
            return json.loads(cand.text)
        except json.JSONDecodeError as e:
            last_error = str(e)
        try:
            return json.loads(_repair(cand.text))
        except json.JSONDecodeError as e:
            last_error = str(e)

    raise StructuredParseError(
        f"no valid JSON found ({last_error or 'no candidates'})",
        raw=text,
        snippet=haystack[:200],
    )


def parse_structured(text: str, model: Type[M]) -> M:
    """Extract JSON and validate it against a pydantic model.

    Example:
        class Plan(BaseModel):
            steps: list[str]
            confidence: float

        plan = parse_structured(llm_response, Plan)
    """
    data = extract_json(text)
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise StructuredParseError(
            f"schema validation failed: {e.errors(include_url=False)[:3]}",
            raw=text,
        ) from e


# ---------------------------------------------------------------------------
# Self-test. Run this file directly to confirm the snippet still passes.
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    class _Plan(BaseModel):
        steps: list[str]
        confidence: float

    cases: list[tuple[str, str]] = [
        (
            "fenced",
            'Sure, here is the plan:\n```json\n{"steps": ["a", "b"], "confidence": 0.9}\n```\nLet me know.',
        ),
        (
            "trailing prose",
            '{"steps": ["a", "b"], "confidence": 0.9}\nThanks!',
        ),
        (
            "trailing comma",
            '{"steps": ["a", "b",], "confidence": 0.9,}',
        ),
        (
            "smart quotes",
            "“steps”: [“a”], “confidence”: 0.5".join(("{", "}")),
        ),
        (
            "nested object",
            'noise {"steps": ["a {nested: true}", "b"], "confidence": 0.42} noise',
        ),
    ]

    failures = 0
    for name, payload in cases:
        try:
            plan = parse_structured(payload, _Plan)
            print(f"PASS  {name:14s}  steps={plan.steps}  confidence={plan.confidence}")
        except StructuredParseError as e:
            failures += 1
            print(f"FAIL  {name:14s}  {e.reason}")

    bad = "this response forgot to include any JSON at all"
    try:
        parse_structured(bad, _Plan)
        failures += 1
        print("FAIL  no-json        should have raised")
    except StructuredParseError:
        print("PASS  no-json        raised as expected")

    raise SystemExit(0 if failures == 0 else 1)

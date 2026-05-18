"""
PII redactor with reversible tokenisation - safer LLM prompts.

A practical, dependency-free PII redactor for LLM pipelines. Detects and
replaces emails, phone numbers, IPv4 addresses, US SSNs, credit-card
numbers (Luhn-validated), and AWS access-key IDs with stable placeholder
tokens. Stores a session-scoped mapping so the placeholders can be
reversed in the model's response before it reaches the user.

Why this exists:
    Most teams shipping LLM features need a redaction step long before
    they need a managed DLP service. This snippet is the "good enough
    for a side project, audited for an audit" middle ground - small,
    readable, and easy to extend with custom patterns.

Public API:
    Redactor()
        .redact(text)            -> RedactionResult(redacted, mapping)
        .unredact(text, mapping) -> str
    detect(text)                 -> list[Match]

CLI:
    python pii_redactor.py --self-test
    python pii_redactor.py --redact   < input.txt > redacted.txt
    python pii_redactor.py --unredact mapping.json < model_output.txt

Dependencies:
    Standard library only.

License:
    MIT (see repository LICENSE).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


# -- Detection ---------------------------------------------------------------

# Patterns are ordered so that more specific patterns run before more general
# ones. For example, credit-card numbers must match before generic digit
# sequences would otherwise overlap.
_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "AWS_ACCESS_KEY",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
    (
        "SSN_US",
        # Avoids obvious test SSNs like 000-XX-XXXX and 666-XX-XXXX
        re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
    ),
    (
        "CREDIT_CARD",
        # 13-19 digits, allowing single spaces or single dashes as separators.
        re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
    ),
    (
        "PHONE",
        # E.164-ish and common US/EU forms. Deliberately permissive; the
        # cost of a false positive here is low (a number gets redacted)
        # and the cost of a false negative is high (a phone leaks).
        re.compile(
            r"(?<!\d)"
            r"(?:\+?\d{1,3}[\s.-]?)?"
            r"(?:\(?\d{2,4}\)?[\s.-]?)?"
            r"\d{3,4}[\s.-]?\d{3,4}"
            r"(?!\d)"
        ),
    ),
    (
        "IPV4",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d?\d)\b"
        ),
    ),
]


@dataclass(frozen=True)
class Match:
    """A single PII match found in the input text."""

    kind: str
    start: int
    end: int
    value: str


def _luhn_ok(digits: str) -> bool:
    """Return True if a digit string passes the Luhn check."""
    only = [int(c) for c in digits if c.isdigit()]
    if len(only) < 13:
        return False
    s = 0
    parity = len(only) % 2
    for i, d in enumerate(only):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    return s % 10 == 0


def detect(text: str) -> list[Match]:
    """Find non-overlapping PII matches, longest-first to avoid clashes."""
    raw: list[Match] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(0)
            if kind == "CREDIT_CARD" and not _luhn_ok(value):
                continue
            if kind == "PHONE":
                # Need at least 7 digits to count as a real phone number
                if sum(c.isdigit() for c in value) < 7:
                    continue
                # Reject pure IPv4 dotted form (rare overlap, but cheap to check)
                if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value):
                    continue
                # Reject if the phone match is part of a longer digit-with-separators run
                # (typical of credit-card-style numbers that failed Luhn validation).
                left_ctx = text[max(0, m.start() - 8):m.start()]
                right_ctx = text[m.end():m.end() + 8]
                if re.search(r"\d[\s.-]?$", left_ctx) or re.search(r"^[\s.-]?\d", right_ctx):
                    continue
            raw.append(Match(kind=kind, start=m.start(), end=m.end(), value=value))

    # Resolve overlaps: prefer the longer match, then the earlier match.
    raw.sort(key=lambda m: (-(m.end - m.start), m.start))
    accepted: list[Match] = []
    for m in raw:
        if any(not (m.end <= a.start or m.start >= a.end) for a in accepted):
            continue
        accepted.append(m)
    accepted.sort(key=lambda m: m.start)
    return accepted


# -- Redaction ---------------------------------------------------------------


@dataclass
class RedactionResult:
    """Output of a single redact() call."""

    redacted: str
    mapping: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.mapping, indent=2, sort_keys=True)


class Redactor:
    """Stateful redactor that reuses placeholders across calls.

    Reuse matters when a long conversation references the same email or
    phone many times - you want stable placeholders so the model can
    reason about them consistently.
    """

    def __init__(self) -> None:
        self._value_to_token: dict = {}
        self._counters: dict = {}

    def _token_for(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key in self._value_to_token:
            return self._value_to_token[key]
        n = self._counters.get(kind, 0) + 1
        self._counters[kind] = n
        token = f"<{kind}_{n}>"
        self._value_to_token[key] = token
        return token

    def redact(self, text: str) -> RedactionResult:
        matches = detect(text)
        out: list = []
        cursor = 0
        mapping: dict = {}
        for m in matches:
            out.append(text[cursor:m.start])
            token = self._token_for(m.kind, m.value)
            out.append(token)
            mapping[token] = m.value
            cursor = m.end
        out.append(text[cursor:])
        return RedactionResult(redacted="".join(out), mapping=mapping)

    @staticmethod
    def unredact(text: str, mapping: dict) -> str:
        # Replace longest tokens first so prefixes never partially match.
        for token in sorted(mapping, key=len, reverse=True):
            text = text.replace(token, mapping[token])
        return text


# -- CLI ---------------------------------------------------------------------


def _cli(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true", help="run the offline self-test")
    g.add_argument("--redact", action="store_true", help="redact stdin, print to stdout")
    g.add_argument("--unredact", metavar="MAPPING_JSON", help="reverse a redaction using a JSON mapping file")
    parser.add_argument("--mapping-out", metavar="PATH", help="when redacting, write the mapping to this file (default stderr)")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if args.redact:
        text = sys.stdin.read()
        result = Redactor().redact(text)
        sys.stdout.write(result.redacted)
        if args.mapping_out:
            with open(args.mapping_out, "w", encoding="utf-8") as f:
                f.write(result.to_json())
        else:
            sys.stderr.write(result.to_json())
        return 0

    if args.unredact:
        with open(args.unredact, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        text = sys.stdin.read()
        sys.stdout.write(Redactor.unredact(text, mapping))
        return 0

    return 2


# -- Self-test ---------------------------------------------------------------


def _self_test() -> int:
    cases = [
        (
            "Contact alice@example.com or call +1 (415) 555-2671.",
            {"EMAIL": 1, "PHONE": 1},
        ),
        (
            "Server at 10.0.0.42 is down. Reach me at bob@corp.io.",
            {"IPV4": 1, "EMAIL": 1},
        ),
        (
            # Valid Luhn test number from common payment-test data sets
            "Card 4111 1111 1111 1111 expires soon.",
            {"CREDIT_CARD": 1},
        ),
        (
            # Invalid Luhn - must not be redacted
            "Order id 1234 5678 9012 3456 is internal.",
            {},
        ),
        (
            "SSN 123-45-6789 for Jane Doe.",
            {"SSN_US": 1},
        ),
        (
            "Leaked key AKIAIOSFODNN7EXAMPLE found in repo.",
            {"AWS_ACCESS_KEY": 1},
        ),
    ]

    failures = 0
    for i, (text, expected_counts) in enumerate(cases, 1):
        result = Redactor().redact(text)
        got_counts = {}
        for kind in {k for k, _ in _PATTERNS}:
            n = sum(1 for tok in result.mapping if tok.startswith(f"<{kind}_"))
            if n:
                got_counts[kind] = n
        if got_counts != expected_counts:
            failures += 1
            print(f"case {i} FAIL")
            print(f"  text     : {text!r}")
            print(f"  expected : {expected_counts}")
            print(f"  got      : {got_counts}")
            print(f"  redacted : {result.redacted!r}")
        else:
            print(f"case {i} ok ({sum(expected_counts.values())} matches)")

    # Reversibility check
    r = Redactor()
    src = "Email me at a@b.io about ticket 123-45-6789."
    redacted = r.redact(src)
    back = Redactor.unredact(redacted.redacted, redacted.mapping)
    if back != src:
        failures += 1
        print(f"reversibility FAIL\n  src : {src!r}\n  back: {back!r}")
    else:
        print("reversibility ok")

    # Stable placeholders across calls on the same Redactor
    r2 = Redactor()
    a = r2.redact("ping alice@example.com twice")
    b = r2.redact("again alice@example.com here")
    token_a = next(iter(a.mapping))
    token_b = next(iter(b.mapping))
    if token_a != token_b:
        failures += 1
        print(f"stability FAIL: {token_a} != {token_b}")
    else:
        print(f"stability ok ({token_a})")

    if failures:
        print(f"\n{failures} failure(s)")
        return 1
    print(f"\nall {len(cases) + 2} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))

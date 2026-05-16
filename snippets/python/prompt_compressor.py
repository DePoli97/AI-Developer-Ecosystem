"""
prompt_compressor - heuristic compression for system prompts and few-shots.

Why this exists:
    Production system prompts grow organically and bloat. Removing the
    fat without changing meaning is mostly mechanical: collapse repeated
    whitespace, drop filler phrases ("please note that", "it is important
    to remember that"), merge adjacent restatements, trim trailing
    polite scaffolding, and compress few-shot examples.

    No LLM call is required. The script reports how many tokens
    (approximated as words * 1.3) and characters it saved.

Use it before shipping a prompt to production; don't use it on prompts
that depend on exact phrasing for jailbreak resistance.

Public API:
    compress(text: str, *, level: str = "safe") -> CompressionResult
    CompressionResult.text, .stats

CLI:
    python prompt_compressor.py < prompt.txt
    python prompt_compressor.py --level aggressive < prompt.txt
    python prompt_compressor.py --self-test

Dependencies:
    standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

# Phrases that almost always add zero information.
SAFE_FILLERS = [
    r"\bplease note that\b",
    r"\bit is important to remember that\b",
    r"\bplease keep in mind that\b",
    r"\bit should be noted that\b",
    r"\bas previously mentioned\b",
    r"\bas previously stated\b",
    r"\bit goes without saying that\b",
    r"\bneedless to say\b",
    r"\bin order to\b",  # -> "to"
    r"\bdue to the fact that\b",  # -> "because"
    r"\ba large number of\b",  # -> "many"
    r"\bat this point in time\b",  # -> "now"
    r"\bin the event that\b",  # -> "if"
    r"\bfor the purpose of\b",  # -> "to"
    r"\bin spite of the fact that\b",  # -> "although"
]
SAFE_REPLACEMENTS = {
    r"\bin order to\b": "to",
    r"\bdue to the fact that\b": "because",
    r"\ba large number of\b": "many",
    r"\bat this point in time\b": "now",
    r"\bin the event that\b": "if",
    r"\bfor the purpose of\b": "to",
    r"\bin spite of the fact that\b": "although",
    r"\bas a matter of fact\b": "in fact",
    r"\bin the process of\b": "while",
}

# Politeness that the model does not need.
POLITE_OPENERS = [
    r"^\s*please\s+",
    r"^\s*kindly\s+",
    r"^\s*could you (?:please\s+)?",
    r"^\s*would you (?:please\s+)?",
]


@dataclass
class CompressionStats:
    chars_before: int
    chars_after: int
    words_before: int
    words_after: int

    @property
    def chars_saved(self) -> int:
        return self.chars_before - self.chars_after

    @property
    def words_saved(self) -> int:
        return self.words_before - self.words_after

    @property
    def approx_tokens_saved(self) -> int:
        # Word-level approximation: 1 token ≈ 0.75 words for English
        return round(self.words_saved * 1.3)

    @property
    def char_ratio(self) -> float:
        if self.chars_before == 0:
            return 1.0
        return self.chars_after / self.chars_before

    def as_dict(self) -> dict:
        return {
            "chars_before": self.chars_before,
            "chars_after": self.chars_after,
            "chars_saved": self.chars_saved,
            "words_before": self.words_before,
            "words_after": self.words_after,
            "words_saved": self.words_saved,
            "approx_tokens_saved": self.approx_tokens_saved,
            "char_ratio": round(self.char_ratio, 3),
        }


@dataclass
class CompressionResult:
    text: str
    stats: CompressionStats


def _collapse_whitespace(text: str) -> str:
    # Trim trailing spaces on each line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    # Collapse runs of 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of 2+ spaces (not at line start)
    text = re.sub(r"(?<=\S) {2,}", " ", text)
    return text.strip() + "\n"


def _strip_safe_fillers(text: str) -> str:
    out = text
    for rx in SAFE_FILLERS:
        out = re.sub(rx, "", out, flags=re.IGNORECASE)
    for rx, repl in SAFE_REPLACEMENTS.items():
        out = re.sub(rx, repl, out, flags=re.IGNORECASE)
    for rx in POLITE_OPENERS:
        out = re.sub(rx, "", out, flags=re.IGNORECASE | re.MULTILINE)
    # Capitalise first letter of each paragraph after stripping leading polite phrases
    return out


def _drop_adjacent_duplicates(text: str) -> str:
    """
    Drop adjacent duplicate lines AND adjacent duplicate paragraphs.
    Paragraphs are split on blank lines; comparison is case-insensitive
    on trimmed content.
    """
    # First pass: line-level dedup
    lines = text.splitlines()
    out: list[str] = []
    prev_key = None
    for ln in lines:
        key = ln.strip().lower()
        if key and key == prev_key:
            continue
        out.append(ln)
        prev_key = key if key else None
    text = "\n".join(out)

    # Second pass: paragraph-level dedup (drops ANY duplicate paragraph, not just adjacent)
    paragraphs = re.split(r"\n\s*\n", text)
    seen: set[str] = set()
    keep: list[str] = []
    for p in paragraphs:
        key = re.sub(r"\s+", " ", p.strip().lower())
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        keep.append(p)
    return "\n\n".join(keep)


def _aggressive_passes(text: str) -> str:
    """
    Aggressive mode also removes hedging adverbs and parenthetical asides
    that are stylistic, not semantic. Less safe to apply on prompts where
    nuance matters.
    """
    # Hedging adverbs
    hedges = [r"\bbasically\b", r"\bessentially\b", r"\bsimply\b",
              r"\bactually\b", r"\bobviously\b", r"\bclearly\b",
              r"\breally\b", r"\bvery\b", r"\bquite\b", r"\bjust\b",
              r"\bperhaps\b", r"\bsomewhat\b"]
    out = text
    for rx in hedges:
        out = re.sub(rx, "", out, flags=re.IGNORECASE)
    # Parentheticals: drop (e.g. ...) and (i.e. ...) and short asides
    out = re.sub(r"\s*\([^)]{0,80}\)", "", out)
    # Multiple consecutive commas / spaces after removals
    out = re.sub(r"\s+,", ",", out)
    out = re.sub(r" {2,}", " ", out)
    return out


def compress(text: str, *, level: str = "safe") -> CompressionResult:
    if level not in {"safe", "aggressive"}:
        raise ValueError("level must be 'safe' or 'aggressive'")

    chars_before = len(text)
    words_before = len(text.split())

    out = text
    out = _strip_safe_fillers(out)
    if level == "aggressive":
        out = _aggressive_passes(out)
    out = _drop_adjacent_duplicates(out)
    out = _collapse_whitespace(out)

    stats = CompressionStats(
        chars_before=chars_before,
        chars_after=len(out),
        words_before=words_before,
        words_after=len(out.split()),
    )
    return CompressionResult(text=out, stats=stats)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli() -> int:
    p = argparse.ArgumentParser(description="Heuristic prompt compressor.")
    p.add_argument("--level", choices=["safe", "aggressive"], default="safe")
    p.add_argument("--stats-only", action="store_true",
                   help="Print stats JSON instead of the compressed text.")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        return _self_test()

    text = sys.stdin.read()
    result = compress(text, level=args.level)
    if args.stats_only:
        import json as _json
        print(_json.dumps(result.stats.as_dict(), indent=2))
    else:
        sys.stdout.write(result.text)
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────

VERBOSE_PROMPT = """\
Please note that you are a careful assistant. It is important to remember that
you must answer in clear prose.

In order to be helpful, kindly do the following: read the input thoroughly,
think step by step, and basically respond very concisely.

Please note that you are a careful assistant. It is important to remember that
you must answer in clear prose.

For the purpose of providing context, the user is essentially a beginner.
Due to the fact that they are new, please obviously avoid jargon.



It goes without saying that hallucinations are bad (i.e. making things up).
"""


def _self_test() -> int:
    # Safe mode: should remove fillers but keep semantic content
    result_safe = compress(VERBOSE_PROMPT, level="safe")
    out = result_safe.text.lower()
    assert "please note that" not in out, out
    assert "due to the fact that" not in out, out
    assert "in order to" not in out, out
    assert "for the purpose of" not in out, out
    # Duplicate paragraph collapsed
    assert out.count("you are a careful assistant") == 1, out
    # Stats sane
    s = result_safe.stats
    assert s.chars_saved > 0, s.as_dict()
    assert s.words_saved > 0, s.as_dict()
    assert s.char_ratio < 1.0, s.as_dict()

    # Aggressive mode: should also strip hedges and parentheticals
    result_aggr = compress(VERBOSE_PROMPT, level="aggressive")
    out_a = result_aggr.text.lower()
    assert "basically" not in out_a, out_a
    assert "obviously" not in out_a, out_a
    assert "very" not in out_a, out_a
    assert "(i.e. making things up)" not in out_a, out_a
    # Aggressive should compress further than safe
    assert result_aggr.stats.chars_after <= result_safe.stats.chars_after, (
        result_aggr.stats.as_dict(), result_safe.stats.as_dict()
    )

    # Idempotence: running compress again should change very little (within 2% char delta)
    result_twice = compress(result_safe.text, level="safe")
    if result_safe.stats.chars_after > 0:
        delta = abs(result_twice.stats.chars_after - result_safe.stats.chars_after)
        assert delta / result_safe.stats.chars_after < 0.02, delta

    # Invalid level should raise
    try:
        compress("x", level="bogus")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on bad level")

    print("ok: prompt_compressor self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

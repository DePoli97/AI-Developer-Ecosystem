"""
Prompt cache analyzer for Anthropic responses.

Why this exists:
    Anthropic's prompt-cache pricing is a meaningful cost lever, but the
    only way to know whether you are actually using it is to look at the
    `usage` object on each response and aggregate. This script does that.
    Feed it a JSONL log produced by your application (one record per API
    call, containing at minimum the usage fields), and it prints a cache
    hit-ratio report with USD savings vs. the no-cache baseline.

Expected input format (JSONL):
    Each line is a JSON object with these fields at minimum:
        - model:                     str
        - input_tokens:              int
        - output_tokens:             int
        - cache_creation_input_tokens: int  (optional; defaults to 0)
        - cache_read_input_tokens:   int  (optional; defaults to 0)
        - ts:                        ISO timestamp (optional)

    These are the standard fields returned by anthropic.Messages.create().
    You can produce such a log with snippets/python/streaming_response_logger.py
    extended to include the two cache fields.

Public API:
    analyze(records: Iterable[dict]) -> Report
    Report.as_text() -> str
    Report.as_dict() -> dict

CLI:
    python prompt_cache_analyzer.py --log llm.jsonl
    python prompt_cache_analyzer.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

# Prices per 1M tokens (USD). Update when Anthropic reprices.
# Cache write is 1.25x input; cache read is 0.1x input.
INPUT_PRICES = {
    "claude-opus-4-6":   15.00,
    "claude-sonnet-4-6":  3.00,
    "claude-haiku-4-5":   0.80,
}
OUTPUT_PRICES = {
    "claude-opus-4-6":   75.00,
    "claude-sonnet-4-6": 15.00,
    "claude-haiku-4-5":  4.00,
}
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.10


@dataclass
class ModelReport:
    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def cacheable_tokens(self) -> int:
        return self.cache_creation_tokens + self.cache_read_tokens

    @property
    def cache_hit_ratio(self) -> float:
        total = self.cacheable_tokens
        if total == 0:
            return 0.0
        return self.cache_read_tokens / total

    @property
    def actual_cost_usd(self) -> float:
        in_p = INPUT_PRICES.get(self.model)
        out_p = OUTPUT_PRICES.get(self.model)
        if in_p is None or out_p is None:
            return float("nan")
        return (
            (self.input_tokens / 1_000_000) * in_p
            + (self.cache_creation_tokens / 1_000_000) * in_p * CACHE_WRITE_MULT
            + (self.cache_read_tokens / 1_000_000) * in_p * CACHE_READ_MULT
            + (self.output_tokens / 1_000_000) * out_p
        )

    @property
    def naive_cost_usd(self) -> float:
        """What it would cost without any caching (every cache_read counted as fresh input)."""
        in_p = INPUT_PRICES.get(self.model)
        out_p = OUTPUT_PRICES.get(self.model)
        if in_p is None or out_p is None:
            return float("nan")
        all_input = self.input_tokens + self.cache_creation_tokens + self.cache_read_tokens
        return (all_input / 1_000_000) * in_p + (self.output_tokens / 1_000_000) * out_p

    @property
    def savings_usd(self) -> float:
        if not (self.actual_cost_usd == self.actual_cost_usd):  # NaN check
            return float("nan")
        return max(0.0, self.naive_cost_usd - self.actual_cost_usd)


@dataclass
class Report:
    per_model: dict[str, ModelReport] = field(default_factory=dict)

    def add(self, record: dict) -> None:
        model = record.get("model", "unknown")
        m = self.per_model.setdefault(model, ModelReport(model=model))
        m.calls += 1
        m.input_tokens += int(record.get("input_tokens", 0) or 0)
        m.output_tokens += int(record.get("output_tokens", 0) or 0)
        m.cache_creation_tokens += int(record.get("cache_creation_input_tokens", 0) or 0)
        m.cache_read_tokens += int(record.get("cache_read_input_tokens", 0) or 0)

    def as_dict(self) -> dict:
        return {
            model: {
                "calls": m.calls,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "cache_creation_tokens": m.cache_creation_tokens,
                "cache_read_tokens": m.cache_read_tokens,
                "cache_hit_ratio": round(m.cache_hit_ratio, 4),
                "actual_cost_usd": round(m.actual_cost_usd, 4)
                    if m.actual_cost_usd == m.actual_cost_usd else None,
                "naive_cost_usd": round(m.naive_cost_usd, 4)
                    if m.naive_cost_usd == m.naive_cost_usd else None,
                "savings_usd": round(m.savings_usd, 4)
                    if m.savings_usd == m.savings_usd else None,
            }
            for model, m in self.per_model.items()
        }

    def as_text(self) -> str:
        if not self.per_model:
            return "(no records)"
        out: list[str] = []
        total_savings = 0.0
        total_calls = 0
        for model in sorted(self.per_model):
            m = self.per_model[model]
            out.append(f"== {model} ==")
            out.append(f"  calls:                  {m.calls}")
            out.append(f"  input tokens (fresh):   {m.input_tokens:,}")
            out.append(f"  cache write tokens:     {m.cache_creation_tokens:,}")
            out.append(f"  cache read tokens:      {m.cache_read_tokens:,}")
            out.append(f"  output tokens:          {m.output_tokens:,}")
            out.append(f"  cache hit ratio:        {m.cache_hit_ratio:.1%}")
            if m.actual_cost_usd == m.actual_cost_usd:
                out.append(f"  actual cost:            ${m.actual_cost_usd:.4f}")
                out.append(f"  no-cache baseline:      ${m.naive_cost_usd:.4f}")
                out.append(f"  savings vs baseline:    ${m.savings_usd:.4f}")
                total_savings += m.savings_usd
            else:
                out.append(f"  cost:                   (unknown model, no price)")
            total_calls += m.calls
            out.append("")
        out.append(f"TOTAL calls: {total_calls}   TOTAL savings: ${total_savings:.4f}")
        return "\n".join(out)


def analyze(records: Iterable[dict]) -> Report:
    report = Report()
    for r in records:
        report.add(r)
    return report


def load_jsonl(path: str) -> list[dict]:
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Analyse prompt-cache usage from a JSONL log.")
    parser.add_argument("--log", help="Path to JSONL log file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human text.")
    parser.add_argument("--self-test", action="store_true", help="Run offline self-test.")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    if not args.log:
        parser.error("--log is required (or use --self-test)")

    report = analyze(load_jsonl(args.log))
    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(report.as_text())
    return 0


def _self_test() -> int:
    records = [
        # Three calls on sonnet, of which two hit the cache for most input
        {
            "model": "claude-sonnet-4-6",
            "input_tokens": 200,
            "output_tokens": 500,
            "cache_creation_input_tokens": 10_000,
            "cache_read_input_tokens": 0,
        },
        {
            "model": "claude-sonnet-4-6",
            "input_tokens": 250,
            "output_tokens": 500,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 10_000,
        },
        {
            "model": "claude-sonnet-4-6",
            "input_tokens": 180,
            "output_tokens": 600,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 10_000,
        },
        # One opus call, no caching
        {
            "model": "claude-opus-4-6",
            "input_tokens": 1_000,
            "output_tokens": 800,
        },
        # One unknown model -> no price
        {
            "model": "claude-future-x",
            "input_tokens": 100,
            "output_tokens": 100,
        },
    ]
    report = analyze(records)
    d = report.as_dict()

    sonnet = d["claude-sonnet-4-6"]
    assert sonnet["calls"] == 3, sonnet
    assert sonnet["cache_read_tokens"] == 20_000, sonnet
    assert sonnet["cache_creation_tokens"] == 10_000, sonnet
    # hit ratio = read / (read+write) = 20000/30000 = 0.6667
    assert abs(sonnet["cache_hit_ratio"] - 0.6667) < 0.001, sonnet
    # naive cost should be strictly greater than actual cost (cache saved money)
    assert sonnet["actual_cost_usd"] < sonnet["naive_cost_usd"], sonnet
    assert sonnet["savings_usd"] > 0, sonnet

    opus = d["claude-opus-4-6"]
    # No caching at all -> savings should be 0
    assert opus["savings_usd"] == 0.0, opus

    unknown = d["claude-future-x"]
    assert unknown["actual_cost_usd"] is None, unknown
    assert unknown["savings_usd"] is None, unknown

    text = report.as_text()
    assert "claude-sonnet-4-6" in text
    assert "savings" in text.lower()

    print("ok: prompt_cache_analyzer self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

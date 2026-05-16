"""
Streaming response logger - print to console, log to JSONL, annotate with cost.

Why this exists:
    Most LLM applications stream responses. The default behavior is to print
    tokens as they arrive and forget them. That is fine until you want to
    answer "what did the model say last Tuesday at 14:32, and how much did
    that one call cost". This module solves three problems at once:

      1. Forward streamed tokens to stdout (or any writer) so you keep the
         interactive UX.
      2. Collect the full final text and the usage object once the stream
         closes.
      3. Write a single line to a JSONL log with timestamp, model, full text,
         token usage, and a USD cost estimate.

Public API:
    log_streamed_call(
        client, *, model, messages, system=None,
        max_tokens=2048, log_path="llm.jsonl",
        printer=sys.stdout.write,
    ) -> dict

    The returned dict matches the JSONL record exactly.

Pricing:
    A small embedded price table covers current Anthropic models. Unknown
    models fall back to a "cost_usd": None record so the log still works.

No external dependencies beyond the anthropic SDK.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Callable


# Price per 1M tokens, USD. Update when providers reprice.
PRICES = {
    "claude-opus-4-6":   {"in": 15.00, "out": 75.00},
    "claude-sonnet-4-6": {"in":  3.00, "out": 15.00},
    "claude-haiku-4-5":  {"in":  0.80, "out":  4.00},
}


def _cost_usd(model: str, in_tokens: int, out_tokens: int) -> float | None:
    if model not in PRICES:
        return None
    p = PRICES[model]
    return round(
        (in_tokens / 1_000_000) * p["in"] + (out_tokens / 1_000_000) * p["out"],
        6,
    )


def log_streamed_call(
    client: Any,
    *,
    model: str,
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 2048,
    log_path: str = "llm.jsonl",
    printer: Callable[[str], int] | None = None,
) -> dict:
    """
    Run a streamed completion, print tokens as they arrive, and write a
    structured JSONL record. Returns the record.
    """
    printer = printer or sys.stdout.write
    started = time.monotonic()
    chunks: list[str] = []
    in_tokens = 0
    out_tokens = 0

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                printer(event.delta.text)
                chunks.append(event.delta.text)
        final = stream.get_final_message()
        if final.usage is not None:
            in_tokens = final.usage.input_tokens
            out_tokens = final.usage.output_tokens

    duration_ms = int((time.monotonic() - started) * 1000)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "duration_ms": duration_ms,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "cost_usd": _cost_usd(model, in_tokens, out_tokens),
        "text": "".join(chunks),
    }

    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


# ── Self-test ────────────────────────────────────────────────────────────────

def _self_test() -> int:
    """
    Offline self-test: fake client, fake stream, verify the record shape.
    """
    class _FakeDelta:
        def __init__(self, text: str) -> None:
            self.type = "text_delta"
            self.text = text

    class _FakeEvent:
        def __init__(self, text: str) -> None:
            self.type = "content_block_delta"
            self.delta = _FakeDelta(text)

    class _FakeUsage:
        input_tokens = 12
        output_tokens = 34

    class _FakeFinal:
        usage = _FakeUsage()

    class _FakeStream:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def __iter__(self):
            return iter([_FakeEvent("hello "), _FakeEvent("world")])
        def get_final_message(self): return _FakeFinal()

    class _FakeMessages:
        def stream(self, **kwargs): return _FakeStream()

    class _FakeClient:
        messages = _FakeMessages()

    written: list[str] = []
    out_path = "/tmp/_streaming_logger_test.jsonl"
    try:
        import os
        if os.path.exists(out_path):
            os.remove(out_path)
        record = log_streamed_call(
            _FakeClient(),
            model="claude-sonnet-4-6",
            messages=[{"role": "user", "content": "hi"}],
            log_path=out_path,
            printer=lambda s: written.append(s) or len(s),
        )
        assert record["text"] == "hello world"
        assert record["input_tokens"] == 12
        assert record["output_tokens"] == 34
        assert record["cost_usd"] is not None
        assert "".join(written) == "hello world"
        with open(out_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded["text"] == "hello world"
        print("ok: streaming_response_logger self-test passed")
        return 0
    except AssertionError as exc:
        print(f"fail: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_self_test())

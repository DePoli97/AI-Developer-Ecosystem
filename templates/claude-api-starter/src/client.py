"""
Anthropic client wrapper with retry, logging, and streaming.

Public API:
    ClaudeClient(config: Config)
        .complete(messages, system=None) -> str
        .stream(messages, system=None, on_token=None) -> str

Both methods append a structured JSONL record to LOG_DIR/runs.jsonl.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Callable

from anthropic import Anthropic, APIStatusError

from .config import Config


def _read_system_prompt() -> str:
    from pathlib import Path
    path = Path(__file__).parent / "prompts" / "system.txt"
    return path.read_text(encoding="utf-8").strip()


class ClaudeClient:
    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._client = Anthropic(api_key=config.api_key)
        self._default_system = _read_system_prompt()
        config.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = config.log_dir / "runs.jsonl"

    # ── Non-streaming ────────────────────────────────────────────────────────

    def complete(self, messages: list[dict], system: str | None = None) -> str:
        started = time.monotonic()
        response = self._with_retry(
            lambda: self._client.messages.create(
                model=self._cfg.model,
                max_tokens=self._cfg.max_tokens,
                system=system or self._default_system,
                messages=messages,
            )
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        self._log({
            "kind": "complete",
            "duration_ms": int((time.monotonic() - started) * 1000),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "stop_reason": response.stop_reason,
            "text": text,
        })
        return text

    # ── Streaming ────────────────────────────────────────────────────────────

    def stream(
        self,
        messages: list[dict],
        system: str | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        started = time.monotonic()
        chunks: list[str] = []
        in_tokens = out_tokens = 0
        with self._client.messages.stream(
            model=self._cfg.model,
            max_tokens=self._cfg.max_tokens,
            system=system or self._default_system,
            messages=messages,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    chunks.append(event.delta.text)
                    if on_token:
                        on_token(event.delta.text)
            final = stream.get_final_message()
            if final.usage is not None:
                in_tokens = final.usage.input_tokens
                out_tokens = final.usage.output_tokens
        text = "".join(chunks)
        self._log({
            "kind": "stream",
            "duration_ms": int((time.monotonic() - started) * 1000),
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "text": text,
        })
        return text

    # ── Internals ────────────────────────────────────────────────────────────

    def _with_retry(self, fn, *, max_attempts: int = 4):
        delay = 0.5
        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except APIStatusError as exc:
                if exc.status_code in (429, 503, 529) and attempt < max_attempts:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def _log(self, record: dict) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": self._cfg.model,
            **record,
        }
        with open(self._log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

"""
Rate-limit aware client wrapper - token bucket plus Retry-After respect.

Why this exists:
    Every LLM provider rate-limits both requests per minute and tokens per
    minute. The naive client either blasts through and gets 429s, or sleeps
    far longer than necessary on a single retry. This wrapper does two
    things well:

      1. Pre-flight: a local token bucket throttles requests so you stay
         under a configured RPM and TPM, smoothing bursts.
      2. Reactive: if the server still returns a 429 or 529, the wrapper
         honours the Retry-After header (in seconds) and retries with a
         capped exponential backoff.

It is provider-agnostic: pass any callable that takes a payload dict and
either returns a response or raises an exception with a `.status_code` and
optional `.response.headers` attribute (matching httpx / requests / the
anthropic SDK conventions).

Public API:
    RateLimitedClient(send, *, rpm, tpm, max_retries=5, max_backoff_s=30)
        .send(payload, *, estimated_input_tokens, estimated_output_tokens=0)

Dependencies:
    standard library only.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _Bucket:
    capacity: float
    refill_per_s: float
    tokens: float
    last: float

    def take(self, n: float) -> float:
        """Reserve n tokens. Returns the seconds to wait before they are available."""
        now = time.monotonic()
        elapsed = now - self.last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        deficit = n - self.tokens
        wait = deficit / self.refill_per_s
        self.tokens = 0.0
        return wait


class RateLimitedClient:
    def __init__(
        self,
        send: Callable[[dict], Any],
        *,
        rpm: int,
        tpm: int,
        max_retries: int = 5,
        max_backoff_s: float = 30.0,
    ) -> None:
        self._send = send
        self._max_retries = max_retries
        self._max_backoff = max_backoff_s
        self._lock = threading.Lock()
        now = time.monotonic()
        self._req = _Bucket(
            capacity=float(rpm), refill_per_s=rpm / 60.0,
            tokens=float(rpm), last=now,
        )
        self._tok = _Bucket(
            capacity=float(tpm), refill_per_s=tpm / 60.0,
            tokens=float(tpm), last=now,
        )

    def _reserve(self, tokens: float) -> None:
        with self._lock:
            wait_req = self._req.take(1.0)
            wait_tok = self._tok.take(tokens)
        wait = max(wait_req, wait_tok)
        if wait > 0:
            time.sleep(wait)

    def send(
        self,
        payload: dict,
        *,
        estimated_input_tokens: int,
        estimated_output_tokens: int = 0,
    ) -> Any:
        tokens = float(estimated_input_tokens + estimated_output_tokens)
        attempt = 0
        while True:
            self._reserve(tokens)
            try:
                return self._send(payload)
            except Exception as exc:  # noqa: BLE001
                status = getattr(exc, "status_code", None)
                if status is None:
                    resp = getattr(exc, "response", None)
                    status = getattr(resp, "status_code", None)
                if status not in (429, 529, 503):
                    raise
                if attempt >= self._max_retries:
                    raise
                retry_after = _retry_after_seconds(exc)
                backoff = _exponential_backoff(attempt, cap=self._max_backoff)
                time.sleep(max(retry_after, backoff))
                attempt += 1


def _retry_after_seconds(exc: Exception) -> float:
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return 0.0
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 0.0


def _exponential_backoff(attempt: int, *, base: float = 0.5, cap: float = 30.0) -> float:
    span = min(cap, base * (2 ** attempt))
    return random.uniform(0, span)


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate a server that returns 429 for the first two calls, then 200.
    calls = {"n": 0}

    class FakeError(Exception):
        def __init__(self, status: int, retry_after: float = 0.0) -> None:
            self.status_code = status
            self.response = type("R", (), {"headers": {"retry-after": str(retry_after)}})()

    def fake_send(payload: dict):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise FakeError(429, retry_after=0.05)
        return {"ok": True, "echo": payload}

    client = RateLimitedClient(fake_send, rpm=600, tpm=600_000, max_retries=5)
    start = time.monotonic()
    result = client.send(
        {"prompt": "hello"},
        estimated_input_tokens=100,
        estimated_output_tokens=50,
    )
    elapsed = time.monotonic() - start

    assert result["ok"] is True, result
    assert calls["n"] == 3, calls
    assert elapsed >= 0.10, elapsed  # at least the two retry-after waits
    print(f"ok: rate_limit_aware_client self-test passed ({elapsed:.2f}s, {calls['n']} attempts)")

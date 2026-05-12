"""
A small, pragmatic retry helper for HTTP and LLM API calls.

Why it exists:
    - Most retry libraries are either too heavy or hide the policy.
    - The 90% case is: retry on a known set of exceptions, exponential backoff,
      capped wait, full jitter, give up after N tries.

Usage:

    @retry(
        retries=4,
        retry_on=(ConnectionError, TransientAPIError),
        base_delay_s=0.5,
        max_delay_s=8.0,
    )
    def fetch_thing(client, id):
        return client.get(id)

Run the self-test:
    python retry_with_backoff.py
"""

from __future__ import annotations

import functools
import random
import time
from typing import Callable, Iterable, Type, TypeVar

T = TypeVar("T")


class TransientAPIError(Exception):
    """Raise this from your code when an API returned a retryable status."""


def retry(
    *,
    retries: int = 3,
    retry_on: Iterable[Type[BaseException]] = (Exception,),
    base_delay_s: float = 0.5,
    max_delay_s: float = 8.0,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry the wrapped function on the given exception types.

    Delay grows as base * 2**attempt, capped at max_delay_s. With jitter=True,
    the actual sleep is uniformly sampled from [0, delay] (full jitter).
    """
    retry_on_t = tuple(retry_on)

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except retry_on_t as e:
                    if attempt >= retries:
                        raise
                    delay = min(max_delay_s, base_delay_s * (2 ** attempt))
                    if jitter:
                        delay = random.uniform(0.0, delay)
                    sleep(delay)
                    attempt += 1

        return wrapper

    return decorator


# --- Self-test ---------------------------------------------------------------


def _self_test() -> None:
    attempts = {"n": 0}

    @retry(retries=3, retry_on=(TransientAPIError,), base_delay_s=0.01, max_delay_s=0.01)
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientAPIError("nope")
        return "ok"

    assert flaky() == "ok"
    assert attempts["n"] == 3

    fails = {"n": 0}

    @retry(retries=1, retry_on=(TransientAPIError,), base_delay_s=0.01, max_delay_s=0.01)
    def always_fails():
        fails["n"] += 1
        raise TransientAPIError("nope")

    try:
        always_fails()
    except TransientAPIError:
        pass
    assert fails["n"] == 2  # initial + 1 retry

    print("retry_with_backoff self-test: OK")


if __name__ == "__main__":
    _self_test()

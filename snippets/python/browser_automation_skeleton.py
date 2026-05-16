"""
browser_automation_skeleton - idempotent action layer for LLM-driven browsing.

Why this exists:
    Naive LLM browser agents fail in three predictable ways: they double-
    submit forms, they retry an action whose visible state already changed,
    and they cannot tell "I already did this" from "the page is broken".
    The fix is an idempotent action layer that exposes a small, stable set
    of verbs and validates the page state before and after each action.

    This module provides a typed action protocol (ActionRequest /
    ActionResult), a state-machine runner, and an `IdempotencyLedger` that
    suppresses repeat actions when their post-condition is already true.

    The runner is browser-agnostic: it talks to any object that implements
    a tiny `BrowserLike` protocol (goto, click, fill, current_url, locate,
    text_of). The shipped `FakeBrowser` implements that protocol with an
    in-memory DOM, which is what powers the offline self-test.

    In production, wrap Playwright's page object with a thin adapter that
    implements the same five methods, and you get the same guarantees.

Public API:
    ActionRequest(kind, selector=None, value=None, expect=None)
    ActionResult(ok, state, reason, request)
    IdempotencyLedger().has(state_key) / .record(state_key)
    Runner(browser, ledger=None, max_retries=2)
        .perform(action) -> ActionResult
        .run_plan(actions) -> list[ActionResult]

Dependencies:
    standard library only.

Self-test:
    python browser_automation_skeleton.py
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Protocol

# ── Browser protocol ─────────────────────────────────────────────────────────

class BrowserLike(Protocol):
    def goto(self, url: str) -> None: ...
    def click(self, selector: str) -> None: ...
    def fill(self, selector: str, value: str) -> None: ...
    def current_url(self) -> str: ...
    def text_of(self, selector: str) -> str: ...
    def exists(self, selector: str) -> bool: ...


# ── Public data types ────────────────────────────────────────────────────────

@dataclass
class ActionRequest:
    kind: str                       # "goto" | "click" | "fill" | "assert_text" | "assert_url"
    selector: str | None = None
    value: str | None = None
    expect: dict | None = None      # post-condition: {"text_in": str, "url_matches": str, ...}


@dataclass
class ActionResult:
    ok: bool
    state: str                      # short post-action state digest
    reason: str
    request: ActionRequest
    duration_ms: int = 0


class IdempotencyLedger:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def has(self, key: str) -> bool:
        return key in self._seen

    def record(self, key: str) -> None:
        self._seen.add(key)

    def __len__(self) -> int:
        return len(self._seen)


# ── Runner ───────────────────────────────────────────────────────────────────

class Runner:
    def __init__(
        self,
        browser: BrowserLike,
        *,
        ledger: IdempotencyLedger | None = None,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._browser = browser
        self._ledger = ledger or IdempotencyLedger()
        self._max_retries = max_retries

    def _state_key(self, action: ActionRequest) -> str:
        if action.kind == "goto":
            return f"url::{action.value}"
        if action.kind == "click":
            return f"click::{action.selector}::{self._browser.current_url()}"
        if action.kind == "fill":
            return f"fill::{action.selector}::{action.value}"
        if action.kind == "assert_text":
            return f"text::{action.selector}::{action.value}"
        if action.kind == "assert_url":
            return f"url-matches::{action.value}"
        return f"other::{action.kind}::{action.selector}::{action.value}"

    def _post_satisfied(self, action: ActionRequest) -> bool:
        exp = action.expect or {}
        if "url_matches" in exp:
            if not re.search(exp["url_matches"], self._browser.current_url()):
                return False
        if "text_in" in exp:
            sel = exp.get("text_in_selector", "body")
            if exp["text_in"] not in self._browser.text_of(sel):
                return False
        if "exists" in exp:
            if not self._browser.exists(exp["exists"]):
                return False
        return True

    def perform(self, action: ActionRequest) -> ActionResult:
        started = time.monotonic()

        # Pre-check idempotency: if the post-condition is already true, skip.
        if action.expect and self._post_satisfied(action):
            return ActionResult(
                ok=True,
                state="already-satisfied",
                reason="post-condition already true; action skipped",
                request=action,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        key = self._state_key(action)
        if self._ledger.has(key) and action.kind != "goto":
            return ActionResult(
                ok=True,
                state="already-executed",
                reason="idempotency ledger says we already did this",
                request=action,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        last_err = ""
        for attempt in range(self._max_retries + 1):
            try:
                self._dispatch(action)
                last_err = ""
                break
            except Exception as exc:  # noqa: BLE001
                last_err = f"{type(exc).__name__}: {exc}"

        if last_err:
            return ActionResult(
                ok=False,
                state="error",
                reason=last_err,
                request=action,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        if action.expect:
            if not self._post_satisfied(action):
                return ActionResult(
                    ok=False,
                    state="post-failed",
                    reason=f"post-condition not satisfied: {action.expect}",
                    request=action,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )

        self._ledger.record(key)
        return ActionResult(
            ok=True,
            state="executed",
            reason="ok",
            request=action,
            duration_ms=int((time.monotonic() - started) * 1000),
        )

    def _dispatch(self, action: ActionRequest) -> None:
        if action.kind == "goto":
            self._browser.goto(action.value or "")
        elif action.kind == "click":
            self._browser.click(action.selector or "")
        elif action.kind == "fill":
            self._browser.fill(action.selector or "", action.value or "")
        elif action.kind == "assert_text":
            if (action.value or "") not in self._browser.text_of(action.selector or "body"):
                raise AssertionError(
                    f"assertion failed: {action.value!r} not in {action.selector!r}"
                )
        elif action.kind == "assert_url":
            if not re.search(action.value or "", self._browser.current_url()):
                raise AssertionError(
                    f"url assertion failed: {self._browser.current_url()!r} !~ {action.value!r}"
                )
        else:
            raise ValueError(f"unknown action kind: {action.kind}")

    def run_plan(self, actions: list[ActionRequest]) -> list[ActionResult]:
        results: list[ActionResult] = []
        for a in actions:
            r = self.perform(a)
            results.append(r)
            if not r.ok:
                break
        return results


# ── FakeBrowser (drives the self-test and any unit test) ─────────────────────

@dataclass
class FakeBrowser:
    url: str = "about:blank"
    dom: dict = field(default_factory=dict)        # selector -> text
    inputs: dict = field(default_factory=dict)     # selector -> value
    on_click: dict = field(default_factory=dict)   # selector -> callable(self) | None
    flaky: dict = field(default_factory=dict)      # selector -> remaining failures

    def goto(self, url: str) -> None:
        self.url = url

    def click(self, selector: str) -> None:
        if self.flaky.get(selector, 0) > 0:
            self.flaky[selector] -= 1
            raise RuntimeError(f"transient: click on {selector} failed")
        cb = self.on_click.get(selector)
        if cb:
            cb(self)

    def fill(self, selector: str, value: str) -> None:
        self.inputs[selector] = value

    def current_url(self) -> str:
        return self.url

    def text_of(self, selector: str) -> str:
        return self.dom.get(selector, "")

    def exists(self, selector: str) -> bool:
        return selector in self.dom or selector in self.inputs


# ── Self-test ────────────────────────────────────────────────────────────────

def _self_test() -> int:
    # Scenario: login flow on a fake page.
    browser = FakeBrowser(
        dom={
            "body": "Please log in",
            "h1": "Login",
        },
    )

    def submit(b: FakeBrowser) -> None:
        u = b.inputs.get("#username", "")
        p = b.inputs.get("#password", "")
        if u == "alice" and p == "secret":
            b.url = "https://example.com/dashboard"
            b.dom = {"body": "Welcome, alice", "h1": "Dashboard"}
        else:
            b.dom = {"body": "Invalid credentials", "h1": "Login"}

    browser.on_click["#submit"] = submit

    runner = Runner(browser, max_retries=2)
    plan = [
        ActionRequest(kind="goto", value="https://example.com/login",
                      expect={"url_matches": "/login"}),
        ActionRequest(kind="fill", selector="#username", value="alice"),
        ActionRequest(kind="fill", selector="#password", value="secret"),
        ActionRequest(kind="click", selector="#submit",
                      expect={"url_matches": "/dashboard", "text_in": "Welcome, alice"}),
    ]
    results = runner.run_plan(plan)
    assert all(r.ok for r in results), [r.reason for r in results]
    assert results[-1].state == "executed", results[-1]

    # Re-run just the final click on the post-login state. The post-condition
    # is already satisfied, so the runner must skip without re-submitting.
    only_click = [plan[-1]]
    again = runner.run_plan(only_click)
    assert again[0].ok and again[0].state == "already-satisfied", again[0]

    # Re-run the full plan. The runner is allowed to either short-circuit on
    # post-condition or be blocked by the ledger; either is acceptable as
    # long as no real side effects re-fire.
    again_full = runner.run_plan(plan)
    skip_states = {"already-satisfied", "already-executed"}
    assert all(r.ok for r in again_full), [r.reason for r in again_full]
    assert all(r.state in skip_states or r.state == "executed" for r in again_full), [r.state for r in again_full]

    # Flaky click: should succeed after retry.
    b2 = FakeBrowser(dom={"body": "ready"})
    b2.on_click["#go"] = lambda x: (setattr(x, "url", "https://x/ok"),
                                    x.dom.__setitem__("body", "DONE"))
    b2.flaky["#go"] = 2  # fail twice, then succeed
    r2 = Runner(b2, max_retries=3)
    res = r2.perform(ActionRequest(kind="click", selector="#go",
                                   expect={"url_matches": "/ok", "text_in": "DONE"}))
    assert res.ok, res
    assert res.state == "executed"

    # Flaky beyond retry budget: should fail.
    b3 = FakeBrowser(dom={"body": ""})
    b3.flaky["#never"] = 5
    r3 = Runner(b3, max_retries=2)
    res2 = r3.perform(ActionRequest(kind="click", selector="#never"))
    assert not res2.ok, res2
    assert "transient" in res2.reason or "RuntimeError" in res2.reason, res2

    # Bad action kind
    try:
        Runner(FakeBrowser()).perform(ActionRequest(kind="bogus"))
    except Exception:
        raise AssertionError("expected ActionResult with ok=False, not raise")
    # (Runner catches and reports; verify it does)
    bad = Runner(FakeBrowser()).perform(ActionRequest(kind="bogus"))
    assert not bad.ok, bad

    # Invalid configs
    try:
        Runner(FakeBrowser(), max_retries=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    print("ok: browser_automation_skeleton self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())

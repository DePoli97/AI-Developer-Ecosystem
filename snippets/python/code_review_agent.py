"""
code_review_agent - a runnable Claude code-review agent.

Building blocks used:
    - diff_summariser.py  : structural summary of the diff
    - claude_agent_sdk_starter.py : the underlying tool-use loop pattern

What it does:
    Given a unified diff (file path, stdin, or `git diff` of the current
    repo), the agent inspects relevant files, classifies risks, and emits
    a structured review with: a one-paragraph summary, a list of issues
    (each with severity, file, line, and a suggested fix), and a verdict
    (approve / request_changes / comment).

Two modes:
    - 'offline'  : no API call. Uses the diff_summariser plus a rule-based
                   reviewer. Always works, useful in CI smoke tests.
    - 'claude'   : makes the agent loop against the Anthropic API.

The script's self-test runs the offline mode end-to-end against a sample
diff so it is verifiable without an API key.

CLI:
    python code_review_agent.py --self-test
    git diff main...HEAD | python code_review_agent.py --offline
    python code_review_agent.py --offline --diff patch.diff --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Import the diff summariser from the same snippets directory
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from diff_summariser import summarise_text, parse_diff  # type: ignore


# ── Rule-based reviewer (offline mode) ──────────────────────────────────────

SECRET_RX = re.compile(
    r"(?:api[_\-]?key|secret|token|password|passwd|aws[_\-]?(?:access|secret))"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    re.IGNORECASE,
)
PRINT_DEBUG_RX = re.compile(r"^\s*(?:print|console\.log|dump\()\(")
TODO_RX = re.compile(r"\b(?:TODO|FIXME|XXX)\b", re.IGNORECASE)
BARE_EXCEPT_RX = re.compile(r"^\s*except\s*:")
HARDCODED_LOCALHOST_RX = re.compile(r"https?://(?:localhost|127\.0\.0\.1)(?::\d+)?")


@dataclass
class Issue:
    severity: str           # "blocker" | "major" | "minor" | "nit"
    file: str
    line: int | None
    rule: str
    message: str
    snippet: str | None = None


@dataclass
class Review:
    summary: str
    issues: list[Issue] = field(default_factory=list)
    verdict: str = "comment"  # "approve" | "request_changes" | "comment"
    totals: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "summary": self.summary,
            "verdict": self.verdict,
            "totals": self.totals,
            "issues": [asdict(i) for i in self.issues],
        }


def _scan_added_line(file_path: str, line_no: int, content: str) -> list[Issue]:
    issues: list[Issue] = []
    if SECRET_RX.search(content):
        issues.append(Issue(
            severity="blocker",
            file=file_path,
            line=line_no,
            rule="hardcoded-secret",
            message="Possible secret/credential committed in source.",
            snippet=content.strip()[:160],
        ))
    if PRINT_DEBUG_RX.search(content):
        issues.append(Issue(
            severity="minor",
            file=file_path,
            line=line_no,
            rule="debug-print",
            message="Debug print/log left in code path. Consider using a logger or removing.",
            snippet=content.strip()[:160],
        ))
    if BARE_EXCEPT_RX.search(content):
        issues.append(Issue(
            severity="major",
            file=file_path,
            line=line_no,
            rule="bare-except",
            message="Bare `except:` swallows everything including KeyboardInterrupt; catch specific exceptions.",
            snippet=content.strip()[:160],
        ))
    if HARDCODED_LOCALHOST_RX.search(content):
        issues.append(Issue(
            severity="minor",
            file=file_path,
            line=line_no,
            rule="hardcoded-host",
            message="Hardcoded localhost URL; consider moving to config.",
            snippet=content.strip()[:160],
        ))
    if TODO_RX.search(content):
        issues.append(Issue(
            severity="nit",
            file=file_path,
            line=line_no,
            rule="todo-marker",
            message="TODO/FIXME left in diff. Consider tracking in an issue.",
            snippet=content.strip()[:160],
        ))
    return issues


def review_diff_offline(diff_text: str) -> Review:
    summary_doc = summarise_text(diff_text)
    diff = parse_diff(diff_text)

    issues: list[Issue] = []
    for file in diff.files:
        for hunk in file.hunks:
            line_no = hunk.new_start
            for content in hunk.added:
                issues.extend(_scan_added_line(file.path, line_no, content))
                line_no += 1

    # Add risk-driven issues from the structural summary
    for risk in summary_doc["risks"]:
        sev = "major" if ("sensitive" in risk or "binary" in risk) else "minor"
        issues.append(Issue(
            severity=sev,
            file="(diff-level)",
            line=None,
            rule="diff-risk",
            message=risk,
        ))

    totals = summary_doc["totals"]
    n_blockers = sum(1 for i in issues if i.severity == "blocker")
    n_major = sum(1 for i in issues if i.severity == "major")

    if n_blockers:
        verdict = "request_changes"
    elif n_major:
        verdict = "request_changes"
    elif issues:
        verdict = "comment"
    else:
        verdict = "approve"

    summary_text = (
        f"{totals['files_changed']} files changed "
        f"(+{totals['added_lines']} / -{totals['removed_lines']}); "
        f"{n_blockers} blocker(s), {n_major} major issue(s), "
        f"{len(issues) - n_blockers - n_major} other note(s)."
    )

    return Review(summary=summary_text, issues=issues, verdict=verdict, totals=totals)


# ── Claude-powered reviewer (placeholder agent loop) ─────────────────────────

def review_diff_with_claude(diff_text: str, *, model: str = "claude-sonnet-4-6") -> dict:
    """
    Runs the agent loop against the Anthropic API. Requires:
        pip install anthropic
        ANTHROPIC_API_KEY in env.

    The agent has two tools: get_diff_summary and inspect_added_lines.
    It must produce a final JSON-formatted review.
    """
    try:
        from anthropic import Anthropic  # type: ignore
    except ImportError as exc:
        raise RuntimeError("anthropic not installed; run `pip install anthropic`") from exc

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    summary = summarise_text(diff_text)
    parsed = parse_diff(diff_text)

    tools = [
        {
            "name": "get_diff_summary",
            "description": "Return the structural summary of the diff (files, kinds, line counts, risks).",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "inspect_added_lines",
            "description": "Return added lines for a specific file in the diff. Use to read what was actually added.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    ]

    added_by_file: dict[str, list[str]] = {
        f.path: [line for h in f.hunks for line in h.added]
        for f in parsed.files
    }

    def run_tool(name: str, args: dict) -> str:
        if name == "get_diff_summary":
            return json.dumps(summary)
        if name == "inspect_added_lines":
            return json.dumps(added_by_file.get(args.get("path", ""), []))
        return json.dumps({"error": f"unknown tool {name}"})

    client = Anthropic()
    system = (
        "You are a senior code reviewer. Use the tools to inspect the diff, "
        "then return a JSON object with keys: summary, verdict "
        "(approve|request_changes|comment), and issues (list of objects "
        "with severity, file, line, rule, message). Be specific and concise. "
        "Do not invent file paths."
    )
    messages = [{"role": "user", "content": "Review this pull request."}]
    for _ in range(8):
        resp = client.messages.create(
            model=model, max_tokens=2048, system=system, tools=tools, messages=messages,
        )
        if resp.stop_reason == "end_turn":
            text = "".join(b.text for b in resp.content if b.type == "text")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                output = run_tool(block.name, dict(block.input))
                is_error = False
            except Exception as exc:  # noqa: BLE001
                output = f"tool raised {type(exc).__name__}: {exc}"
                is_error = True
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": results})

    return {"summary": "agent loop exceeded step limit", "verdict": "comment", "issues": []}


# ── CLI ──────────────────────────────────────────────────────────────────────

def _read_diff(args: argparse.Namespace) -> str:
    if args.diff:
        return Path(args.diff).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Code-review agent over a unified diff.")
    parser.add_argument("--diff", help="Path to a diff file (default: stdin).")
    parser.add_argument("--offline", action="store_true",
                        help="Use the rule-based reviewer; no API call.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run offline self-test.")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    diff_text = _read_diff(args)
    if args.offline or not os.environ.get("ANTHROPIC_API_KEY"):
        review = review_diff_offline(diff_text)
        data = review.as_dict()
    else:
        data = review_diff_with_claude(diff_text, model=args.model)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print(f"Verdict: {data.get('verdict', '?')}")
    print(f"Summary: {data.get('summary', '?')}")
    issues = data.get("issues") or []
    if not issues:
        print("No issues found.")
        return 0
    print(f"\n{len(issues)} issue(s):")
    for i in issues:
        loc = f"{i.get('file')}"
        if i.get("line"):
            loc += f":{i['line']}"
        print(f"  [{i.get('severity').upper()}] {loc}  ({i.get('rule')})")
        print(f"      {i.get('message')}")
        if i.get("snippet"):
            print(f"      | {i['snippet']}")
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────

SAMPLE_BAD_DIFF = """diff --git a/src/api.py b/src/api.py
index aaaaaaa..bbbbbbb 100644
--- a/src/api.py
+++ b/src/api.py
@@ -1,3 +1,8 @@
 import requests
+
+API_KEY = "sk-proj-deadbeefdeadbeefdeadbeef12345678"
+
+def fetch(url):
+    print("DEBUG: about to call", url)
+    try:
+        return requests.get(url).json()
+    except:
+        return None
diff --git a/.env b/.env
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/.env
@@ -0,0 +1 @@
+TOKEN=abcdefghijklmnop1234567890qrstuv
"""

SAMPLE_OK_DIFF = """diff --git a/src/util.py b/src/util.py
index aaaaaaa..bbbbbbb 100644
--- a/src/util.py
+++ b/src/util.py
@@ -1,3 +1,5 @@
 def add(a, b):
     return a + b
+
+def mul(a, b):
+    return a * b
"""


def _self_test() -> int:
    bad = review_diff_offline(SAMPLE_BAD_DIFF)
    rules = {i.rule for i in bad.issues}
    assert "hardcoded-secret" in rules, rules
    assert "debug-print" in rules, rules
    assert "bare-except" in rules, rules
    assert bad.verdict == "request_changes", bad.verdict
    assert any(i.severity == "blocker" for i in bad.issues), bad.issues

    good = review_diff_offline(SAMPLE_OK_DIFF)
    assert good.verdict == "approve", good.verdict
    assert good.issues == [], good.issues

    # JSON round-trip
    payload = json.dumps(bad.as_dict())
    loaded = json.loads(payload)
    assert loaded["verdict"] == "request_changes"
    assert len(loaded["issues"]) >= 3

    print("ok: code_review_agent self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

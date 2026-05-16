"""
diff_summariser - parse a unified diff and emit a structured summary.

Why this exists:
    A code-review agent needs a compact, faithful summary of what a diff
    changes before it can reason about it. Feeding raw `git diff` output
    into an LLM wastes tokens and often loses the structural signal.
    This module parses unified diff text into per-file and per-hunk
    records, classifies each hunk, flags risks (deleted-only files,
    binary blobs, very large additions, touched config), and returns a
    JSON-serialisable summary that fits comfortably in a system prompt.

Public API:
    parse_diff(text: str) -> Diff
    summarise(diff: Diff) -> dict
    summarise_text(text: str) -> dict

CLI:
    cat patch.diff | python diff_summariser.py
    git diff main...HEAD | python diff_summariser.py --json

Dependencies:
    standard library only.

Self-test:
    python diff_summariser.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field

# A unified-diff hunk header looks like: @@ -12,7 +12,8 @@ optional context
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
FILE_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")
NEW_FILE = re.compile(r"^new file mode")
DELETED_FILE = re.compile(r"^deleted file mode")
RENAMED = re.compile(r"^rename from (.+)$")
BINARY_MARKER = re.compile(r"^Binary files .* differ$|^GIT binary patch$")
INDEX_LINE = re.compile(r"^index [0-9a-f]+\.\.[0-9a-f]+( [0-7]+)?$")

# Conventional config/sensitive file globs that elevate risk
SENSITIVE_PATTERNS = [
    re.compile(r"\.env$|\.env\."),
    re.compile(r"(?i)secrets?"),
    re.compile(r"(?i)credential"),
    re.compile(r"requirements\.txt$|pyproject\.toml$|package\.json$|Cargo\.toml$|go\.mod$"),
    re.compile(r"\.github/workflows/"),
    re.compile(r"Dockerfile$|docker-compose"),
    re.compile(r"(?i)migration|schema"),
]


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    context: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)


@dataclass
class FileChange:
    path: str
    old_path: str | None = None
    kind: str = "modified"  # added | deleted | renamed | modified | binary
    is_binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def added_lines(self) -> int:
        return sum(len(h.added) for h in self.hunks)

    @property
    def removed_lines(self) -> int:
        return sum(len(h.removed) for h in self.hunks)


@dataclass
class Diff:
    files: list[FileChange] = field(default_factory=list)


def parse_diff(text: str) -> Diff:
    diff = Diff()
    current: FileChange | None = None
    current_hunk: Hunk | None = None

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = FILE_HEADER.match(line)
        if m:
            # Finalise previous
            if current is not None:
                if current_hunk is not None:
                    current.hunks.append(current_hunk)
                    current_hunk = None
                diff.files.append(current)
            current = FileChange(path=m.group(2))
            current.old_path = m.group(1) if m.group(1) != m.group(2) else None
            i += 1
            continue

        if current is None:
            i += 1
            continue

        if NEW_FILE.match(line):
            current.kind = "added"
            i += 1
            continue
        if DELETED_FILE.match(line):
            current.kind = "deleted"
            i += 1
            continue
        m = RENAMED.match(line)
        if m:
            current.kind = "renamed"
            current.old_path = m.group(1)
            i += 1
            continue
        if BINARY_MARKER.match(line):
            current.is_binary = True
            current.kind = "binary"
            i += 1
            continue
        if INDEX_LINE.match(line) or line.startswith(("--- ", "+++ ")) or line.startswith("similarity index"):
            i += 1
            continue

        m = HUNK_HEADER.match(line)
        if m:
            if current_hunk is not None:
                current.hunks.append(current_hunk)
            current_hunk = Hunk(
                old_start=int(m.group(1)),
                old_count=int(m.group(2) or 1),
                new_start=int(m.group(3)),
                new_count=int(m.group(4) or 1),
                context=m.group(5).strip(),
            )
            i += 1
            continue

        if current_hunk is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk.added.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk.removed.append(line[1:])
            # context lines are ignored; the model has the headers
        i += 1

    if current is not None:
        if current_hunk is not None:
            current.hunks.append(current_hunk)
        diff.files.append(current)
    return diff


def _is_sensitive(path: str) -> bool:
    return any(rx.search(path) for rx in SENSITIVE_PATTERNS)


def _classify_risks(diff: Diff) -> list[str]:
    risks: list[str] = []
    for f in diff.files:
        if f.is_binary:
            risks.append(f"binary change in {f.path}")
        if f.kind == "deleted" and not _is_sensitive(f.path):
            if f.removed_lines > 50:
                risks.append(f"large file deletion: {f.path} ({f.removed_lines} lines)")
        if _is_sensitive(f.path):
            risks.append(f"sensitive file touched: {f.path}")
        if f.added_lines > 400:
            risks.append(f"large addition in {f.path} ({f.added_lines} lines)")
    return risks


def summarise(diff: Diff) -> dict:
    files_out = []
    for f in diff.files:
        files_out.append({
            "path": f.path,
            "old_path": f.old_path,
            "kind": f.kind,
            "is_binary": f.is_binary,
            "added_lines": f.added_lines,
            "removed_lines": f.removed_lines,
            "hunks": [
                {
                    "old_range": [h.old_start, h.old_count],
                    "new_range": [h.new_start, h.new_count],
                    "context": h.context,
                    "added": len(h.added),
                    "removed": len(h.removed),
                }
                for h in f.hunks
            ],
        })
    total_added = sum(f.added_lines for f in diff.files)
    total_removed = sum(f.removed_lines for f in diff.files)
    return {
        "files": files_out,
        "totals": {
            "files_changed": len(diff.files),
            "added_lines": total_added,
            "removed_lines": total_removed,
            "net_lines": total_added - total_removed,
        },
        "risks": _classify_risks(diff),
    }


def summarise_text(text: str) -> dict:
    return summarise(parse_diff(text))


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli() -> int:
    parser = argparse.ArgumentParser(description="Summarise a unified diff.")
    parser.add_argument("--json", action="store_true", help="Emit JSON (default: pretty).")
    parser.add_argument("--self-test", action="store_true", help="Run offline self-test.")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    data = sys.stdin.read()
    summary = summarise_text(data)
    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    totals = summary["totals"]
    print(f"{totals['files_changed']} files, +{totals['added_lines']} / -{totals['removed_lines']} ({totals['net_lines']:+d} net)")
    for f in summary["files"]:
        flag = ""
        if f["kind"] == "added": flag = " (new)"
        elif f["kind"] == "deleted": flag = " (deleted)"
        elif f["kind"] == "renamed": flag = f" (renamed from {f['old_path']})"
        elif f["kind"] == "binary": flag = " (binary)"
        print(f"  {f['path']}{flag}: +{f['added_lines']} / -{f['removed_lines']}")
    if summary["risks"]:
        print("\nRisks:")
        for r in summary["risks"]:
            print(f"  - {r}")
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────

SAMPLE_DIFF = """diff --git a/src/auth.py b/src/auth.py
index abc1234..def5678 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,7 +10,8 @@ def login(user, password):
-    return verify(user, password)
+    if not user:
+        raise ValueError("user required")
+    return verify(user, password)
diff --git a/.env.example b/.env.example
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/.env.example
@@ -0,0 +1,2 @@
+API_KEY=
+SECRET=
diff --git a/old.txt b/new.txt
similarity index 100%
rename from old.txt
rename to new.txt
diff --git a/data/image.png b/data/image.png
new file mode 100644
index 0000000..deadbee
Binary files /dev/null and b/data/image.png differ
"""


def _self_test() -> int:
    summary = summarise_text(SAMPLE_DIFF)
    files = {f["path"]: f for f in summary["files"]}

    assert "src/auth.py" in files
    auth = files["src/auth.py"]
    assert auth["kind"] == "modified", auth
    assert auth["added_lines"] == 3, auth
    assert auth["removed_lines"] == 1, auth

    assert ".env.example" in files
    env = files[".env.example"]
    assert env["kind"] == "added", env
    assert env["added_lines"] == 2, env

    assert "new.txt" in files
    renamed = files["new.txt"]
    assert renamed["kind"] == "renamed", renamed
    assert renamed["old_path"] == "old.txt", renamed

    assert "data/image.png" in files
    bin_f = files["data/image.png"]
    assert bin_f["is_binary"] is True, bin_f
    assert bin_f["kind"] == "binary", bin_f

    totals = summary["totals"]
    assert totals["files_changed"] == 4, totals
    assert totals["added_lines"] == 5, totals
    assert totals["removed_lines"] == 1, totals

    risks = summary["risks"]
    assert any("sensitive" in r for r in risks), risks
    assert any("binary" in r for r in risks), risks

    print("ok: diff_summariser self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

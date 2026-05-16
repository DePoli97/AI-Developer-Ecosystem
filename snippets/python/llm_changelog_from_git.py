"""
llm_changelog_from_git - turn `git log` into structured release notes.

Why this exists:
    Most teams write changelogs by hand and stop after the second release.
    This script takes `git log` output between two refs, groups commits by
    conventional-commit prefix (feat, fix, docs, refactor, perf, test,
    chore, content, seo), and emits a Markdown release note ready to
    paste into CHANGELOG.md or the GitHub release body. No LLM call is
    required for the basic format; an optional polish step can be added
    later if you want to call Claude to rewrite the bullets.

Public API:
    parse_git_log(text: str) -> list[Commit]
    build_release_notes(commits, *, version, date) -> str

CLI:
    git log --oneline v1.0..HEAD | python llm_changelog_from_git.py --version v1.1
    python llm_changelog_from_git.py --self-test

Dependencies:
    standard library only. Optional: subprocess call to git if you pass --from/--to.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls

CONVENTIONAL = re.compile(r"^(?P<type>feat|fix|docs|refactor|perf|test|chore|content|seo|build|ci|automation|research)(?:\((?P<scope>[^)]+)\))?(!)?:\s*(?P<subject>.+)$")

# Human-friendly section titles, ordered as we want them in the output.
SECTION_TITLES = [
    ("feat",       "Added"),
    ("content",    "Content"),
    ("seo",        "SEO"),
    ("research",   "Research"),
    ("automation", "Automation"),
    ("fix",        "Fixed"),
    ("perf",       "Performance"),
    ("refactor",   "Refactored"),
    ("docs",       "Documentation"),
    ("test",       "Tests"),
    ("ci",         "CI"),
    ("build",      "Build"),
    ("chore",      "Chore"),
    ("other",      "Other changes"),
]


@dataclass
class Commit:
    sha: str
    type: str
    scope: str | None
    breaking: bool
    subject: str

    @property
    def short_sha(self) -> str:
        return self.sha[:7]


def parse_git_log(text: str) -> list[Commit]:
    """
    Accepts output of `git log --pretty=format:'%H %s'` (one commit per line).
    Lines that don't follow conventional commits are bucketed as 'other'.
    """
    commits: list[Commit] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Optional SHA prefix
        sha = ""
        subject_line = line
        m = re.match(r"^([0-9a-f]{7,40})\s+(.*)$", line)
        if m:
            sha, subject_line = m.group(1), m.group(2)

        cm = CONVENTIONAL.match(subject_line)
        if cm:
            ctype = cm.group("type")
            scope = cm.group("scope")
            breaking = bool(cm.group(3))
            subject = cm.group("subject")
        else:
            ctype = "other"
            scope = None
            breaking = False
            subject = subject_line
        commits.append(Commit(sha=sha, type=ctype, scope=scope, breaking=breaking, subject=subject))
    return commits


def _group(commits: list[Commit]) -> dict[str, list[Commit]]:
    grouped: dict[str, list[Commit]] = defaultdict(list)
    for c in commits:
        grouped[c.type].append(c)
    return grouped


def build_release_notes(
    commits: list[Commit],
    *,
    version: str,
    date: str | None = None,
) -> str:
    date_str = date or date_cls.today().isoformat()
    grouped = _group(commits)

    lines: list[str] = [f"## {version} - {date_str}", ""]

    # Surface BREAKING CHANGES first
    breaking = [c for c in commits if c.breaking]
    if breaking:
        lines.append("### Breaking changes")
        lines.append("")
        for c in breaking:
            scope = f" *({c.scope})*" if c.scope else ""
            lines.append(f"- {c.subject}{scope} ({c.short_sha})" if c.sha else f"- {c.subject}{scope}")
        lines.append("")

    for key, title in SECTION_TITLES:
        items = grouped.get(key, [])
        if not items:
            continue
        lines.append(f"### {title}")
        lines.append("")
        for c in items:
            scope = f" *({c.scope})*" if c.scope else ""
            entry = f"- {c.subject}{scope}"
            if c.sha:
                entry += f" ({c.short_sha})"
            lines.append(entry)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _run_git_log(from_ref: str, to_ref: str) -> str:
    result = subprocess.run(
        ["git", "log", f"--pretty=format:%H %s", f"{from_ref}..{to_ref}"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout


def _cli() -> int:
    p = argparse.ArgumentParser(description="Build release notes from git log.")
    p.add_argument("--version", default="Unreleased", help="Version heading.")
    p.add_argument("--date", help="Date heading (default: today).")
    p.add_argument("--from", dest="from_ref", help="Start ref for `git log a..b`.")
    p.add_argument("--to", dest="to_ref", default="HEAD", help="End ref for `git log a..b`.")
    p.add_argument("--self-test", action="store_true", help="Run offline self-test.")
    args = p.parse_args()

    if args.self_test:
        return _self_test()

    if args.from_ref:
        log_text = _run_git_log(args.from_ref, args.to_ref)
    else:
        log_text = sys.stdin.read()

    commits = parse_git_log(log_text)
    print(build_release_notes(commits, version=args.version, date=args.date))
    return 0


def _self_test() -> int:
    sample = """\
abc1234 feat(api): add streaming endpoint
def5678 fix: handle empty responses
0011223 docs: update README
4455667 refactor(client): simplify retry path
8899aab content: add prompt engineering article
ccddeef feat(agents)!: new agent loop, breaks tool schema
1234567 seo: improve internal linking
abcdef0 random non-conventional commit message
fedcba9 chore: bump deps
1110000 test: add eval harness cases
"""
    commits = parse_git_log(sample)
    assert len(commits) == 10, len(commits)
    by_type = _group(commits)
    assert len(by_type["feat"]) == 2, by_type
    assert any(c.breaking for c in by_type["feat"]), by_type
    assert len(by_type["other"]) == 1, by_type

    notes = build_release_notes(commits, version="v1.0.0", date="2026-05-16")
    assert "## v1.0.0 - 2026-05-16" in notes
    assert "### Breaking changes" in notes
    assert "### Added" in notes
    assert "### Fixed" in notes
    assert "### Documentation" in notes
    assert "### Other changes" in notes
    assert "random non-conventional commit message" in notes
    assert "(abcdef0)" in notes
    # Breaking change should appear before the Added section
    bidx = notes.index("### Breaking changes")
    aidx = notes.index("### Added")
    assert bidx < aidx, "Breaking section should come first"

    # Empty input
    empty = build_release_notes(parse_git_log(""), version="v0.0.0", date="2026-01-01")
    assert "## v0.0.0 - 2026-01-01" in empty

    print("ok: llm_changelog_from_git self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

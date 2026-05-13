# Changelog

All notable changes to this repository are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-based because this is a content repository, not a
released library.

## 2026-05-13

### Added
- Tutorial: *Parse structured JSON output from any LLM, reliably*
  (`tutorials/2026-05-parse-structured-llm-output.md`). End-to-end
  walkthrough that turns messy LLM responses into validated pydantic
  objects, with a retry policy keyed on the parse error.
- Snippet: `snippets/python/structured_json_output.py`. Robust
  fenced/repaired/balanced JSON extractor with a runnable self-test
  covering five common LLM failure modes.
- `CHANGELOG.md` (this file) to track repository evolution.
- `SESSION_LOG.md` to coordinate handoffs between autonomous sessions.

### Changed
- `README.md` now exposes a *Latest content* section with direct links to
  the highest-value entries, and lists `CHANGELOG.md` in *Project direction*.
- `snippets/README.md` and `tutorials/README.md` index the new entries.

### Removed
- `test.txt` placeholder marked for removal (handled via `git rm` at commit).

## 2026-05-12

### Added
- Initial repository scaffold: top-level strategy docs (`ROADMAP.md`,
  `MONETIZATION.md`, `SEO.md`, `GROWTH.md`, `IDEAS.md`, `CONTRIBUTING.md`),
  five content areas (`articles/`, `tutorials/`, `workflows/`, `snippets/`,
  `templates/`), `LICENSE` (MIT for code, CC BY 4.0 for content), first
  article (*A practical guide to Claude tool use*), three Python snippets
  (Anthropic tool-use loop, token-aware text splitter, retry with backoff),
  and the *Agent loop with tool use* workflow note.
- One-time `.bootstrap/` handoff bundle for pushing the initial commit
  from the user's local machine.

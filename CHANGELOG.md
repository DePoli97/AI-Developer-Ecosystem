# Changelog

All notable changes to this repository are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-based because this is a content repository, not a
released library.

## 2026-05-14

### Added
- Tutorial: *Build your first Claude tool-use agent in 30 minutes*
  (`tutorials/2026-05-claude-tool-use-starter.md`). Full walkthrough
  with three runnable files (tools.py, agent.py, run.py), a visual
  loop diagram, and a common-mistakes table.
- Snippet: `snippets/python/token_cost_estimator.py`. Unified cost
  estimator for Anthropic, OpenAI, and Google models. Accepts raw API
  response objects or explicit token counts; returns a structured
  `CostEstimate` with input/output/total USD breakdown and prompt-cache
  support. Ships with 12 passing self-tests and a cost-comparison table.
- Research: `opportunities/affiliate-devtools-shortlist.md`. Shortlist
  of 6 affiliate programmes with audience-fit analysis, SEO keyword
  angles, revenue projections, and action items.

### Changed
- `tutorials/README.md`: new tutorial indexed; *Coming soon* list updated.
- `snippets/README.md`: new snippet indexed.
- `opportunities/README.md`: affiliate opportunity added as item #4.
- `SESSION_LOG.md`: 2026-05-14 entry prepended.

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

## 2026-05-15

### Added
- Tutorial: *Prompt versioning with golden examples*
  (`tutorials/2026-05-prompt-versioning-with-golden-examples.md`).
  20-minute guide covering versioned prompt files, a golden_examples.json
  schema with four composable check types, a CI-ready runner script, and
  a GitHub Actions workflow snippet.
- Snippet: `snippets/python/prompt_version_runner.py`. Production-ready
  golden-example test harness: loads versioned `.txt` prompt files, fills
  `{{variable}}` templates, runs single-turn messages via the Anthropic SDK,
  and evaluates outputs with exact_match / max_sentences / must_contain_any /
  must_not_contain checks. Ships with 9 evaluator self-tests (no API key
  required: `--self-test`). CI-friendly exit codes.

### Changed
- `tutorials/README.md`: added prompt-versioning tutorial to index;
  removed "Coming soon" entry for it.
- `snippets/README.md`: added prompt_version_runner.py entry.

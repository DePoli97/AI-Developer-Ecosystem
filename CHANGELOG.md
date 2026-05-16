# Changelog

All notable changes to this repository are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-based because this is a content repository, not a
released library.

## 2026-05-16

### Added
- Tutorial: *Build a working Claude agent in 20 minutes with the Claude
  Agent SDK* (`tutorials/2026-05-claude-agent-sdk-quickstart.md`).
  Single-file agent with three sandboxed tools (read_file, list_dir,
  run_shell), full conversation-loop walkthrough, and a section on the
  three failure modes that bite first.
- Snippet: `snippets/python/claude_agent_sdk_starter.py`. Companion code
  for the quickstart, ready to drop into any project.
- Snippet: `snippets/python/streaming_response_logger.py`. Streams LLM
  responses to stdout while writing structured JSONL records (timestamp,
  model, tokens, USD cost). Offline self-test.
- Snippet: `snippets/python/minimal_eval_harness.py`. Sub-200-line eval
  harness with composable checks (exact, substring, regex, predicate,
  max-length), async runner, and CI-friendly exit code.
- Snippet: `snippets/python/rate_limit_aware_client.py`. Token-bucket
  wrapper that smooths bursts to configured RPM and TPM, honours
  `Retry-After` headers, and applies capped exponential backoff.
- Workflow: `workflows/rag-starter-sqlite-fts5.md`. Hybrid retrieval
  (FTS5 + embeddings) in one SQLite file, with RRF fusion, indexing and
  query code, schema, and a "when to graduate" section.
- Article: `articles/2026-05-ai-devtools-trends-that-actually-matter.md`.
  Five trends that are reshaping the stack in 2026, plus three honest
  "did not pan out" calls.
- Template: `templates/claude-api-starter/`. Typed env loading, retry-aware
  Anthropic client, streaming support, JSONL run logs, CLI entry point,
  smoke tests, dependency manifest.
- Research: `research/agent-frameworks-landscape-2026-05.md`. Field
  comparison of seven agent frameworks with recommendations by team
  profile.
- `CONTENT_PLAN.md`. Rolling 30-day editorial calendar with topic clusters
  and metrics to track.
- Opportunity: `opportunities/product-brief-claude-agent-kit.md`. Brief
  for a potential paid starter kit, packaging the open-source assets in
  this repo with a cookbook and support.

### Changed
- `articles/README.md`, `tutorials/README.md`, `snippets/README.md`,
  `workflows/README.md`, `templates/README.md`, `research/README.md`: all
  indices updated with the new entries.
- `IDEAS.md`: six new entries added under "Added 2026-05-16".
- `SEO.md`: foundational clusters documented, six new long-tail keywords
  added.
- `GROWTH.md`: distribution moments for the new content queued.
- `MONETIZATION.md`: opportunities identified from today's content set.
- `SESSION_LOG.md`: 2026-05-16 entry added.


### Added (afternoon batch)
- Article: *A field guide to LLM cost engineering*
  (`articles/2026-05-llm-cost-engineering-field-guide.md`). Six tactics
  in apply-order with effort/savings numbers; closes the cost+observability
  cluster.
- Snippet: `snippets/python/reciprocal_rank_fusion.py` (RRF utility,
  composable scorers, debug origins).
- Snippet: `snippets/python/rag_sqlite_starter.py` (runnable RAG companion
  with hashing-encoder offline mode).
- Snippet: `snippets/python/prompt_cache_analyzer.py` (cache-hit ratio
  and USD savings from a JSONL log).
- Snippet: `snippets/python/diff_summariser.py` (unified-diff parser with
  risk classification; tested on real `git diff`).
- Snippet: `snippets/python/llm_changelog_from_git.py` (release notes
  generator from git history with conventional-commit grouping).
- Snippet: `snippets/python/code_review_agent.py` (offline rule-based
  reviewer + Claude agent loop variant).
- Snippet: `snippets/python/model_router.py` (heuristic router with
  composable scorers and low-confidence escalation).
- Snippet: `snippets/python/prompt_compressor.py` (safe + aggressive
  compression with measurable savings).
- Snippet: `snippets/python/conversation_compactor.py` (token-budgeted
  compaction with heuristic summary and recent-turns preservation).
- Snippet: `snippets/python/browser_automation_skeleton.py` (idempotent
  action layer with FakeBrowser for offline tests).
- Cookbook: `cookbook/` with `documentation_search_agent.py`,
  `eval_on_commit.py`, and `cost_budget_guard.py`. All self-tested.
- CI: `.github/workflows/tests.yml` (matrix-runs every snippet self-test
  across Python 3.10-3.12; pins numpy/pydantic/anthropic).
- CI: `.github/workflows/eval.yml` (runs the eval cookbook on PRs that
  touch prompts; posts a status comment).

### Changed (afternoon batch)
- `articles/README.md`: cost engineering article indexed.
- `snippets/README.md`: ten new snippet entries indexed.
- `README.md`: latest content refreshed.

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

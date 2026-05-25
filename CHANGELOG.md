# Changelog

All notable changes to this repository are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is date-based because this is a content repository, not a
released library.

## 2026-05-25

### Added
- Tutorial: *Build a 50-query gold set for your RAG system*
  (`tutorials/2026-05-build-rag-eval-gold-set.md`). End-to-end walkthrough
  of the hand-labelling and measurement loop: where to source real
  queries (production logs, support tickets, Slack), how to pool
  candidates for fast labelling, the JSON schema to commit, and the
  variance-aware regression check that prevents "average went up, ten
  queries got worse" merges. Closes the retrieval-cluster gold-set gap
  flagged in `CONTENT_PLAN.md`. Primary keyword: *rag evaluation gold
  set*.
- Snippet: `snippets/python/rag_eval_gold_set.py`. Sub-200-line
  evaluation harness. Loads the gold set, runs an arbitrary dict of
  retriever callables (`retrieve(query, k) -> list[str]`), reports
  averaged nDCG@10 and MRR, and surfaces the worst per-query
  regressions for triage. Zero third-party dependencies; ships with a
  self-test that runs perfect, baseline, and broken retrievers against
  a fixture gold set.

### Changed
- `README.md` - latest content list now leads with the gold-set
  tutorial and harness.
- `tutorials/README.md` and `snippets/README.md` - indexed the new
  entries.
- `CONTENT_PLAN.md` - retrieval-cluster note updated; the gold-set
  tutorial is marked shipped.

### Fixed
- `.push-pending.sh` - resolved a stale merge-conflict block left over
  from a prior session; kept the LaunchAgent-friendly version (idempotent
  re-runs, auto-stash, structured logging) that pairs with
  `.launchd/com.depoli.ai-dev-push.plist`.

## 2026-05-22

### Added
- Workflow: *Automated changelog generator, from git log to release notes*
  (`workflows/llm-changelog-from-git.md`). Companion document to the
  existing `snippets/python/llm_changelog_from_git.py`. Describes the
  deterministic two-piece pipeline (parser + renderer), a copy-paste
  release script, a one-line CI check for conventional commits, and an
  optional LLM polish pass with a diff-and-fall-back safety step.
  Closes the Week 3 workflow slot in `CONTENT_PLAN.md`. Primary
  keyword: *automated changelog generator*.

### Changed
- `README.md` - latest content list now leads with the changelog
  workflow.
- `workflows/README.md` - indexed the new workflow.
- `CONTENT_PLAN.md` - Week 3 workflow row marked DONE.

## 2026-05-20

### Added
- Article: *Hybrid retrieval, with numbers*
  (`articles/2026-05-hybrid-retrieval-numbers.md`). Foundation piece of
  the retrieval cluster, with concrete nDCG@10 / MRR numbers from a 30-
  document corpus and six labelled queries. Honest reporting: when fusion
  helps, when it averages-out a strong dense signal, and the simple
  decision rule for whether to add a cross-encoder reranker. Cross-links
  the RRF snippet, the reranker snippet, the RAG workflow, and the RAG
  starter tutorial.
- Snippet: `snippets/python/cross_encoder_reranker.py`. Second-stage
  cross-encoder reranker for RAG. Pluggable scorer interface (default is
  a deterministic mock so self-tests run offline; optional
  `sentence_transformers_scorer` for production). Returns `Hit`
  dataclasses carrying both stage-one and stage-two ranks for regression
  debugging. Self-tested (6 checks, all passing).
- Opportunity brief: `opportunities/product-brief-pii-guard.md`. Three-
  tier monetisation plan for the existing `pii_redactor.py` snippet:
  free PyPI library, paid locale pattern packs, paid self-hosted +
  hosted proxy. Decision: ship the PyPI package only after one external
  inbound link; defer the rest behind a 500-weekly-download trigger.

### Changed
- `README.md` - latest content list updated with the hybrid retrieval
  article and the cross-encoder reranker snippet.
- `articles/README.md` - hybrid retrieval article indexed.
- `snippets/README.md` - cross-encoder reranker entry added.
- `opportunities/README.md` - pii-guard slot added (item 5).
- `CONTENT_PLAN.md` - hybrid retrieval article and reranker snippet
  marked done; retrieval cluster status set to complete with the next
  additions surfaced.

## 2026-05-18

### Added
- Tutorial: *Build a runnable RAG starter in 30 minutes, SQLite FTS5 +
  embeddings* (`tutorials/2026-05-rag-starter-runnable.md`). Step-by-step
  walkthrough that pairs the existing workflow and snippet: clone, run
  the self-test, install sentence-transformers, ingest Markdown, query
  with hybrid retrieval, and wire a grounded LLM answer with citations.
  Closes the CONTENT_PLAN slot for the retrieval cluster's tutorial.
- Snippet: `snippets/python/pii_redactor.py`. Dependency-free PII redactor
  with reversible tokenisation. Detects emails, phones, IPv4 addresses,
  US SSNs, Luhn-validated credit-card numbers, and AWS access keys.
  Stateful so placeholders stay stable across calls in long conversations.
  Ships with an offline self-test (8 checks, all passing) and a CLI for
  both redaction and unredaction.

### Changed
- `README.md` - latest content list updated with the RAG tutorial and the
  PII redactor.
- `tutorials/README.md` - new tutorial indexed; the RAG entry moved out
  of "Coming soon".
- `snippets/README.md` - PII redactor entry added.
- `CONTENT_PLAN.md` - retrieval-cluster tutorial slot marked done;
  cluster status line updated (foundation article still pending).

### Added
- Research note: `research/2026-05-18-pii-redaction-landscape.md`. Field
  notes on the trade-offs between rolling your own redactor, using a
  cloud DLP, and dedicated tools like Microsoft Presidio.

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

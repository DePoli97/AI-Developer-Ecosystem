# Snippets

Small, focused code samples. Each one is self-contained, runs as-is (after installing the noted dependencies), and is short enough to copy into a real project without ceremony.

## Layout

`python/` - Python snippets, tested on 3.10+.

`typescript/` - TypeScript snippets, written for Node 20+ (coming soon).

## Index

- `python/anthropic_tool_use_loop.py` - Minimal but production-shaped agent loop with tool runners, structured error handling, and a hard step limit. Companion to the article on Claude tool use.
- `python/token_aware_text_splitter.py` - Sentence- and paragraph-aware chunker that respects a token budget.
- `python/retry_with_backoff.py` - Pragmatic exponential backoff with jitter, typed exceptions, and a clean retry policy.
- `python/structured_json_output.py` - Robust extractor that turns messy LLM responses (fenced, smart-quoted, trailing-comma, prose-wrapped) into a validated pydantic model. Ships with a self-test.
- `python/token_cost_estimator.py` - Unified token cost estimator across Anthropic, OpenAI, and Google. Parses raw API responses or accepts explicit token counts; returns structured USD cost breakdowns. Supports prompt-cache pricing and unknown models. Ships with a self-test and a cost-comparison table.
- `python/prompt_version_runner.py` - Golden-example test harness for versioned LLM prompts. Load prompt `.txt` files, run them against the API, score outputs with composable checks (exact match, sentence count, keyword presence). CI-friendly exit codes. Ships with a self-test (`--self-test`) that needs no API key.
- `python/claude_agent_sdk_starter.py` - Single-file Claude agent with three sandboxed tools (read_file, list_dir, run_shell). Companion to the Agent SDK quickstart tutorial.
- `python/streaming_response_logger.py` - Stream LLM responses to console, capture full text and usage, append a structured JSONL log with USD cost annotation. Ships with an offline self-test.
- `python/minimal_eval_harness.py` - Sub-200-line eval harness for prompt regression tests. Composable checks (exact, substring, regex, predicate, max-length); async runner; CI-friendly exit code. Ships with a self-test.
- `python/rate_limit_aware_client.py` - Token-bucket wrapper that smooths bursts to configured RPM and TPM, honours `Retry-After` headers, and applies capped exponential backoff. Provider-agnostic. Ships with a self-test using a fake server.


- `python/reciprocal_rank_fusion.py` - Reciprocal Rank Fusion utility with composable result lists and an `rrf_with_origins` debug helper. Self-tested.
- `python/rag_sqlite_starter.py` - Runnable companion to the RAG starter workflow. Hybrid retrieval (FTS5 + embeddings, RRF fused) in a single SQLite file. Ships with a deterministic hashing encoder so the self-test runs with no heavy dependencies; swap in sentence-transformers for production.
- `python/prompt_cache_analyzer.py` - Parse a JSONL log of Anthropic responses, compute the cache-hit ratio and USD savings versus the no-cache baseline. CLI + self-test.
- `python/diff_summariser.py` - Parse a unified diff into structured per-file and per-hunk records, flag risks (sensitive files, binaries, large additions). CLI + self-test.
- `python/llm_changelog_from_git.py` - Turn `git log` output into Markdown release notes grouped by conventional-commit prefix. Works against real git history; self-tested.
- `python/code_review_agent.py` - Code-review agent with two modes: an offline rule-based reviewer (no API key needed) and a Claude-powered agent loop. Self-tested in offline mode.
- `python/model_router.py` - Heuristic model router with composable scorers (length, keyword complexity, explicit override) and a low-confidence escalation policy. Self-tested.
- `python/prompt_compressor.py` - Mechanical prompt compressor (safe and aggressive modes) that reports characters, words, and approximate tokens saved. Self-tested.
- `python/conversation_compactor.py` - Keep long agent conversations under a token budget by summarising old turns and keeping the recent ones verbatim. Self-tested with mixed content blocks.
- `python/browser_automation_skeleton.py` - Idempotent action layer for LLM-driven browsing. Pre/post-condition checks, retry budget, idempotency ledger. Ships with a `FakeBrowser` so the self-test runs without launching Chromium.
- `python/pii_redactor.py` - Dependency-free PII redactor with reversible tokenisation. Detects emails, phones, IPv4 addresses, US SSNs, Luhn-validated credit-card numbers, and AWS access keys. Stable placeholders across calls so model output can be unredacted before reaching the user. CLI + self-test (no API key required).
- `python/cross_encoder_reranker.py` - Second-stage cross-encoder reranker for RAG. Pluggable scorer interface, deterministic mock scorer for offline self-tests, optional `sentence_transformers_scorer()` for production. Returns `Hit` dataclasses with stage-one and stage-two ranks so regressions are debuggable. Companion to the hybrid retrieval article and the RAG starter tutorial.

## Conventions

Every snippet in this directory is expected to:

1. Run as `python <file>` and either print a useful result or run its self-test.
2. Be importable as a module without side effects (the demo lives under `if __name__ == "__main__":`).
3. Declare external dependencies in the module docstring.
4. Be short enough that the reader can hold the whole file in their head.

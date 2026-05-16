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

## Conventions

Every snippet in this directory is expected to:

1. Run as `python <file>` and either print a useful result or run its self-test.
2. Be importable as a module without side effects (the demo lives under `if __name__ == "__main__":`).
3. Declare external dependencies in the module docstring.
4. Be short enough that the reader can hold the whole file in their head.

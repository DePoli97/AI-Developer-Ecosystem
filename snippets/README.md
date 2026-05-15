# Snippets

Small, focused code samples. Each one is self-contained, runs as-is (after installing the noted dependencies), and is short enough to copy into a real project without ceremony.

## Layout

`python/` - Python snippets, tested on 3.10+.

`typescript/` - TypeScript snippets, written for Node 20+.

## Index

- `python/anthropic_tool_use_loop.py` - Minimal but production-shaped agent loop with tool runners, structured error handling, and a hard step limit. Companion to the article on Claude tool use.
- `python/token_aware_text_splitter.py` - Sentence- and paragraph-aware chunker that respects a token budget.
- `python/retry_with_backoff.py` - Pragmatic exponential backoff with jitter, typed exceptions, and a clean retry policy.
- `python/structured_json_output.py` - Robust extractor that turns messy LLM responses (fenced, smart-quoted, trailing-comma, prose-wrapped) into a validated pydantic model. Ships with a self-test.
- `python/token_cost_estimator.py` - Unified token cost estimator across Anthropic, OpenAI, and Google. Parses raw API responses or accepts explicit token counts; returns structured USD cost breakdowns. Supports prompt-cache pricing and unknown models. Ships with a self-test and a cost-comparison table.
- `python/prompt_version_runner.py` - Golden-example test harness for versioned LLM prompts. Load prompt `.txt` files, run them against the API, score outputs with composable checks (exact match, sentence count, keyword presence). CI-friendly exit codes. Ships with a self-test (`--self-test`) that needs no API key.

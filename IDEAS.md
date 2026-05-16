# Ideas Backlog

A living list of article topics, tools, and experiments worth considering. Items get pulled out of this file when they are ready to ship; rejected ones get a one-line note about why.

The list is intentionally noisy. Filtering happens at the moment of writing, not at the moment of capturing.

## Article topics

A practical guide to Claude tool use: designing tools that the model actually calls correctly, validating tool inputs, and handling tool errors so the agent recovers gracefully.

Structured output that survives reality. Comparing JSON-mode, schema-constrained decoding, and post-hoc validation. When each one is the right call.

Token budgets for agents. How to think about context windows when an agent makes many tool calls, and concrete patterns for summarizing intermediate state without losing the plot.

A minimal eval harness in 100 lines. Just enough to catch prompt regressions without adopting a heavy framework.

Designing prompts for two-week-from-now you. Versioning, diffing, golden examples, the smallest workflow that prevents prompt rot.

When RAG is the wrong answer. Cases where fine-tuning, a smaller model, or a non-LLM approach wins.

Cost shaping. How to actually drive per-request cost down without making the product worse. Caching strategies, model routing, prompt compression.

Browser automation with an LLM driver: the failure modes nobody talks about. Idempotency, recoverable actions, dealing with auth and CAPTCHAs the right way (i.e., do not).

A Claude agent that reviews your pull requests. End-to-end: webhook, fetch diff, plan, comment.

The five prompt patterns that pay rent. The handful of patterns that show up in nearly every shipping product.

Debugging an agent that "almost works". A taxonomy of common failure modes and the tools you need to spot each one.

How to evaluate an evals framework. Meta, but useful: the questions you should ask before adopting any eval library.

## Tooling and templates

A tiny CLI that diffs two prompt versions and runs them against the same inputs.

A streaming-aware logger for LLM responses, with token cost annotation.

A token-aware text splitter that respects sentence and paragraph boundaries.

A Claude tool-use scaffold: an opinionated starting point with retry, validation, and tracing built in.

A RAG starter kit: ingest, embed, store (SQLite + FTS5 first, optional vector store later), retrieve, eval. Designed to fit on a laptop.

A GitHub Action that runs a small eval suite on every PR that touches `prompts/`.

A browser-automation skeleton that pairs Playwright with Claude and demonstrates idempotent tool design.

A prompt registry: small, file-based, version-controlled prompt store with a tiny TypeScript/Python client.

## Experiments

Compare three RAG chunking strategies on a fixed dataset and publish a reproducible benchmark.

Build the same small agent twice: once with a heavy framework, once from scratch. Compare lines of code, debuggability, and cost.

Run a one-week experiment of writing every commit message with an LLM as a draft assistant. Report on what helped, what got in the way.

## Possible newsletter angles

"What I shipped this week." Personal, short, honest.

"Three links worth your time." Curated picks from the broader AI-devtools world.

"Quietly good tools." A monthly spotlight on under-the-radar developer tools, with a clear disclosure on any affiliate links.

## SEO opportunities to validate

Long-tail queries around "Claude tool use" - low competition, growing volume.

"OpenAI structured output" troubleshooting variations.

"Prompt versioning" - very few good results today.

"Agent eval" - early-stage cluster, room to own a topic.

"Browser automation LLM" - growing, mostly noisy results.

## Rejected, with reason

"Top 10 AI startups in 2026" - listicle, not aligned with the project.

"Why GPT-X is better than Claude-Y" - tribal, dates poorly, low value.

"AI tools to make you a millionaire" - hard no.

## Added 2026-05-16

LLM-driven changelog generator from git history. Read commit messages over a date range, group by conventional-commit prefix, draft a release note. Likely a workflow plus a 100-line snippet.

A "cost engineering field guide" article that consolidates everything we know about per-request cost reduction: prompt caching, model routing, batched calls, output-token caps, and per-feature token budgets.

A `prompt_cache_analyzer.py` snippet that parses Anthropic responses and reports the actual cache-hit ratio over a window of calls, with a CLI to summarise a JSONL log.

A code-review agent tutorial built on top of the Claude Agent SDK quickstart. Same skeleton, three extra tools (`fetch_pr_diff`, `comment_on_line`, `read_repo_file`), and a system prompt focused on review quality.

A "reciprocal rank fusion in 30 lines" snippet to support the hybrid-retrieval article. Tiny, well-documented, easy to drop into any retrieval system.

A "diff summariser for pull requests" snippet: input is a unified diff, output is a structured summary with risks, breaking-change flags, and reviewer hints. Useful as a building block for the code-review agent.

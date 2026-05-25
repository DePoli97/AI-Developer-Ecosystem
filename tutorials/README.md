# Tutorials

Step-by-step guides. Each tutorial gets you from zero to a working result in a single sitting, with copy-pasteable commands and explicit dependency versions.

## Index

2026-05 - [Build your first Claude tool-use agent in 30 minutes](./2026-05-claude-tool-use-starter.md). End-to-end walkthrough: define tools with JSON Schema, implement the agent loop, run a multi-turn shopping assistant, and understand every common mistake.

2026-05 - [Parse structured JSON output from any LLM, reliably](./2026-05-parse-structured-llm-output.md). A 15-minute walkthrough on turning messy LLM responses into validated pydantic objects, with a tested fallback parser and a retry policy that uses the actual error.

2026-05 - [Prompt versioning with golden examples](./2026-05-prompt-versioning-with-golden-examples.md). A 20-minute guide to tracking prompt changes like code, version files, define expected outputs in JSON, and catch regressions in CI before they reach production.

2026-05 - [Build a working Claude agent in 20 minutes with the Claude Agent SDK](./2026-05-claude-agent-sdk-quickstart.md). From an empty folder to an agent with file-read, directory-list, and shell tools. Companion snippet ships at `snippets/python/claude_agent_sdk_starter.py`.

2026-05 - [Build a runnable RAG starter in 30 minutes, SQLite FTS5 + embeddings](./2026-05-rag-starter-runnable.md). Index a folder of Markdown, run hybrid retrieval (lexical + embeddings + RRF), and wire a grounded LLM answer on top. Companion to the existing `workflows/rag-starter-sqlite-fts5.md` and `snippets/python/rag_sqlite_starter.py`.

2026-05 - [Build a 50-query gold set for your RAG system](./2026-05-build-rag-eval-gold-set.md). The hand-labelling and measurement loop that turns every retrieval change into a number. Companion snippet at `snippets/python/rag_eval_gold_set.py` with a self-tested nDCG@10 + MRR harness.

## Coming soon

- A code-review agent built on top of the Agent SDK quickstart.

Topics tracked in `IDEAS.md` and `CONTENT_PLAN.md`.

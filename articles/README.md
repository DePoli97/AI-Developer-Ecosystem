# Articles

Long-form technical writing. Each article is dated and includes a short summary at the top so a reader can decide in five seconds whether to keep reading.

## Index

2026-05 - [A practical guide to Claude tool use](./2026-05-claude-tool-use-practical-guide.md). Designing tools the model calls correctly, validating inputs, and recovering from tool errors.

2026-05 - [Five AI devtools trends that actually matter in 2026](./2026-05-ai-devtools-trends-that-actually-matter.md). A field report on the patterns that change how production AI software gets written, with three honest "do not bother" calls.
2026-05 - [A field guide to LLM cost engineering](./2026-05-llm-cost-engineering-field-guide.md). Six tactics, in apply-order, with the engineering effort and the typical savings you should expect. Companion to the cost+observability snippets in this repository.

2026-05 - [Hybrid retrieval, with numbers](./2026-05-hybrid-retrieval-numbers.md). The foundation piece of the retrieval cluster. What you actually buy when you fuse BM25 with dense retrieval, when a cross-encoder reranker is worth its latency, and a tiny corpus you can run on your laptop. Cross-links the RRF snippet, the reranker snippet, the RAG workflow, and the RAG tutorial.

2026-06 - [Indirect prompt injection via RAG: threat model and mitigations](./2026-06-indirect-prompt-injection-rag.md). Full attack taxonomy (instruction override, role hijack, tool invocation injection, data exfiltration, corpus poisoning) with working mitigation code: structural delimiters, heuristic chunk scanner, LLM-judge pre-filter, privilege separation for tool-capable agents, and corpus integrity controls. Companion to the RAG injection scanner snippet and the LLM firewall snippet.

2026-06 - [Multi-turn context attacks on LLM agents](./2026-06-multi-turn-context-attacks.md). A taxonomy of injections that unfold across multiple turns: slow-burn priming, context-window poisoning via long documents, memory poisoning in stateful agents, and role-confusion escalation in multi-agent pipelines. Includes a per-call and per-session defensive checklist and companion code (`session_integrity_guard.py`).

2026-06 - [Prompts as code: treat your prompts like the engineering artefacts they are](./2026-06-prompts-as-code-engineering-discipline.md). The foundation article for the prompt-engineering-as-code cluster. Version control for prompts, PR review discipline, model-version pinning, golden-example regression suites, CI integration, and staged rollout with feature flags. Companion to the prompt versioning tutorial and the `prompt_version_runner.py` snippet. Completes cluster 2.

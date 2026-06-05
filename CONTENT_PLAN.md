# Content plan, rolling 30 days

The editorial calendar for the next month. Each item lists the format,
the working title, the primary keyword, and the file path it will land at.
Items are pulled in order; if a higher-priority topic emerges, it jumps the
queue and the rest shift down by one.

The plan is reviewed every Monday. Completed items move to
`CHANGELOG.md`; abandoned items get a one-line note in `IDEAS.md`.

## Next 30 days

| Week | Type      | Working title                                                  | Primary keyword                  | Path                                                                       |
|------|-----------|----------------------------------------------------------------|----------------------------------|----------------------------------------------------------------------------|
| 1    | Tutorial  | Build a code-review agent with the Claude Agent SDK            | claude code review agent         | tutorials/2026-05-claude-code-review-agent.md                              |
| 1    | Snippet   | Diff-summariser for git pull requests                          | llm git diff summary             | snippets/python/diff_summariser.py                                         |
| 2    | Article   | A field guide to LLM cost engineering                          | llm cost optimization            | articles/2026-05-llm-cost-engineering-field-guide.md                       |
| 2    | Snippet   | Prompt cache analyzer for Anthropic responses                  | anthropic prompt cache           | snippets/python/prompt_cache_analyzer.py                                   |
| 3    | Tutorial  | RAG starter end-to-end (runnable script) - DONE 2026-05-18     | sqlite fts5 embeddings rag       | tutorials/2026-05-rag-starter-runnable.md + snippets/python/rag_sqlite_starter.py |
| 3    | Workflow  | LLM-driven changelog generator from commit history - DONE 2026-05-22 | automated changelog generator    | workflows/llm-changelog-from-git.md                                        |
| 4    | Article   | What hybrid retrieval actually buys you (with numbers) - DONE 2026-05-20 | hybrid retrieval bm25 embeddings | articles/2026-05-hybrid-retrieval-numbers.md                               |
| 4    | Snippet   | Reciprocal rank fusion as a 30-line utility                    | reciprocal rank fusion python    | snippets/python/reciprocal_rank_fusion.py                                  |
| 5    | Snippet   | Cross-encoder reranker (stage-two RAG ranking) - DONE 2026-05-20 | cross encoder reranker rag       | snippets/python/cross_encoder_reranker.py                                  |
| 6    | Tutorial  | Streaming logger walkthrough - DONE 2026-05-29                 | log llm calls cost jsonl         | tutorials/2026-05-streaming-logger-walkthrough.md                          |
| 6    | Tutorial  | PII redaction for LLM gateway - DONE 2026-05-29               | pii redaction llm python         | tutorials/2026-05-pii-redaction-llm-gateway.md                             |
| 7    | Article   | Defence-in-depth for LLM applications - DONE 2026-06-01        | llm security prompt injection    | articles/2026-06-llm-safety-defense-in-depth.md                            |
| 7    | Snippet   | LLM firewall drop-in wrapper - DONE 2026-06-01                 | llm firewall python anthropic    | snippets/python/llm_firewall.py                                             |
| 8    | Tutorial  | Build a code-review agent with the Claude Agent SDK            | claude code review agent         | tutorials/2026-06-claude-code-review-agent.md                              |
| 8    | Article   | Indirect prompt injection via RAG — DONE 2026-06-05            | indirect prompt injection rag    | articles/2026-06-indirect-prompt-injection-rag.md                          |
| 8    | Snippet   | RAG injection scanner (pre-injection chunk filter) — DONE 2026-06-05 | rag security prompt injection python | snippets/python/rag_injection_scanner.py                        |
| 9    | Tutorial  | Secure RAG pipeline end-to-end (scanner + firewall + audit)    | secure rag python llm            | tutorials/2026-06-secure-rag-pipeline.md                                   |
| 9    | Article   | Multi-turn context attacks on LLM agents                       | multi turn prompt injection llm  | articles/2026-06-multi-turn-context-attacks.md                             |

## Standing slots

A weekly research note in `research/` summarising what we read or
experimented with. These are not articles; they are field notes, dated,
short, and unedited. The most useful ones eventually graduate into
articles.

A monthly review pass on `IDEAS.md`. Anything older than three months that
has not surfaced into the plan gets archived to `IDEAS_ARCHIVE.md` with a
note on why.

## Topic clusters under construction

The repository is organising content around four clusters. Each cluster
is a topic an AI engineer searches for, and each cluster gets one foundational
article, one tutorial with runnable code, and at least one snippet.

The first cluster is **Claude agents**. Foundation: the trends article.
Tutorial: the Agent SDK quickstart. Snippet: `claude_agent_sdk_starter.py`.
Status: complete. Next addition: a code-review agent.

The second cluster is **prompt engineering as code**. Foundation: a future
"prompts-as-code" article that consolidates the patterns. Tutorial: the
prompt versioning with golden examples tutorial. Snippet:
`prompt_version_runner.py`. Status: tutorial and snippet shipped; foundation
article pending.

The third cluster is **retrieval**. Foundation: a hybrid retrieval article
backed by numbers. Tutorial: a runnable RAG starter. Workflow: the SQLite
FTS5 plus embeddings write-up. Snippets: `reciprocal_rank_fusion.py`,
`rag_sqlite_starter.py`, `cross_encoder_reranker.py`. Status: complete.
The 50-query gold-set tutorial shipped 2026-05-25 at
`tutorials/2026-05-build-rag-eval-gold-set.md` with the harness at
`snippets/python/rag_eval_gold_set.py`. Next addition: the companion to
the reranker snippet ("when to add a reranker, with numbers"
walk-through).

The fourth cluster is **cost and observability**. Foundation: a cost
engineering field guide. Tutorial: a streaming logger walkthrough. Snippet:
`token_cost_estimator.py` and `streaming_response_logger.py`. Status:
**complete as of 2026-05-29**. Tutorials shipped:
`tutorials/2026-05-streaming-logger-walkthrough.md` (how to log every call
with cost, latency, and full text) and
`tutorials/2026-05-pii-redaction-llm-gateway.md` (drop-in PII redaction
for any API call).

The fifth cluster is **safety and compliance**. Foundation: "Defence-in-depth
for LLM applications" (shipped 2026-06-01). Snippet: `llm_firewall.py`
(shipped 2026-06-01). Next additions: a tutorial on indirect prompt injection
via RAG, and a follow-up article on multi-turn context attacks.

The clusters are the spine of the SEO strategy in `SEO.md`. Cross-linking
across the four clusters is more valuable than absolute volume.

## Metrics to track once we have analytics

The plan is to add a simple analytics integration (Plausible or Umami)
once we have ten articles live. Until then the proxy signals are GitHub
stars on snippets, referral traffic to specific articles from external
links, and direct feedback (issues, PRs).

The first quantitative goal is 200 GitHub stars on the repository as a
whole and 1,000 monthly readers on the foundation articles by end of Q3
2026. Both numbers are deliberately modest; the value of this asset comes
from cumulative depth over years, not from a launch spike.

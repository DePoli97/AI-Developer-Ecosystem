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
| 3    | Tutorial  | RAG starter end-to-end (runnable script)                       | sqlite fts5 embeddings rag       | tutorials/2026-05-rag-starter-runnable.md + snippets/python/rag_sqlite_starter.py |
| 3    | Workflow  | LLM-driven changelog generator from commit history             | automated changelog generator    | workflows/llm-changelog-from-git.md                                        |
| 4    | Article   | What hybrid retrieval actually buys you (with numbers)         | hybrid retrieval bm25 embeddings | articles/2026-05-hybrid-retrieval-numbers.md                               |
| 4    | Snippet   | Reciprocal rank fusion as a 30-line utility                    | reciprocal rank fusion python    | snippets/python/reciprocal_rank_fusion.py                                  |

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
FTS5 plus embeddings write-up. Status: workflow shipped; tutorial and
foundation article pending.

The fourth cluster is **cost and observability**. Foundation: a cost
engineering field guide. Tutorial: a streaming logger walkthrough. Snippet:
`token_cost_estimator.py` and `streaming_response_logger.py`. Status:
snippets shipped; foundation article and tutorial pending.

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

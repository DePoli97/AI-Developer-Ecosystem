# Cookbook

Worked, end-to-end examples that wire several snippets together into a
small but real system. Each example is runnable, with an offline self-test
that does not require an API key.

## Index

- [`documentation_search_agent.py`](./documentation_search_agent.py) -
  Builds a hybrid (FTS5+embeddings) index over a Markdown documentation
  folder and answers a natural-language question by retrieving the top
  chunks. Optional Claude step rewrites them into an answer; the offline
  mode just returns the retrieved passages.

- [`eval_on_commit.py`](./eval_on_commit.py) - A pre-commit-style script
  that runs the minimal eval harness against a tiny prompt registry and
  exits non-zero on regression. Designed to be wired into a Git hook or
  a GitHub Action.

- [`cost_budget_guard.py`](./cost_budget_guard.py) - A wrapper that
  enforces a per-process USD budget on LLM calls. Uses the token cost
  estimator to convert usage to dollars and aborts on overrun. Self-test
  exercises both "under budget" and "over budget" paths.

Each example is small enough to read in one sitting. The shared building
blocks live under `snippets/python/`.

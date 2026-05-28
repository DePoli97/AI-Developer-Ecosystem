---
title: "LLM-as-Judge: The Eval Pattern Every AI Engineer Needs"
date: 2026-05-28
tags: [evals, llm-as-judge, testing, quality, anthropic, openai, python]
description: How to use a language model as an automated evaluator for open-ended outputs — with working code and real trade-offs.
---

# LLM-as-Judge: The Eval Pattern Every AI Engineer Needs

Evaluating LLM outputs is hard. Exact-match fails the moment you care
about semantics. Human review doesn't scale. The answer most production
teams land on: **use a second LLM to judge the first one**.

This pattern — called LLM-as-judge — is now the de facto standard for
automated evals at companies running Claude, GPT-4, and Gemini in
production.

---

## The problem with traditional evals

Classic software tests compare outputs to expected strings. That works
fine for:
- structured extraction (JSON, tables)
- code that can be run and tested
- classification with known labels

It breaks for:
- open-ended Q&A
- summarisation quality
- tone and helpfulness
- factual accuracy in long responses
- any task where multiple valid answers exist

---

## How LLM-as-judge works

You write a **rubric** (a natural language scoring guide), then send
each `(question, candidate_answer, rubric)` triple to a judge model.
The judge returns a numeric score and a rationale.

```python
score, rationale = judge(
    question="Explain gradient descent to a 10-year-old.",
    answer=model_output,
    rubric=(
        "Award 1.0 if the explanation is accurate AND uses an analogy "
        "a child would understand. Award 0.5 if accurate but too technical. "
        "Award 0.0 if inaccurate."
    ),
)
```

The judge never sees the "right answer" — it evaluates quality against
your rubric, just like a human grader would.

---

## Rubric design is everything

A vague rubric produces noisy scores. Good rubrics are:

**Specific** — name the exact criteria:
> "Award 1.0 if all three requested items appear in the output."

Not:
> "Award 1.0 if the answer is good."

**Anchored** — explain what each score value means:
> "1.0 = fully correct and concise; 0.5 = correct but missing context;
> 0.0 = incorrect or off-topic"

**Single-dimensional** — if you care about both accuracy and tone, run
two separate judges rather than combining them in one rubric.

---

## Choosing the judge model

| Scenario               | Judge model               | Why                                   |
|------------------------|---------------------------|---------------------------------------|
| High-stakes regressions | Same or stronger model   | Best judgment quality                 |
| Bulk automated CI       | Haiku / smaller model    | Cost-efficient, fast enough           |
| Comparing two models    | Third-party / different  | Avoid self-serving bias               |

For most teams: use Claude Haiku as the judge for speed and cost,
promote to Opus/Sonnet when you need higher confidence.

---

## Known failure modes

**Position bias** — the judge favours whichever answer appears first.
Fix: shuffle or use two calls with reversed order.

**Self-serving bias** — a Claude judge may prefer Claude outputs.
Fix: benchmark your judge on known good/bad pairs before trusting it.

**Rubric gaming** — verbose answers score higher even if wrong.
Fix: add "penalise unnecessary verbosity" to your rubric.

**Token limit** — long candidate answers get truncated.
Fix: chunk or summarise before judging, or increase `max_tokens`.

---

## Production setup

1. Store rubrics in version control alongside your prompts.
2. Run judges in CI on every prompt change.
3. Alert if `mean_score` drops more than 0.1 from baseline.
4. Save all `JudgmentResult` objects to a database for trend analysis.
5. Periodically sample 5% of judgments for human review to detect
   judge drift.

---

## Code

Drop-in implementation: [`snippets/python/eval_judge_llm.py`](../snippets/python/eval_judge_llm.py)

Pairs well with: [`snippets/python/minimal_eval_harness.py`](../snippets/python/minimal_eval_harness.py)

---

## Monetisation note

LLM-as-judge infrastructure is a natural paid add-on:
- hosted eval dashboard
- rubric library (pre-written for common use cases)
- CI integration (GitHub Action)
- regression alerts via webhook

---

*Part of the [AI Developer Ecosystem](../README.md) — practical AI
engineering, openly built.*

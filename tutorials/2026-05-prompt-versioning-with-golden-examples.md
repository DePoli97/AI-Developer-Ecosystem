# Prompt versioning with golden examples

*A 20-minute guide to tracking prompt changes like code changes — with a lightweight test harness that catches regressions before they reach production.*

---

## The problem

You ship a prompt. It works. Two weeks later you tweak a sentence to fix one edge case and quietly break three others you had forgotten about. There is no error, no exception — just subtly wrong LLM outputs that only surface in production or in a user complaint.

Prompt engineering without versioning is the equivalent of editing production code directly, without tests, on a Friday afternoon.

This guide fixes that with three simple ingredients:

1. **Version-controlled prompt files** — one file per prompt, named with a version slug.
2. **A golden-example library** — a small JSON file of `(input, expected_output)` pairs that document what "correct" looks like for each version.
3. **A runner script** — a ~150-line Python file that loads prompts, runs them against your LLM, and scores each output against expectations.

No external eval framework required. No paid tooling. Runs in CI.

---

## Prerequisites

```
python 3.10+
anthropic>=0.28
```

Install:

```bash
pip install anthropic
```

Set your API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Step 1 — Structure your prompt directory

Create a folder called `prompts/` at the root of your project. Store each prompt as a plain `.txt` file. Use a naming convention that includes the version:

```
prompts/
  summarizer_v1.txt
  summarizer_v2.txt
  classifier_v1.txt
  golden_examples.json
```

A prompt file is just the system prompt text — no JSON wrapping, no code fences.

**`prompts/summarizer_v1.txt`**

```
You are a concise summarizer. Given a piece of text, return a single paragraph of at most three sentences that captures the key idea. Do not add commentary or preamble. Output only the summary paragraph.
```

**`prompts/summarizer_v2.txt`**

```
You are a concise summarizer. Given a piece of text, return a single paragraph of at most three sentences that captures the key idea.

Rules:
- Output only the summary paragraph — no preamble, no labels.
- Use plain language. Avoid jargon unless it appears in the source text.
- If the source text is shorter than three sentences, return it verbatim.
```

The second version adds explicit rules to handle edge cases discovered after v1 shipped.

---

## Step 2 — Write your golden examples

Create `prompts/golden_examples.json`. Each entry maps a `prompt_file` to a list of test cases. Each test case has an `input` dict and an `expected` object describing what a passing response looks like.

```json
[
  {
    "prompt_file": "summarizer_v2.txt",
    "cases": [
      {
        "id": "long-article",
        "input": {
          "text": "Retrieval-Augmented Generation (RAG) combines a retrieval step with a generative model. The retrieval step pulls relevant documents from a corpus; the generative step synthesises an answer from those documents. This separation lets you update the knowledge base without retraining the model, and it gives you a citation trail back to source documents."
        },
        "expected": {
          "max_sentences": 3,
          "must_not_contain": ["As an AI", "Here is", "Summary:"],
          "must_contain_any": ["retrieval", "generation", "RAG", "documents"]
        }
      },
      {
        "id": "short-input-verbatim",
        "input": {
          "text": "RAG is fast."
        },
        "expected": {
          "exact_match": "RAG is fast."
        }
      },
      {
        "id": "no-preamble",
        "input": {
          "text": "Large language models are trained on vast corpora of text scraped from the web, books, and other sources. They learn statistical patterns and can generate coherent text, answer questions, and perform many language tasks."
        },
        "expected": {
          "must_not_contain": ["Sure", "Of course", "Here", "Summary", "Certainly"]
        }
      }
    ]
  }
]
```

The `expected` object supports four check types (all optional, composable):

| Key | Meaning |
|-----|---------|
| `max_sentences` | Response must have at most N sentence-ending marks |
| `must_contain_any` | At least one string must appear (case-insensitive) |
| `must_not_contain` | None of these strings may appear (case-insensitive) |
| `exact_match` | Response must equal this string exactly (stripped) |

---

## Step 3 — Run the harness

The runner is in `snippets/python/prompt_version_runner.py`. Copy or symlink it into your project, then:

```bash
# Verify the evaluator logic without any API calls
python snippets/python/prompt_version_runner.py --self-test

# Run the full golden-example suite
python snippets/python/prompt_version_runner.py \
  --prompts-dir prompts/ \
  --golden prompts/golden_examples.json \
  --model claude-haiku-4-5-20251001
```

Sample output:

```
============================================================
Prompt : summarizer_v2.txt   (3 case(s))
Model  : claude-haiku-4-5-20251001
============================================================

  [PASS] long-article
        Output: 'RAG combines a retrieval step with a generative model...'

  [PASS] short-input-verbatim
        Output: 'RAG is fast.'

  [FAIL] no-preamble
        ! must_not_contain: found forbidden strings ['Here']
        Output: "Here is a concise summary of the text..."

============================================================
Results: 2/3 passed, 1 failed
============================================================
```

The script exits with code `1` on any failure — useful for CI gates.

---

## Step 4 — Wire it into CI

**`.github/workflows/prompt-tests.yml`:**

```yaml
name: Prompt golden-example tests
on: [push, pull_request]

jobs:
  prompt-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install anthropic
      - run: python snippets/python/prompt_version_runner.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

Every pull request that edits a prompt file now automatically runs the golden-example suite. A regression blocks the merge.

---

## Versioning strategy

Keep both prompt files in the repository while you build confidence in a new version. Once v2 has passed all tests for two weeks in production, delete v1 and remove its golden examples.

Tag git commits when you promote a prompt version:

```bash
git tag prompt/summarizer/v2
git push origin prompt/summarizer/v2
```

---

## What to put in golden examples

Write a case for every failure you have seen or can imagine:

- The happy path (normal input, expected output)
- Edge-case inputs (empty string, very short text, code blocks, markdown)
- Failure modes you have observed (preamble hallucination, refusals, format drift)
- Boundary cases for numeric constraints (exactly three sentences)

Aim for five to ten cases per prompt. More is fine; fewer is risky.

---

## Extensions

**Fuzzy scoring.** Replace `exact_match` with a semantic-similarity check using `sentence-transformers` and cosine similarity when you need "close enough" rather than exact. The evaluator function in the snippet is designed to be extended with new check types.

**Model comparison.** Add a `--model` flag loop to run the same suite against multiple models. Useful when evaluating whether a cheaper model can replace a more expensive one for a given task.

**Regression history.** Save the runner's exit code and case counts to a JSON artifact on each CI run. Over time you get a history of prompt flakiness across versions.

---

## Summary

| What you built | Why it matters |
|---|---|
| Versioned prompt files | Diffs, blame, history — same as code |
| Golden-example JSON | Living documentation of what correct looks like |
| Runner script | Automated regression detection before production |
| CI integration | Prevents prompt regressions from merging |

Prompt versioning is one of those practices that feels like overhead until the first time it saves you from a silent regression. Add it early, when the golden-example library is still small and cheap to maintain.

---

*Related: [Build your first Claude tool-use agent](./2026-05-claude-tool-use-starter.md) · [Parse structured JSON output reliably](./2026-05-parse-structured-llm-output.md)*

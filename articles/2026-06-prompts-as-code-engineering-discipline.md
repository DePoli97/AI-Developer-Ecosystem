# Prompts as Code: Treat Your Prompts Like the Engineering Artefacts They Are

*Published: June 2026 · Cluster: Prompt Engineering as Code*

Most teams that adopt LLMs start with prompts in a Google Doc, then a
Notion page, then buried in a `.env` file, then copy-pasted across three
microservices with subtle per-team drift. By the time the model changes or
a regression surfaces, no one knows which version of the prompt is running
in production, what it was six weeks ago, or why it changed.

This article makes the case that prompts deserve the same engineering
discipline as code: version control, structured review, automated testing,
and staged rollout. It then walks through a practical setup you can adopt
without a specialised platform.

---

## Why prompts rot

A prompt is a program. It has observable inputs (the user message, context
variables), a runtime (the model), and outputs (the completion). Changing
any of those three changes the behaviour of your application.

Unlike a Python function, a prompt has no type checker, no linter, and no
obvious unit test boundary. The temptation is to treat it as configuration
rather than code. That is the mistake.

Prompts rot for four concrete reasons:

**1. No diff history.** A prompt stored in a database cell or a secret
manager gets overwritten. Six weeks later, when a regression surfaces,
there is no `git blame`, no PR, no reviewer. The only record is "it worked
before and now it does not."

**2. Implicit coupling to model version.** A prompt tuned on Claude 3
Sonnet may behave differently on Claude 3.5 Sonnet, even if the
advertised capabilities overlap. If the prompt and the model version are
not co-versioned, a model upgrade silently changes your application.

**3. No test suite.** Prompts are usually manually tested against two or
three examples in a playground. A structural change that breaks 15% of
edge cases ships undetected because no one ran a regression suite.

**4. Team drift.** Different services copy-paste a "base prompt" and each
team tweaks it independently. Within weeks the divergence is large enough
that a fix in one place does not propagate to the others.

---

## The prompts-as-code model

The fix is straightforward: apply to prompts the same practices you
already apply to code.

### 1. Store prompts in version control

Put every system prompt, every few-shot template, every structured output
spec in a file in your repository. Organise by function:

```
prompts/
  summariser/
    v1.txt
    v2.txt
    current -> v2.txt   # symlink or a pointer file
  code_reviewer/
    system.txt
    output_schema.json
  classifier/
    system.txt
    examples.jsonl
```

Each file is a single, complete prompt. No string interpolation at runtime
beyond filling labelled slots (`{{user_code}}`, `{{context}}`). The slot
names are the interface contract.

### 2. Review prompts in pull requests

Every prompt change goes through a PR. The description must answer:

- What behaviour is being changed and why?
- Which model version was this tested against?
- What is the expected impact on the golden-example suite?

This forces the author to articulate the intent before merging. It also
means future you can read the PR and understand why `v3` changed the
instruction ordering.

### 3. Pin model versions in code

Treat the model identifier as a dependency version, not a "use latest"
call:

```python
# bad — silently breaks when the provider updates "latest"
client.messages.create(model="claude-latest", ...)

# good — explicit, co-reviewable with the prompt
MODEL = "claude-sonnet-4-6"
client.messages.create(model=MODEL, ...)
```

The model constant lives next to the prompt file it was tuned on. When
you upgrade the model, you open a PR that touches both.

### 4. Write a golden-example suite

For each prompt, maintain a small set of (input, expected_output) pairs
that encode the behaviour you care about. This is not a benchmark — it is
a regression guard. Aim for 10–50 examples per prompt, covering the happy
path and the failure modes you have seen in production.

The test runner does not need LLM-as-judge for most cases. A structured
output check or a substring presence check is enough:

```python
# simplified runner — full version at snippets/python/prompt_version_runner.py
for example in golden_examples:
    response = call_llm(system=prompt, user=example["input"])
    assert example["check"](response), f"Failed: {example['input']}"
```

Run this in CI on every PR that touches a prompt file. A failing golden
example is a breaking change.

### 5. Stage rollout with prompt feature flags

When you have confidence in a new prompt version, you do not flip all
traffic at once. Use the same feature flag or canary infrastructure you
use for code:

```python
def get_system_prompt(user_id: str) -> str:
    if feature_flags.is_enabled("summariser_v3", user_id):
        return prompts.load("summariser/v3.txt")
    return prompts.load("summariser/v2.txt")
```

Log which prompt version produced each completion. Attach the version
identifier to your observability traces. Then you can compare error rates,
latency, and quality signals across versions before full rollout.

---

## The minimal file layout

You do not need a dedicated prompt management platform to do this. A
repository with the following structure is enough to start:

```
prompts/
  README.md             # prompt catalogue, owner, model pin, test count
  summariser/
    v2.txt              # current production prompt
    v3.txt              # candidate under A/B test
    examples.jsonl      # golden examples (input + assertion)
  code_reviewer/
    system.txt
    output_schema.json
    examples.jsonl
tests/
  test_prompts.py       # CI runner
scripts/
  eval_prompt.py        # local eval helper
```

The `README.md` in `prompts/` is the catalogue. It lists every prompt,
which model it was tuned on, who owns it, and how many golden examples it
has. When a new engineer joins, this file is the map.

---

## Versioning scheme

Use a simple integer version in the filename (`v1`, `v2`, `v3`). Do not
use semantic versioning for prompts — there are no public API consumers to
consider, and the overhead outweighs the benefit.

A version bump is required whenever:

- The instruction text changes beyond a typo fix.
- The output schema changes.
- The model pin changes.
- You add or remove few-shot examples.

Minor tweaks (punctuation, whitespace, rephrasing that does not change
semantics) can land in-place with a clear commit message, no version bump
required. Use judgment.

---

## Golden examples as documentation

The `examples.jsonl` file does double duty. It is a test suite and it is
documentation. An engineer reading the prompt for the first time can look
at the examples to understand the expected behaviour faster than by parsing
the instruction text alone.

Keep the examples realistic. Pull them from production logs (redacted if
necessary). Edge cases you invented in a vacuum are less valuable than
edge cases the model actually encountered.

Format:

```jsonl
{"input": "Summarise this PR: ...", "expected_keywords": ["refactor", "adds test"], "max_words": 50}
{"input": "Summarise this PR: ...", "expected_keywords": ["bug fix"], "max_words": 50}
```

The assertion can be as simple as keyword presence or as sophisticated as
a secondary LLM judge call. Start simple. Add complexity only when simple
assertions miss real regressions.

---

## CI pipeline sketch

```yaml
# .github/workflows/prompt-ci.yml
name: Prompt regression
on:
  pull_request:
    paths:
      - 'prompts/**'
      - 'tests/test_prompts.py'

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install anthropic
      - run: python tests/test_prompts.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

This runs on every PR that touches a prompt file. It takes one or two
minutes and costs a few cents. It catches regressions before they reach
production.

---

## What this does not solve

Prompts-as-code is a discipline, not a platform. It does not give you:

- **Semantic diff views.** You see the text diff; you do not see a summary
  of behavioural change. That requires an eval framework.
- **Automatic prompt optimisation.** DSPy and similar frameworks can
  optimise prompts against a metric, but they require a clear metric and
  a labelled dataset. The practices here are prerequisites, not
  alternatives.
- **Latent failure modes.** A prompt can pass all golden examples and
  still fail on a distribution of inputs you have not seen. Golden
  examples guard against known regressions, not unknown distributions.

These are real limitations. Address them as the system matures. The
discipline described here is the foundation: without it, the more
sophisticated tooling has nothing to build on.

---

## Summary

| Practice | Tool | Effort |
|---|---|---|
| Store prompts in files | Git | Negligible |
| Review changes in PRs | GitHub / GitLab | Negligible |
| Pin model versions in code | Python constant | Negligible |
| Golden-example regression suite | `prompt_version_runner.py` | Low |
| CI on prompt changes | GitHub Actions | Low |
| Staged rollout with flags | Feature flag system | Medium |

Start with the first three. They are free, take an afternoon to set up,
and immediately eliminate the "which version is in production?" class of
problems. Add the regression suite when you have had your first
prompt-related incident. Add staged rollout when the application is
customer-facing and the blast radius of a bad prompt matters.

Prompts are code. Treat them accordingly.

---

## Related content

- [Tutorial: Prompt versioning with golden examples](../tutorials/2026-05-prompt-versioning-with-golden-examples.md)
- [Snippet: `prompt_version_runner.py`](../snippets/python/prompt_version_runner.py)
- [Article: A field guide to LLM cost engineering](./2026-05-llm-cost-engineering-field-guide.md)
- [Article: Defence-in-depth for LLM applications](./2026-06-llm-safety-defense-in-depth.md)

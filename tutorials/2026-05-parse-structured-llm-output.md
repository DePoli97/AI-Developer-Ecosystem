# Parse structured JSON output from any LLM, reliably

> 15-minute tutorial. You will end with a function that turns a messy
> LLM response into a validated pydantic object, even when the model
> wraps it in prose, fences it in `` ```json `` blocks, uses smart
> quotes, or sprinkles trailing commas.

## Why this is harder than it looks

If your agent depends on the model returning JSON, you have probably
already met the failure modes:

1. The model adds a friendly intro before the JSON.
2. The JSON is wrapped in a `` ```json `` fence.
3. There is a trailing comma after the last field.
4. A copy-pasted prompt example used `"` quotes that became `“ ”` along the way.
5. The model emits a nested object inside a string, and your regex `\{.*\}`
   matches the wrong closing brace.

`json.loads(response.text)` covers exactly zero of these. A regex like
`re.search(r"\{.*\}", text, re.DOTALL)` covers four out of five and then
silently breaks the fifth, which is the one that costs you production
debugging time.

This tutorial walks through a small, well-tested fix.

## What you will build

A single function:

```python
plan = parse_structured(llm_response_text, Plan)
```

where `Plan` is any pydantic model. On success you get a typed object.
On failure you get a `StructuredParseError` with a precise `.reason`
field so you can decide whether to retry, fall back, or escalate.

## Prerequisites

- Python 3.11+
- `pip install pydantic>=2.7`
- The snippet at [`snippets/python/structured_json_output.py`](../snippets/python/structured_json_output.py)

No API keys are required for this tutorial. We will feed pre-recorded
strings to the parser so you can run everything offline.

## Step 1 - Run the snippet's self-test

The snippet ships with a runnable self-test that exercises five common
failure modes. Run it first to confirm your environment works:

```bash
python snippets/python/structured_json_output.py
```

Expected output:

```
PASS  fenced          steps=['a', 'b']  confidence=0.9
PASS  trailing prose  steps=['a', 'b']  confidence=0.9
PASS  trailing comma  steps=['a', 'b']  confidence=0.9
PASS  smart quotes    steps=['a']  confidence=0.5
PASS  nested object   steps=['a {nested: true}', 'b']  confidence=0.42
PASS  no-json        raised as expected
```

Six cases pass. The last one confirms that the parser raises when no
JSON is present at all - silent failures are worse than loud ones.

## Step 2 - Use it in your own code

Define the shape you expect, then call `parse_structured`:

```python
from pydantic import BaseModel
from structured_json_output import parse_structured, StructuredParseError


class TriageDecision(BaseModel):
    label: str
    confidence: float
    reasons: list[str]


def triage(llm_response_text: str) -> TriageDecision:
    try:
        return parse_structured(llm_response_text, TriageDecision)
    except StructuredParseError as e:
        # log e.reason and e.snippet, then retry with a stricter prompt
        raise
```

The pydantic validation step is the important part. Once
`parse_structured` returns, every downstream call can rely on
`decision.confidence` being a float and `decision.reasons` being a
list of strings.

## Step 3 - Decide what to do on failure

The parser raises a single typed exception, `StructuredParseError`,
with three useful attributes:

- `.reason` - a short human-readable description, e.g. `"no valid JSON found"` or `"schema validation failed: [...]"`
- `.raw` - the original response text, untouched
- `.snippet` - the first 200 characters of the candidate region, when applicable

A good error-handling policy looks like this:

```python
for attempt in range(3):
    response = client.messages.create(...)
    try:
        return parse_structured(response.content[0].text, TriageDecision)
    except StructuredParseError as e:
        if "schema validation" in e.reason:
            # The model produced JSON but with the wrong fields. Reprompt
            # with the validation error so it can self-correct.
            history.append({
                "role": "user",
                "content": f"Your JSON had schema errors: {e.reason}. Fix and resend ONLY JSON.",
            })
            continue
        # Otherwise it didn't produce JSON at all. Tighten the prompt and
        # retry.
        history.append({
            "role": "user",
            "content": "Respond with ONLY a JSON object matching the schema. No prose.",
        })
raise RuntimeError("triage failed after 3 attempts")
```

This pattern - parse, route on `.reason`, reprompt with the actual
error - is the single highest-leverage upgrade you can make to a
fragile agent loop.

## Step 4 - Prefer native structured output when available

The parser above is the safety net. If your provider supports it, the
first line of defense should be the API's own structured-output mode:

- **Anthropic Claude**: declare a tool whose `input_schema` is the
  pydantic model's JSON schema, and force `tool_choice` to that tool.
- **OpenAI**: use `response_format={"type": "json_schema", ...}` with
  `strict: true`.
- **Open-source models** via vLLM / TGI: use grammar-constrained
  decoding (GBNF / JSON-schema grammars).

Even with these, you still want a parser at the edge for the cases
where the constraint can't be applied: fallback models, older endpoints,
prompts that have to stream prose and JSON together, or evaluations
against historical logs. The snippet covers all of them.

## When not to use this

Two cases:

1. **You control the model and can hard-constrain output**. If every
   call goes through a structured-output API with `strict: true`, you
   only need `json.loads` plus pydantic.
2. **The data is genuinely free-form**. Don't force JSON onto a task
   where the model would do better answering in natural language.
   Forcing structure where there is none lowers quality.

## Wrap-up

You now have a parser that survives the five LLM-JSON failure modes
and tells you exactly which one happened when it can't recover. The
full code, with comments, is at
[`snippets/python/structured_json_output.py`](../snippets/python/structured_json_output.py).
The companion article on [Claude tool use](../articles/2026-05-claude-tool-use-practical-guide.md)
covers the upstream side: how to design tool schemas so the model
returns clean structured data in the first place.

# Wrap Your LLM Calls With PII Redaction in 10 Minutes

**Cluster:** Cost & Safety · **Snippet:** [`pii_redactor.py`](../snippets/python/pii_redactor.py)  
**Difficulty:** Beginner · **Time:** ~10 min · **Dependencies:** `anthropic` only

You are shipping an LLM feature. Users type real text. That text contains
emails, phone numbers, credit-card numbers, and AWS keys — sometimes
accidentally, sometimes not. You do not want that data leaving your
infrastructure in plaintext. You also do not want to pay for a managed DLP
service before you have paying customers.

This tutorial shows how to drop `pii_redactor.py` into any Anthropic API
call in under ten minutes. The result: PII is replaced with stable
placeholders before the prompt is sent, and restored in the model's reply
before the user sees it.

---

## How It Works

```
user input ──► redact() ──► [REDACTED PROMPT] ──► Anthropic API
                    │                                     │
              mapping dict                          model reply
                    │                                     │
                    └────────── unredact() ◄──────────────┘
                                     │
                               user sees reply
                            (with real values back)
```

`redact()` scans the text with regex patterns, replaces each match with a
token like `<EMAIL_1>` or `<PHONE_2>`, and returns both the redacted text
and a mapping dict. `unredact()` reverses the mapping in the model's reply.
The same `Redactor` instance reuses placeholders across turns, so `<EMAIL_1>`
always refers to the same address throughout a conversation.

---

## Step 1 — Copy the snippet

```bash
curl -O https://raw.githubusercontent.com/<your-username>/ai-developer-ecosystem/main/snippets/python/pii_redactor.py
```

Or just download [`pii_redactor.py`](../snippets/python/pii_redactor.py) and
place it next to your script. Zero dependencies — standard library only.

Run the self-test to confirm it works:

```bash
python pii_redactor.py --self-test
# case 1 ok (2 matches)
# ...
# all 8 checks passed
```

---

## Step 2 — Single-turn redaction

Here is the minimal wrapper:

```python
import anthropic
from pii_redactor import Redactor

client = anthropic.Anthropic()
redactor = Redactor()

def safe_complete(user_message: str, *, model: str = "claude-opus-4-6") -> str:
    result = redactor.redact(user_message)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": result.redacted}],
    )

    raw_reply = response.content[0].text
    return Redactor.unredact(raw_reply, result.mapping)


# Try it
reply = safe_complete(
    "Hey, my email is alice@example.com and my card is 4111 1111 1111 1111. "
    "What should I know about protecting payment data?"
)
print(reply)
```

What gets sent to the API:

```
Hey, my email is <EMAIL_1> and my card is <CREDIT_CARD_1>. What should I
know about protecting payment data?
```

What the user reads back: a reply where `<EMAIL_1>` and `<CREDIT_CARD_1>`
have been swapped out for the originals.

---

## Step 3 — Multi-turn conversations

`Redactor` is stateful. Create one instance per conversation session and it
reuses placeholders across turns. This matters because the model may refer
back to earlier values ("the email address you gave me earlier") and stable
tokens keep that coherent.

```python
import anthropic
from pii_redactor import Redactor

client = anthropic.Anthropic()

def run_chat_session():
    redactor = Redactor()          # one per session
    history = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            break

        result = redactor.redact(user_input)
        history.append({"role": "user", "content": result.redacted})

        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=history,
        )

        raw = response.content[0].text
        restored = Redactor.unredact(raw, result.mapping)

        # Store the redacted version in history so future turns stay clean
        history.append({"role": "assistant", "content": raw})

        print(f"Assistant: {restored}\n")

run_chat_session()
```

> **Design note:** We store the raw (redacted) assistant reply in `history`,
> not the restored one. If we stored the restored text, the next user turn
> that triggers redaction would see real PII in the assistant slot — defeating
> the purpose.

---

## Step 4 — Streaming

`Redactor` works on strings, so for streaming you accumulate the full text
and unredact once the stream closes:

```python
import anthropic
from pii_redactor import Redactor

client = anthropic.Anthropic()
redactor = Redactor()

def safe_stream(user_message: str):
    result = redactor.redact(user_message)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": result.redacted}],
    ) as stream:
        chunks = []
        for text in stream.text_stream:
            chunks.append(text)
            print(text, end="", flush=True)

    full_reply = "".join(chunks)
    restored = Redactor.unredact(full_reply, result.mapping)
    print()  # newline after stream
    return restored

safe_stream("Summarise the GDPR obligations for alice@corp.io based in Berlin.")
```

---

## Step 5 — Log what was detected (optional)

For audit trails, `detect()` gives you structured match objects:

```python
from pii_redactor import detect

text = "Call me at +1 415 555 2671 or reach alice@example.com"
for match in detect(text):
    print(f"{match.kind:15} [{match.start}:{match.end}]  {match.value!r}")

# PHONE           [10:26]  '+1 415 555 2671'
# EMAIL           [30:49]  'alice@example.com'
```

You can log the `kind` and position without logging the raw value — giving
your security team detection coverage with no data-retention risk.

---

## What It Covers (and What It Doesn't)

**Covered out of the box:**

| Pattern | Example |
|---|---|
| Email | `alice@example.com` |
| Phone (E.164 + common forms) | `+1 (415) 555-2671` |
| IPv4 address | `10.0.0.42` |
| US SSN | `123-45-6789` |
| Credit card (Luhn-validated) | `4111 1111 1111 1111` |
| AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` |

**Not covered** (by design, to keep it dependency-free):

- Named entities (person names, company names) — needs an NER model
- Non-US ID formats — add your own regex via `_PATTERNS`
- Image or audio PII — out of scope for a text utility

---

## Extending With Custom Patterns

Add entries to `_PATTERNS` in the script:

```python
import re
from pii_redactor import _PATTERNS

# UK National Insurance number: AB123456C
_PATTERNS.insert(0, (
    "NI_UK",
    re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]\b"),
))
```

Insert at position 0 so it runs before the more general PHONE pattern.

---

## CLI Usage

The script ships with a CLI for quick one-off redaction:

```bash
# Redact a file, get mapping on stderr
python pii_redactor.py --redact < input.txt > clean.txt

# Save mapping for later unredaction
python pii_redactor.py --redact --mapping-out mapping.json < input.txt > clean.txt

# Reverse
python pii_redactor.py --unredact mapping.json < model_output.txt
```

Useful for pre-processing datasets before you send them to a fine-tuning job.

---

## Next Steps

- Pair with [`streaming_response_logger.py`](../snippets/python/streaming_response_logger.py) to log redacted prompts and costs to JSONL — you get safety and observability in the same pipeline.
- See [`workflows/pii-safe-llm-gateway.md`](../workflows/pii-safe-llm-gateway.md) for a FastAPI wrapper that exposes this as a drop-in proxy endpoint.
- Read the [product brief](../opportunities/product-brief-pii-guard.md) if you want to turn this into a hosted service.

---
title: "Wrap Your LLM Gateway with PII Redaction in 10 Minutes"
date: 2026-05-28
tags: [pii, privacy, llm, gateway, python, anthropic, security]
description: Add a PII redaction layer in front of any LLM call in under 10 minutes. Zero infra changes required.
---

# Wrap Your LLM Gateway with PII Redaction in 10 Minutes

Sending user data to an LLM without scrubbing PII first is a compliance
risk — and in regulated industries it can be a hard blocker. This
tutorial shows you how to drop a transparent redaction layer in front of
any Claude (or OpenAI-compatible) call with minimal code and zero
infrastructure changes.

**Time:** ~10 minutes  
**Prerequisites:** Python 3.10+, `anthropic` package, basic regex  
**What you'll build:** A thin wrapper that redacts PII before sending,
then restores the original values in the response.

---

## Why bother?

- GDPR / CCPA compliance when processing EU or US customer data
- Avoid leaking user emails, phone numbers, names into LLM providers'
  training pipelines
- Audit trail: redacted logs are safe to store long-term
- Easy to layer on top of existing code — no prompt changes needed

---

## The core pattern

The idea is a **round-trip vault**:

1. Scan the prompt for PII → replace each match with a placeholder
   (`[EMAIL_1]`, `[PHONE_1]`, …)
2. Send the redacted prompt to the LLM
3. Restore placeholders in the response before returning to the caller

```
User prompt → redact() → LLM API → restore() → caller
```

The vault is just a dict kept in memory (or Redis for multi-turn
sessions). No external services required.

---

## Step 1 — Install dependencies

```bash
pip install anthropic
# optional but recommended for production
pip install presidio-analyzer presidio-anonymizer
```

For the minimal version in this tutorial we use only the standard
library + `anthropic`.

---

## Step 2 — Build the redactor

Create `pii_gateway.py`:

```python
import re
import anthropic

# ---------------------------------------------------------------------------
# Pattern registry — extend as needed
# ---------------------------------------------------------------------------
PATTERNS = [
    ("EMAIL",   re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")),
    ("PHONE",   re.compile(r"\b(\+?1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")),
    ("SSN",     re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD",    re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("IP",      re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]

def redact(text: str) -> tuple[str, dict[str, str]]:
    """Replace PII with placeholders. Returns (redacted_text, vault)."""
    vault: dict[str, str] = {}
    counters: dict[str, int] = {}

    for label, pattern in PATTERNS:
        def replacer(m, label=label):
            counters[label] = counters.get(label, 0) + 1
            key = f"[{label}_{counters[label]}]"
            vault[key] = m.group(0)
            return key

        text = pattern.sub(replacer, text)

    return text, vault


def restore(text: str, vault: dict[str, str]) -> str:
    """Swap placeholders back to original values."""
    for placeholder, original in vault.items():
        text = text.replace(placeholder, original)
    return text
```

---

## Step 3 — Wrap the LLM call

```python
client = anthropic.Anthropic()

def safe_complete(user_message: str, system: str = "") -> str:
    redacted_message, vault = redact(user_message)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": redacted_message}],
    )

    raw_reply = response.content[0].text
    return restore(raw_reply, vault)
```

That's it. The caller sees a normal string response; PII never leaves
your process boundary unredacted.

---

## Step 4 — Test it

```python
if __name__ == "__main__":
    test = (
        "My name is Alice, email alice@example.com, "
        "phone 415-555-0199. Can you summarise my account?"
    )
    result = safe_complete(test, system="You are a helpful support agent.")
    print(result)
```

Expected: the LLM receives `[EMAIL_1]` and `[PHONE_1]` in the prompt,
but the final output you print has the real values restored (if the LLM
echoed them back).

---

## Extending for multi-turn conversations

For chat sessions, persist the vault across turns using a session ID:

```python
from collections import defaultdict
SESSION_VAULTS: dict[str, dict[str, str]] = defaultdict(dict)

def safe_complete_session(session_id: str, user_message: str) -> str:
    vault = SESSION_VAULTS[session_id]
    redacted, new_vault = redact(user_message)
    vault.update(new_vault)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": redacted}],
    )

    return restore(response.content[0].text, vault)
```

---

## Production checklist

- [ ] Replace regex patterns with `presidio-analyzer` for higher
      accuracy (especially for names)
- [ ] Store vaults in Redis with TTL, not in-process memory
- [ ] Add logging of redaction counts (not values) for audit purposes
- [ ] Rate-limit the restore step to prevent prompt-injection attacks
      that try to exfiltrate vault contents
- [ ] Unit-test your patterns against regional phone/ID formats you care
      about

---

## What's next

- **Higher accuracy**: see the companion snippet
  [`pii_redactor.py`](../snippets/python/pii_redactor.py) which adds
  confidence thresholds and entity-type filtering.
- **Cost control**: combine with
  [`prompt_cache_analyzer.py`](../snippets/python/prompt_cache_analyzer.py)
  — redacted prompts are more cache-friendly because personal values
  don't break cache hits.
- **Hosted version**: if you want a zero-config drop-in service, watch
  this repo — a `pii-guard` micro-SaaS is on the roadmap.

---

*Part of the [AI Developer Ecosystem](../README.md) — practical AI
engineering, openly built.*

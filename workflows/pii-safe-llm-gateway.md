---
title: "PII-Safe LLM Gateway Workflow"
date: 2026-05-28
tags: [pii, privacy, gateway, workflow, compliance, llm]
description: End-to-end workflow for routing LLM calls through a PII redaction layer.
---

# PII-Safe LLM Gateway Workflow

A repeatable pattern for organisations that need to send user-generated
content to an LLM provider without leaking personally identifiable
information.

---

## Architecture

```
User input
    │
    ▼
[Redactor]  ─── replaces PII with placeholders ──► vault {[EMAIL_1]: "alice@..."}
    │
    ▼
[LLM API]   ─── receives sanitised prompt ───────► response with placeholders
    │
    ▼
[Restorer]  ─── swaps placeholders back ─────────► final response to user
```

---

## Steps

### 1. Pattern detection

Run the input through a regex or NLP-based detector. Priority entity
types to cover first:

| Entity    | Risk level | Common regex approach              |
|-----------|------------|------------------------------------|
| Email     | High       | RFC-5321 simplified                |
| Phone     | High       | E.164 + national formats           |
| SSN / NIN | Critical   | Country-specific patterns          |
| Credit card | Critical | Luhn-checkable 13-16 digit strings |
| IP address | Medium   | `\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}` |
| Full name | Medium     | NLP (presidio) recommended         |

### 2. Vault creation

Store each original value keyed by its placeholder in a dict (or Redis
for distributed setups). Use per-session vaults so placeholders are
consistent across multi-turn chats.

```python
vault["[EMAIL_1]"] = "alice@example.com"
vault["[PHONE_1]"] = "415-555-0199"
```

### 3. LLM call

Send the redacted string to the LLM. The model never sees raw PII.
Instruct the model in the system prompt to preserve placeholders if
echoing back user data:

> "If the user's message contains tokens like [EMAIL_1], treat them as
> opaque identifiers and include them verbatim in your response if
> you need to reference them."

### 4. Response restoration

After receiving the LLM's response, do a simple string replacement to
swap every placeholder back to its original value.

### 5. Audit logging

Log redaction *counts* (not values) per request:

```json
{"session": "abc123", "redacted": {"EMAIL": 1, "PHONE": 1}, "ts": "..."}
```

This gives you an audit trail without storing PII in logs.

---

## Failure modes to handle

| Failure                          | Mitigation                                   |
|----------------------------------|----------------------------------------------|
| LLM reformats placeholder        | Normalise response before restore step       |
| Multi-turn vault grows unbounded | TTL in Redis; cap vault size per session     |
| False positive redaction         | Tune confidence thresholds in presidio       |
| Prompt injection via vault key   | Validate placeholder format with strict regex|

---

## Code

- Tutorial: [`tutorials/2026-05-pii-safe-llm-gateway.md`](../tutorials/2026-05-pii-safe-llm-gateway.md)
- Snippet: [`snippets/python/pii_redactor.py`](../snippets/python/pii_redactor.py)

---

## Monetisation angle

This workflow is the foundation of a `pii-guard` micro-SaaS:
a hosted proxy that intercepts any OpenAI/Anthropic HTTP call, redacts
PII, and forwards it — zero code changes needed by the caller.
See [`opportunities/product-brief-pii-guard.md`](../opportunities/product-brief-pii-guard.md).

---

*Part of the [AI Developer Ecosystem](../README.md).*

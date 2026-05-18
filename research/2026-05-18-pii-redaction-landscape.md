# Field notes: the PII redaction landscape for LLM pipelines

Date: 2026-05-18

A short scan of where to put a redaction step in an LLM pipeline, and
what the realistic options look like in May 2026 for a small team
shipping something that touches user data. This is a field note, not
an article - dated, opinionated, and short.

## The three places redaction can live

Redaction happens at one of three points, and the choice is mostly
about how much trust you place in each layer.

The first is **client-side**, before the prompt leaves the user's
device. This is the strongest privacy story but the hardest to keep
in sync with a fast-moving regex set, because every client release
needs the new patterns.

The second is **gateway-side**, in your API server before the request
hits the model. This is the default for almost everyone. It is easy
to update, easy to audit, and the only request payload the model sees
is the redacted one.

The third is **model-side**, where you ask the model to redact and
trust it. This is the worst option in May 2026: the model will leak
the original PII into its own reasoning chain, and any output you log
will contain the raw values. Useful only as a defence in depth.

## What the realistic options look like

For a small team, the choice today is roughly:

**Roll your own regex layer.** Cheap, fast, and fine for the common
cases (emails, phones, IPs, US SSNs, credit cards with Luhn). The
weak spot is anything contextual: names, addresses, free-text dates of
birth. The `pii_redactor.py` snippet that landed today is in this
category. It is the right starting point and it stays the right
answer for a long time.

**Microsoft Presidio.** Open source. Adds a NER model on top of the
pattern layer so it catches names and locations that regex misses.
Heavier dependency, but the cost is paid once at deploy time. Good
upgrade path from a regex-only layer because the abstractions overlap.

**Cloud DLP (AWS Comprehend, Google DLP, Azure PII detection).**
Pay-per-call, broad pattern coverage, locale-aware out of the box.
The trade-off is that the redaction step itself becomes a network hop
to a third party, which can be a non-starter for some compliance
regimes. Useful for batch jobs over historical data; less attractive
in the hot path.

**Dedicated commercial tools (Skyflow, Nightfall, Cloaked).** Worth
looking at once you outgrow Presidio. Usually bundled with vault and
tokenisation services. The pricing model is the differentiator here,
not the underlying tech.

## Practical recommendation

For a team building an LLM feature today:

Start with a regex layer at the gateway. Make sure the placeholders
are stable across calls within a session, and reversible. Log only the
redacted text; never log the raw user message and never log the
mapping alongside the redacted message.

When you start missing names, addresses, or anything contextual,
upgrade to Presidio in place. Keep the same gateway shape and the
same placeholder convention; only the detector changes.

Only consider a cloud DLP or a commercial tool when you have a
specific reason (locale coverage, audit certification, or vault
integration). The default assumption should be that you do not need
one for the first year.

## Monetisation angle for this repository

The `pii_redactor.py` snippet is the natural front door to a paid
product if we ever build one. The realistic monetisation paths from
here are, in order of likelihood:

1. A hosted gateway-as-a-service that wraps this redactor plus
   Presidio plus an audit log. Tiny SaaS, target hobbyists and small
   teams. Pricing: usage-based, with a generous free tier.
2. A CLI (`pii-guard`) on PyPI that adds dedicated patterns per
   locale (EU VAT IDs, UK NHS numbers, etc.) and a paid pattern pack
   for high-stakes industries.
3. A consulting-style "PII audit" template under
   `opportunities/` that we can sell as a one-off to small teams.

The snippet stays free and good. The paid path is in the operational
layer around it, not in the code itself. That is consistent with the
project's stated strategy in `MONETIZATION.md`.

## What to read next if going deeper

The Microsoft Presidio documentation has a useful taxonomy of PII
entity types. The NIST SP 800-122 publication is the canonical
reference for what counts as PII in a US-regulated context. The
GDPR Art. 4(1) definition is the equivalent for the EU.

None of those are linked here because the goal of this field note is
to leave a pointer for a future session, not to be a survey article.

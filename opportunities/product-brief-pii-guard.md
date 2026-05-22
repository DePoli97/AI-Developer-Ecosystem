# Product brief: pii-guard

A drop-in PII redaction layer for any team sending real user data through
a hosted LLM. Captured as a brief while the underlying open-source snippet
in this repository is still fresh; the paid product is not built yet.

## One-line pitch

Stop sending customer names, emails, and credit cards to OpenAI and
Anthropic without thinking about it. Three lines of Python, reversible
on the response side, audit-ready out of the box.

## Target customer

B2B SaaS engineering teams who have shipped at least one LLM feature and
are now meeting a procurement, legal, or compliance gate before the next
one. Healthcare-adjacent, fintech-adjacent, and HR-adjacent products are
the highest-intent buyers because their DPAs explicitly call out
third-party processors. Indie builders shipping a consumer app with EU
or California users are a secondary segment.

## Problem

The default path is: prompt the model with raw user content. The right
path is: redact PII on the way out, restore placeholders on the way
back, log every redaction event for the audit trail. Almost nobody
does this on day one because the engineering effort to do it well is a
two-week project nobody scopes correctly, and the off-the-shelf tools
either over-redact (cloud DLP) or are too low-level (Presidio without a
pipeline).

The 2026-05 research note in `research/2026-05-18-pii-redaction-landscape.md`
documents the buy/build trade-offs. The short summary: there is a gap
between "a regex with a name" and "an enterprise platform priced at
$30k/year" that nobody serves well, and that gap is where pii-guard
lives.

## Components in the box

The open-source primitive is already shipped:
`snippets/python/pii_redactor.py`. It handles emails, phone numbers,
Luhn-validated credit cards, IPs, names, and stable reversible
placeholders, with std-lib only and a passing self-test.

The paid product wraps that primitive in three layers the snippet
deliberately does not include.

A pluggable policy layer. Per-tenant rules - "redact names except when
they appear in a recipient field", "preserve last four digits of credit
cards", "redact birth dates only for EU users". Configured in YAML,
versioned, with a dry-run mode that emits the diff without modifying
the request.

A pattern pack registry. Per-locale and per-domain pattern bundles
(US SSN, UK NHS number, IT codice fiscale, FR INSEE, EU IBAN, US
medical record numbers). Each pattern pack is independently versioned
and ships with its own test fixtures.

A drop-in proxy mode. A FastAPI service that sits between the customer's
app and the LLM provider, redacting on the way out and restoring on the
way back, with structured audit logs to stdout (or an S3 bucket the
customer owns). The Python SDK exposes the same primitives for in-process
use when a proxy is overkill.

## Pricing

Three tiers, anchored against the cost of the audit project pii-guard
prevents.

The library tier is free and open-source. The current snippet plus a
modest amount of additional polish stays MIT-licensed forever; this is
the marketing surface.

The pattern-pack tier is $19 per locale per month, billed annually. Each
pattern pack is independently maintained and tested. A buyer typically
needs one (their home market) or three (US, EU, plus their largest
non-domestic market).

The proxy tier is $99 per month for the self-hosted FastAPI service plus
all pattern packs, or $299 per month for a hosted instance with audit
log retention and a tenant dashboard. Volume discounts above 1M
requests per month.

## Distribution

The library lives in this repository and on PyPI as `pii-guard`. The
pattern packs and the proxy live in a private repo with a Stripe-driven
license check. The hosted proxy is a Cloudflare Workers + D1 deployment;
the cost of running it is dominated by egress, not compute.

Launch sequence. First, ship the standalone `pii-guard` PyPI package
that wraps the snippet with a friendlier API (estimated effort: one
weekend). Second, when it has 500+ weekly downloads, write a launch post
on Hacker News titled "pii-guard: the PII-redaction layer your LLM
proxy is missing". Third, only after the post lands, build the pattern
packs and the proxy. Premature productisation is the failure mode for
this class of tool.

## Why this is monetizable and the agent kit might not be

Two structural differences from the Claude Agent Kit brief. PII
redaction is a recurring compliance line item, not a one-time tooling
purchase, so the LTV is higher and the willingness to pay survives
beyond the initial integration. And procurement is the customer for
the proxy tier; once a security review is passed, the product enters a
"do not switch" zone that the agent kit cannot reach. Both of these
matter more than the absolute size of the user base.

## Open questions to resolve before launch

Whether the pattern packs should be a paid tier or part of the proxy
tier. The argument for splitting them out is that the library users
will sometimes want one locale pack without paying for the proxy. The
argument against is the additional billing complexity.

Whether to wrap the snippet in a thin async API or keep it sync. Most
LLM gateway code is async; the redactor is fast enough that the sync
path is fine, but a `redact_async` wrapper would be polite.

Whether to publish a small SOC 2 readiness checklist as a launch lead
magnet. The answer is probably yes - the customer who buys pii-guard
also wants to know what else they need.

## Decision

Do not build the paid product yet. Ship the PyPI package as a weekend
project once the open-source snippet has been linked from one external
post. Re-evaluate the pattern pack and proxy work when the PyPI package
has 500+ weekly downloads and at least one inbound enquiry. The
research note in `research/` is the standing reference; this brief is
the standing implementation plan.

## Cross-references

- Open-source primitive: `snippets/python/pii_redactor.py`
- Research note: `research/2026-05-18-pii-redaction-landscape.md`
- Sibling brief: `opportunities/product-brief-claude-agent-kit.md`
- Affiliate adjacency: `opportunities/affiliate-devtools-shortlist.md`

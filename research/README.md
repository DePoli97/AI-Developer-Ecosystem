# Research

A scratchpad for notes on AI / devtools trends, market gaps, and observations that may turn into articles or products later. Items here are not commitments; they are evidence we are collecting.

## Index

- [`agent-frameworks-landscape-2026-05.md`](./agent-frameworks-landscape-2026-05.md) - Field comparison of the agent frameworks worth considering for production work, with recommendations by team profile.
- [`2026-05-18-pii-redaction-landscape.md`](./2026-05-18-pii-redaction-landscape.md) - Where redaction should sit in an LLM pipeline, the realistic options in May 2026 (roll-your-own, Presidio, cloud DLP, commercial vaults), and the most plausible monetisation path out of the new `pii_redactor.py` snippet.

## Open notes

Long-tail SEO around AI-engineering keywords (`claude tool use`, `prompt versioning`, `agent eval`) is under-served. Most top results are vendor docs or surface-level overviews. Room exists for opinionated, runnable content.

Most "agent framework" projects optimize for breadth, not for production discipline. A small set of patterns (validated tool inputs, step limits, structured tool errors, traces) shows up repeatedly in real systems. There is room to be the canonical write-up for each.

Browser automation with LLMs is being marketed faster than its failure modes are documented. Idempotency, recoverable actions, and auth boundaries are recurring gaps.

Evals and observability for LLM apps are still a fragmented space. Lightweight, file-based eval harnesses that fit in a single repo are under-represented compared to heavy SaaS offerings.

Cost engineering as a discipline is younger than it should be. Most teams underinvest in per-request cost tracking and per-feature token budgets until it bites. There is a clear opening for a canonical write-up plus tooling.

## Process

When a note here matures into something concrete (an article angle, a tool idea, a market gap with a clear customer), it gets promoted into `IDEAS.md` and, when ready, into `ROADMAP.md`.

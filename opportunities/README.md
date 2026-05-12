# Opportunities

A short list of concrete commercial opportunities we are tracking. Each entry has a hypothesis, the evidence behind it, and a small next step that would either validate or kill the idea.

## 1. Claude tool-use starter template

Hypothesis: developers building Claude agents repeatedly re-implement the same loop with the same mistakes. A polished, opinionated starter with structured tool errors, validation, tracing, and tests would save them days.

Evidence: the article and snippet shipped in this repo, the relative absence of opinionated open-source examples, and the steady volume of "how do I structure my Claude agent" questions on developer forums.

Next step: ship the open-source `templates/claude-tool-use-starter/`, gather GitHub stars and issues, decide later whether a paid "production edition" makes sense.

## 2. Prompt registry, file-based

Hypothesis: small teams want prompt versioning without adopting a SaaS. A tiny, file-based prompt store with a clean client library is enough to displace ad-hoc string constants in code.

Evidence: recurring conversations about prompt drift; existing solutions skew heavyweight; many teams reject managed prompt platforms for compliance reasons.

Next step: ship `templates/prompt-registry-starter/` with both TypeScript and Python clients. Measure adoption via stars and forks before considering a SaaS version.

## 3. Newsletter for AI builders

Hypothesis: a low-frequency, high-signal newsletter aimed at AI engineers (not at general "AI news" consumers) can grow to a few thousand subscribers within a year if the content stays focused.

Evidence: most AI newsletters chase hype; the engineering-focused niche is comparatively underserved.

Next step: defer until the repository has a baseline of articles. Then launch a landing page and a monthly digest sourced from this repo and from a tight curated list.

## Process

An opportunity stays here only while it has a defined next step. Once it ships, it moves into `ROADMAP.md`. Once it is killed, it gets a one-line obituary so the project does not retry it without reason.

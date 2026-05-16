# Product brief: Production Claude Agent Kit

A polished, opinionated starter kit aimed at developers who want to ship
a real internal tool or product feature on top of the Claude Agent SDK.
This brief captures the shape of a paid product that could plausibly
emerge from the open-source work already in this repository.

## One-line pitch

The fastest way to get from "we want to add an agent" to "the agent is in
production and we can debug it on Monday".

## Target customer

Engineering teams of two to twenty people building B2B software, who have
decided to ship a Claude-powered agent and would rather buy six weeks of
plumbing for $49 than build it themselves. Indie founders building
internal tools fall in the same bucket.

## Problem

The first agent that works in a demo is almost never the agent that works
in production. The gap is mostly plumbing: structured tool errors, retry
and rate-limit handling, cost tracking per session, prompt versioning,
eval harness, observability that lets you debug a failure on Monday
morning. Every team rebuilds this. None of them enjoy it.

## Components in the box

The kit packages the assets already in this repository plus a small set
of additions that turn them into a coherent system.

Reusable from this repo: `claude_agent_sdk_starter.py`,
`rate_limit_aware_client.py`, `streaming_response_logger.py`,
`minimal_eval_harness.py`, `prompt_version_runner.py`,
`token_cost_estimator.py`, `retry_with_backoff.py`,
`structured_json_output.py`, the Claude API starter template, the
prompt versioning tutorial, and the Agent SDK quickstart.

New additions required for the paid product: a production-shaped
project skeleton that wires all of these together, a "cookbook" of five
worked examples (a code-review agent, a customer-support triage agent, a
documentation-search agent, a CI helper, a Slack assistant), a one-hour
video walkthrough, a private Discord or GitHub Discussions area for
buyers, and 30 days of email support included.

## Pricing

Two tiers. The kit alone at $49 (one-time, lifetime updates). The kit
plus a private 60-minute setup call at $199. The price is anchored
against the time the customer would otherwise spend; the calculation is
trivial for anyone paying engineering salaries.

## Distribution

Launch on Hacker News with a "Show HN" post that links the open-source
sub-components, with the paid product framed honestly as the convenient
bundle. Cross-post to r/SideProject, r/ClaudeAI, r/LLMDevs. Twitter/X
thread tied to a real working demo. Email any newsletter subscribers
when that asset exists.

## Open questions to resolve before launch

How much of the kit stays free and how much sits behind the paywall. The
current instinct is: every individual snippet stays free and open-source;
the integrated project skeleton, the cookbook, the video, and the
support are the paid bundle. This keeps the repository functioning as
the marketing asset without making the paid product feel thin.

Whether to package the kit as a GitHub template repository (private with
buyer access) or as a downloadable zip. Template repository wins for
update delivery; zip wins for simplicity.

Refund policy. Default to a no-questions-asked 14-day refund. The
support cost of being lenient is lower than the trust cost of being
strict.

## Decision

Do not build the paid product yet. Continue producing free content for
another six to eight weeks. Revisit when the repository has at least
twenty pieces, a thousand monthly readers on the foundation articles,
and at least one external link from a publication the target customer
reads.

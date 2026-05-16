# A field guide to LLM cost engineering

*The patterns and numbers that move per-request cost down without
making your product worse. Aimed at engineers who have shipped at least
one LLM feature to production and now have a bill to defend.*

Published: 2026-05.  Reading time: 14 minutes.

## Why this matters now

Two things are true at the same time. Foundation models are cheaper than
they have ever been: sonnet-class inputs at roughly $3 per million tokens,
haiku-class at roughly $0.80, opus at $15. And: a real product running a
single agent loop with retrieval, tool use, and a long system prompt can
burn $0.05 to $0.30 per request without trying. At 100,000 requests a
month that is $5,000 to $30,000 a month. The gap between "feasible
business" and "expensive science project" is almost always closed by
cost engineering, not by waiting for cheaper models.

This guide is the playbook. Six tactics, in the order I would apply them
to a real product, with the engineering effort and the typical savings
you should expect.

## Tactic 1: cap output tokens

This is the lowest-effort win and it is almost always uncapped on a
first implementation. Most providers default to 4096 output tokens or
higher. Most of your responses will not get anywhere near that. Setting
a per-call `max_tokens` that matches the format you actually need cuts
output spend immediately.

The reason this matters is the price asymmetry: output tokens are
typically 3-5x more expensive than input tokens. A request with 5,000
input tokens and 2,000 output tokens at sonnet pricing costs
$0.015 + $0.030 = $0.045, of which two-thirds is the output. Drop the
output cap to a realistic 600 tokens and the same call costs
$0.015 + $0.009 = $0.024. Forty-six percent saved, zero change to the
prompt.

The mistake people make is setting one global `max_tokens` for every
call. Set it per use case. A "rewrite this paragraph" call needs maybe
400 output tokens; an agent step that includes a chain-of-thought needs
1500; a final summary needs 800. Each gets its own number.

Engineering effort: under an hour. Typical savings: 20-40% on output
spend, which is 15-30% on total spend.

## Tactic 2: route by task difficulty

Every product has a long tail of easy requests and a short head of hard
ones. Running them all through sonnet is the default and the wrong
default. Send easy requests to haiku, hard ones to sonnet, and only the
ones that need it to opus.

The right way to decide is empirical: ship the same prompt against all
three tiers, run them through your eval suite, pick the cheapest model
that meets your quality bar. The rule that emerges almost every time is
"haiku for retrieval-supported QA and classification, sonnet for
multi-step reasoning and tool use, opus for the few percent of requests
where you have already detected that something hard is happening".

The escalation pattern is the one that lets you ship this safely.
Default to the cheap tier; track a confidence signal (output validation,
self-evaluation, retrieval coverage); on low confidence, retry on the
next tier up. The
[model_router snippet](../snippets/python/model_router.py) in this
repository ships with a composable scorer and a `low_confidence_escalator`
that implements exactly this pattern.

Numbers for a realistic mix (say 60% easy, 35% medium, 5% hard) at
2,000 input + 500 output tokens per call:

- All sonnet: $0.0135 per request.
- Routed (haiku/sonnet/opus): $0.0048 per request.

That is a 64% reduction. The engineering effort is two or three weeks
the first time you do it (mostly because of the eval work, not the code).

## Tactic 3: use prompt caching for stable system prompts

Anthropic prompt caching makes repeated reads of a stable prefix cost
10% of the input price. If you have a 5,000-token system prompt that
every request reads, and you set up caching, your effective input cost
on those 5,000 tokens drops by 90% after the first request.

The cache is per-window and per-prefix. The discipline you need is:
keep your system prompt at the top, keep the few-shot examples right
after it, never inject changing content (date, user info, retrieved
docs) before the stable prefix. Stick the variable stuff into the user
message at the end.

For a system with 4,000 tokens of stable prefix, 1,000 tokens of varying
content, and 400 tokens of output, at sonnet pricing:

- No cache: $0.015 input + $0.006 output = $0.021 per request.
- With cache on the 4,000-token prefix (after first request):
  $0.0012 (cached) + $0.003 (uncached input) + $0.006 = $0.0102 per
  request.

That is 51% savings on every request after the first one. The
engineering effort is a few hours, plus a one-off audit of your prompt
to confirm the prefix is truly stable. The
[prompt_cache_analyzer snippet](../snippets/python/prompt_cache_analyzer.py)
in this repository reports your actual cache-hit ratio and USD savings
from a JSONL log so you can verify the numbers in production.

## Tactic 4: compact long agent conversations

An agent loop that runs for ten steps with five tools and 2KB of tool
results per step accumulates a 30-40KB conversation. At sonnet pricing
each subsequent step processes that whole accumulated context, so step
ten costs roughly ten times step one. This is the single biggest cost
trap in production agent systems.

The fix is conversation compaction: once you cross a token threshold,
replace the old turns with a single compacted summary, keep the last
few turns verbatim. The
[conversation_compactor snippet](../snippets/python/conversation_compactor.py)
in this repository does exactly this with a deterministic heuristic
summary. In production you usually run the summary through a cheap
model (haiku is fine) to get a higher-quality compaction.

Effect on a ten-step agent loop processing a 2KB tool result per step:

- No compaction: ~110,000 cumulative input tokens across the ten steps.
- Compaction at 50% of context with 4 recent turns kept: ~45,000
  cumulative input tokens.

That is roughly 60% cumulative input savings, with a one-time haiku
call per compaction (under one cent each). Engineering effort: a day
to integrate, a few days to tune the summary template.

## Tactic 5: batch when latency allows

Batch APIs price input and output at roughly 50% of synchronous
pricing on most providers. If your work is not latency-sensitive
(overnight reports, large catalogue annotations, training-data
generation), batching is a flat 50% off with almost no engineering
cost.

The mistake here is assuming "real time" when the user does not
actually need it. A daily summary email does not need a synchronous
call; queue the request and process the queue once a day. A bulk
re-classification job does not need a synchronous call; submit it as
a batch.

Engineering effort: a few hours to wire a queue and a daily cron.
Typical savings: 50% on the batched portion of traffic, which for many
products is 10-30% of total volume.

## Tactic 6: shape prompts before sending them

Two patterns in this tier. First, compress the prompt itself: collapse
filler phrases, drop adjacent restatements, strip polite scaffolding
the model does not need. The
[prompt_compressor snippet](../snippets/python/prompt_compressor.py) in
this repository does this mechanically and reports savings; on a real
production system prompt it typically shaves 10-30% of tokens with no
quality change.

Second, retrieve smarter: a 2,000-token retrieval result that is
60% relevant beats a 6,000-token result that is 25% relevant, and
costs less. Tighten your retrieval before you tighten your model
choice. Hybrid retrieval (FTS5 + embeddings + RRF, as shown in the
[RAG starter workflow](../workflows/rag-starter-sqlite-fts5.md))
typically lifts recall@10 by 5-15 points over pure vector retrieval,
which lets you retrieve fewer chunks at the same quality.

Engineering effort: a half-day to compress prompts, one or two weeks
for a retrieval upgrade. Typical savings: 15-25% on input spend.

## Putting it together

Stack the tactics on top of each other and the savings compound.
Starting from a sonnet-default, max-tokens-uncapped, no-cache,
unbounded-context baseline at $0.10 per request:

- Cap outputs:              $0.065 per request (-35%)
- Route to haiku on easy:   $0.034 per request (-66%)
- Add prompt caching:       $0.018 per request (-82%)
- Compact agent context:    $0.013 per request (-87%)
- Compress system prompt:   $0.011 per request (-89%)

Eighty-nine percent reduction with no batch optimisation. At 100,000
requests per month that takes the bill from $10,000 to $1,100. The
engineering effort across all five steps is somewhere between four and
eight engineer-weeks for a small team. That ROI is not subtle.

## What not to do

Do not chase token counts at the expense of evaluation. Cost engineering
without a quality bar produces faster, cheaper, worse software. Run
every change through an eval suite before you ship it; the
[minimal eval harness snippet](../snippets/python/minimal_eval_harness.py)
in this repository is enough scaffolding to catch the obvious
regressions.

Do not chase mid-call optimisations before fixing your routing. The
biggest lever by an order of magnitude is "right model for the job".
Spend the eval time first.

Do not assume the cheapest model is the right cheap model. Haiku is
excellent at retrieval-supported QA, weaker at multi-step reasoning,
and surprisingly good at classification. Test, do not assume.

## Where to start tomorrow morning

If you take three things away, take these. First, add a `max_tokens`
audit pass: every LLM call in your codebase, every value made
deliberate. This is a one-hour task and it is almost always worth 20%.

Second, instrument cost per request. You cannot optimise what you do
not measure. The
[token_cost_estimator snippet](../snippets/python/token_cost_estimator.py)
takes a raw API response and returns a dollar figure; the
[streaming_response_logger snippet](../snippets/python/streaming_response_logger.py)
appends a JSONL record with cost per call. Together they are a half-day
of integration work.

Third, run the prompt cache analyzer over a week of production traffic
and find out what your real cache-hit ratio looks like. If it is under
70% and your system prompt is large, fixing that is the easiest big
win you have available.

## Companion code in this repository

- [token_cost_estimator.py](../snippets/python/token_cost_estimator.py)
- [streaming_response_logger.py](../snippets/python/streaming_response_logger.py)
- [prompt_cache_analyzer.py](../snippets/python/prompt_cache_analyzer.py)
- [model_router.py](../snippets/python/model_router.py)
- [conversation_compactor.py](../snippets/python/conversation_compactor.py)
- [prompt_compressor.py](../snippets/python/prompt_compressor.py)
- [cost_budget_guard.py](../cookbook/cost_budget_guard.py)
- [minimal_eval_harness.py](../snippets/python/minimal_eval_harness.py)
- [RAG starter workflow](../workflows/rag-starter-sqlite-fts5.md)

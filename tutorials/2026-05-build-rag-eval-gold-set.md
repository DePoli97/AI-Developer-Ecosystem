# Build a 50-query gold set for your RAG system

*A pragmatic walkthrough for building the evaluation harness that all
the other RAG improvements depend on. No magic, no LLM-as-judge, no
synthetic-query generators. Just fifty real queries, labelled by hand,
that let you say with a straight face whether your last change made
things better or worse.*

Published: 2026-05.  Reading time: 14 minutes.  Difficulty: intermediate.

## Why this exists

Every RAG project hits the same wall. You ship the first version with a
dense retriever, it feels fine on the three queries you tried in the
demo, and then a stakeholder asks "is it actually working?" and you have
nothing to say. The next month you swap to hybrid, add a reranker, tune
chunk size, and at every step the only honest answer to "did that help?"
is "I think so".

The fix is not a benchmark. Public benchmarks (BEIR, MTEB) tell you how
generic models behave on generic corpora. They do not tell you whether
*your* corpus, *your* users, and *your* retriever line up. The fix is a
small, hand-labelled gold set on your own data that you re-run on every
change. Fifty queries is enough to detect changes of about five points
of nDCG@10 with reasonable confidence, and you can build it in an
afternoon.

This tutorial walks through that afternoon end to end. The output is a
single JSON file you commit to your repository, plus a small evaluation
script. The companion code lives in
`snippets/python/cross_encoder_reranker.py` and
`snippets/python/reciprocal_rank_fusion.py`; this tutorial focuses on
the *labelling and measurement* loop, which is where most teams stall.

## What you will produce

By the end of the walkthrough you will have:

A `eval/gold.json` file with fifty queries, each annotated with one or
more relevant document IDs from your corpus. A `eval/run.py` script
that loads the gold set, runs every retrieval strategy under test, and
prints a small table of nDCG@10 and MRR. A discipline of re-running
that script before merging any change to the retrieval stack.

The whole thing should be under 200 lines of Python and one JSON file.
If yours grows larger, you are probably overengineering it.

## Step 1: choose the queries (60 minutes)

The single biggest mistake is making up queries. You will subconsciously
write queries that your current retriever already answers well, because
those are the queries that come to mind. The gold set you produce that
way is worthless: every change will look neutral because the queries
were already pre-solved.

Use real queries instead. The sources, in rough order of preference:

Your production logs, if you have them. Take the last 500 queries, strip
duplicates and PII, and sample 80. Read them. Drop the unparseable ones
(timeouts, garbage). Keep about 50.

Your customer-support inbox. Search tickets for "I tried to find" or
"I couldn't get an answer about". These are queries that already failed
once, which is exactly the population you want to improve.

Your team's Slack history. The questions people ask each other are the
queries they would have asked the docs if the docs were better.

If you have *none* of the above, you are pre-launch. In that case, the
least bad option is to spend the hour writing fifty questions yourself,
but doing it in a specific way: open ten random documents from your
corpus, and for each one write five questions a real user might ask
that the document could plausibly answer. Then write the questions
*without* looking at the document, from memory of the topic. This
forces some natural paraphrasing.

Aim for variety along three axes. Length: a mix of two-word queries
("token limits") and full sentences ("how do I increase the maximum
context size for a Claude tool call"). Intent: how-to, definitional,
troubleshooting, comparative. Vocabulary: some queries that use the
exact terms in your docs, some that use a layperson's words. If 45 of
your 50 queries are how-tos in domain vocabulary, your gold set will
make a lexical retriever look invincible and you will ship the wrong
thing.

## Step 2: label the relevant documents (90 minutes)

For each query you need at least one document ID that is "relevant".
Relevance is a judgment call. Use a two-level scheme to keep the
labelling fast:

**Relevant**: this document contains a direct, self-sufficient answer
to the query. A user reading just this document would leave satisfied.

**Partially relevant**: this document is on the right topic and would
help, but the user would probably need to combine it with another
document, or the answer is buried in a long passage.

Skip a three-or-more-level scheme. The marginal value of distinguishing
"highly relevant" from "very highly relevant" is near zero, and the
extra cognitive load slows labelling by 3x.

Run your current best retriever on each query, take the top 20 results,
and label them. This is called pooling, and it is what TREC has done
for thirty years. It is much faster than reading the full corpus per
query. The downside is that pooling biases the gold set toward what
your current retriever finds; you can partially mitigate this by also
labelling the top 10 results of a *different* retriever (lexical if
your default is dense, or vice versa). The union of the two top-N lists
is your candidate pool.

Be ruthless about queries where no document in the corpus answers the
question. These are not bad queries; they are signal that your corpus
has a gap. Move them to a separate `eval/gaps.json` file and treat them
as content tasks, not retrieval tasks. Including them in the retrieval
gold set will only inject noise.

For a 50-query gold set with a pool of ~30 candidates per query, expect
about 90 minutes of focused labelling. If it takes longer, your
relevance criteria are too fuzzy; tighten the definition.

## Step 3: store the gold set in a format you can re-read in two years

The format that has survived every team I've seen is dead-simple JSON,
one query per object, with stable document IDs and human-readable
metadata.

```json
{
  "version": 1,
  "created": "2026-05-25",
  "corpus_revision": "git:8a3b1c2",
  "queries": [
    {
      "id": "q001",
      "text": "how do I increase the max token limit for a tool call",
      "intent": "how-to",
      "relevant": ["doc_142", "doc_207"],
      "partially_relevant": ["doc_88"],
      "notes": "from prod logs 2026-05-12"
    }
  ]
}
```

Three details matter. The `corpus_revision` field pins the labels to a
specific snapshot of your documents; without it, the gold set silently
rots as you reindex. The `notes` field captures provenance so future
you remembers why this query is in the set. Stable document IDs (a
content hash, or a slugified path) survive reindexing; numeric row IDs
do not.

Commit `gold.json` to the repository. Treat it as code: review changes
to the gold set in pull requests, because changing the gold set
changes the meaning of every measurement that follows.

## Step 4: the evaluation script

The script does three things: load the gold set, run each retriever
under test, compute nDCG@10 and MRR per query, then average. Two
metrics, not ten. Adding more metrics is the most common form of
analysis paralysis in retrieval work; pick two and live with them.

```python
import json
import math
from pathlib import Path

def dcg(relevances):
    return sum(r / math.log2(i + 2) for i, r in enumerate(relevances))

def ndcg_at_k(retrieved_ids, relevant_set, partial_set, k=10):
    gains = []
    for doc_id in retrieved_ids[:k]:
        if doc_id in relevant_set:
            gains.append(1.0)
        elif doc_id in partial_set:
            gains.append(0.5)
        else:
            gains.append(0.0)
    ideal = sorted(
        [1.0] * len(relevant_set) + [0.5] * len(partial_set),
        reverse=True,
    )[:k]
    if not ideal:
        return 0.0
    return dcg(gains) / dcg(ideal)

def mrr(retrieved_ids, relevant_set):
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_set:
            return 1.0 / (i + 1)
    return 0.0

def evaluate(gold_path, retrievers):
    gold = json.loads(Path(gold_path).read_text())
    results = {name: {"ndcg": [], "mrr": []} for name in retrievers}
    for q in gold["queries"]:
        rel = set(q["relevant"])
        partial = set(q.get("partially_relevant", []))
        for name, retrieve in retrievers.items():
            hits = retrieve(q["text"], k=10)
            results[name]["ndcg"].append(ndcg_at_k(hits, rel, partial))
            results[name]["mrr"].append(mrr(hits, rel))
    print(f"{'retriever':<25} {'nDCG@10':>10} {'MRR':>10}")
    for name, scores in results.items():
        ndcg_avg = sum(scores["ndcg"]) / len(scores["ndcg"])
        mrr_avg = sum(scores["mrr"]) / len(scores["mrr"])
        print(f"{name:<25} {ndcg_avg:>10.3f} {mrr_avg:>10.3f}")
    return results
```

The `retrievers` argument is a dict mapping a name to a callable that
takes a query string and returns a list of document IDs. That signature
keeps the evaluation script decoupled from any specific retrieval
library; you can swap BM25, dense, hybrid, or reranked variants by
adding entries to the dict.

Run it before every retrieval change. If the change does not improve
the average nDCG@10 by at least 0.02, do not merge it; the latency and
complexity cost is real and the quality benefit is in the noise.

## Step 5: the variance check

A single number across 50 queries hides a lot. Always also print the
*per-query delta* between the variant under test and the baseline, and
read the bottom 5. If a change adds 0.04 to the average but degrades
ten queries by 0.20 each, you have not improved the system, you have
shifted the failure mode.

A two-line extension to the script:

```python
deltas = sorted(
    (b - a, q["text"]) for a, b, q in zip(
        results["baseline"]["ndcg"],
        results["variant"]["ndcg"],
        gold["queries"],
    )
)
for delta, text in deltas[:5]:
    print(f"  {delta:+.3f}  {text}")
```

The five worst-regressed queries are where you spend the next hour.
They will tell you more about your retriever than the average ever
will.

## What to skip on the first pass

LLM-as-judge for relevance labels. Tempting because it scales, but it
will inherit the same biases as your retriever, especially when the
retriever and the judge come from the same model family. Use it later
to *extend* a hand-labelled set, never to *replace* one.

Synthetic queries generated from your documents. Same problem: the
generator writes queries that use the document's vocabulary, which
inflates lexical retrievers and biases the set toward queries your
current system already handles.

Click-through models from production. Useful eventually, but only after
you have enough traffic that the signal beats the noise. For most
teams that is six months out, minimum. Start with hand labels.

A web UI for labelling. A flat JSON file edited in your IDE is faster
than any UI you can build in a day. Wait until you have a labelling
team larger than one person before investing.

## Maintenance

Re-label the bottom 5 queries every quarter. These are the queries
where your retriever struggles, and they are also the ones where your
labels are most likely to be wrong (you were tired by query 45). A 30-
minute quarterly pass keeps the gold set honest.

Add 10 new queries from production every quarter, and retire 10 old
ones. The gold set should drift with the product. A frozen gold set
from 2024 measures your 2024 product, not your 2026 product.

Track the corpus revision. Every time you reindex with materially
different chunking or new documents, mark the gold set with the new
revision and spot-check 10 random queries to verify the labels still
make sense. Most of the time they do; when they don't, you need to
relabel before trusting any numbers.

## What this unlocks

Once you have this loop in place, every claim in the retrieval cluster
of articles becomes empirical for *your* data. The hybrid retrieval
write-up
([hybrid retrieval, with numbers](../articles/2026-05-hybrid-retrieval-numbers.md))
shows that hybrid beats dense by 5-10 points of nDCG on mixed-intent
corpora. The cross-encoder reranker snippet
([cross_encoder_reranker.py](../snippets/python/cross_encoder_reranker.py))
shows when reranking helps and when it costs latency for nothing.
Neither of those claims means anything for your stack until you run
them against your own gold set.

The gold set is not glamorous. It is the smallest investment with the
largest leverage in a RAG project. Build it before you tune anything
else.

## Related

[Hybrid retrieval, with numbers](../articles/2026-05-hybrid-retrieval-numbers.md) - the article this evaluation harness measures against.

[RAG starter, end to end runnable](2026-05-rag-starter-runnable.md) - the
companion tutorial that builds the retriever the gold set evaluates.

[`cross_encoder_reranker.py`](../snippets/python/cross_encoder_reranker.py) - reranker snippet with a built-in mini gold set you can copy as a starting point.

[`reciprocal_rank_fusion.py`](../snippets/python/reciprocal_rank_fusion.py) - the fusion step measured by the script in this tutorial.

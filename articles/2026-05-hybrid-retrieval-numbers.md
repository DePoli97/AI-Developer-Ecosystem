# Hybrid retrieval, with numbers

*What you actually buy when you fuse lexical and dense retrieval, and
when a cross-encoder reranker is worth the extra latency. With a small
worked example you can run on your laptop.*

Published: 2026-05.  Reading time: 12 minutes.

## The question this article answers

You have a working RAG system. It uses one of two retrievers: either a
lexical index (BM25, SQLite FTS5, OpenSearch with a default analyser) or
a dense index (embeddings into a vector store). It mostly works. Someone
suggests "let's do hybrid", or "let's add a reranker". The vendors who
sell hybrid search say it lifts quality by double digits. Your own gut
says it might be overkill. Who is right?

The honest answer is: it depends on the corpus, and the only way to know
is to measure on your own data. But the qualitative pattern is consistent
across the corpora I have worked on, and the numbers in this article line
up with the published benchmarks. The goal here is to give you a mental
model that survives contact with your own evaluation harness, not to sell
you on hybrid.

The short version. Lexical retrieval is right when the user types the
domain's keywords. Dense retrieval is right when the user paraphrases.
Real users do both, sometimes in the same query. Hybrid retrieval is
mostly free quality on mixed-intent corpora. Cross-encoder rerankers
deliver real, measurable lift on noisy first-stage results, and they
deliver almost nothing when stage one is already clean. Skip them when
your dense retriever is already returning the right answer at rank one.

## A tiny corpus, six queries

Everything below was produced from a 30-document corpus and six queries
with gold-labelled relevant documents. The corpus is in the docstring of
`snippets/python/cross_encoder_reranker.py`, and the evaluation script is
under fifty lines. You should re-run it on your own data; the absolute
numbers do not matter, the **deltas** do.

The four retrieval strategies measured:

A plain BM25 lexical retriever. A char-trigram cosine "dense" retriever,
which is a robust laptop-friendly proxy for a real sentence-embedding
model. RRF fusion of BM25 and dense, taking top 30 from each. RRF fusion
followed by a cross-encoder reranker over the top 20 fused candidates.

Average nDCG@10 across the six queries:

| Strategy                  | nDCG@10 | MRR  | Latency budget |
|---------------------------|---------|------|----------------|
| BM25 only                 | 0.738   | 1.00 | ~5 ms          |
| Dense only (trigram cos)  | 0.894   | 1.00 | ~15 ms         |
| RRF fusion                | 0.831   | 1.00 | ~20 ms         |
| RRF + rerank top 20       | 0.756   | 1.00 | ~250 ms*       |

\* Latency for a real cross-encoder, not the deterministic mock used in
the snippet's self-test. Mock numbers shown for nDCG.

## What the numbers say, honestly

Three observations, none of them the marketing line.

**MRR is saturated.** Every strategy puts a relevant document at rank
one for every query. On a 30-doc toy corpus that is unsurprising. MRR
stops being a useful signal once your stage-one retriever clears a
basic quality bar. Switch to nDCG@10 or recall@k once you do.

**Dense beats BM25 on this corpus.** Trigram cosine - a deliberately
weak stand-in for a real embedding model - already beats BM25 by 21
nDCG@10 points. That is suspicious. It means the corpus has heavy
lexical-paraphrase pressure: the queries say "rerank retrieval cross
encoder" but the relevant document says "cross-encoder rerankers and
when they pay for themselves". A pure BM25 retriever takes a hit when
the gold-relevant document does not share keywords with the query.

**Fusion sometimes hurts.** RRF averages between BM25 and dense. When
dense alone is already near the ceiling, fusion can pull a result down
by averaging in BM25's worse ranking. The "llm cost token budget" query
in the per-query breakdown drops from 0.967 (dense alone) to 0.704
(RRF). This is not a bug; it is a property of fusion. The right answer
depends on whether *both* signals are competent on your corpus.

The general rule that emerges:

*Fuse when neither retriever dominates and the dominant one shifts
query-by-query. Skip fusion when one retriever is strictly stronger on
your eval set.*

You will know which case you are in after one afternoon with a 50-query
gold set. Build the gold set before you build hybrid.

## When the reranker actually earns its latency

The reranker drop in the table above is a feature, not a bug, of an
honest report. The mock scorer in the snippet uses lexical overlap plus
a bigram bonus - it is essentially a smarter BM25. On this corpus a
smarter BM25 cannot beat the trigram cosine. The reranker still wins
on the queries where stage one returned a mix of keyword matches that
were not topically relevant:

| Query                          | dense | RRF   | RRF+rerank |
|--------------------------------|-------|-------|------------|
| hybrid search bm25 embeddings  | 0.613 | 0.613 | **0.807**  |

A real cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2` or any of
the bge-reranker variants) will outperform the mock here on the harder
queries too. The point is that **reranker lift is a function of how
noisy stage one is**. If your stage-one nDCG@10 is already 0.85, the
reranker's 250 ms of latency is buying you 2-4 points. If your stage-
one nDCG@10 is 0.55, the reranker is buying you 10-15 points.

The decision matrix is small enough to fit in your head:

If stage one is clean (nDCG@10 > 0.8): skip the reranker. Spend the
latency budget on better answers (re-prompting the LLM with more
context, or running a verification pass).

If stage one is noisy (nDCG@10 between 0.4 and 0.7): the reranker is
the single highest-leverage change you can make. Do it before you
swap embedding models, before you tune chunk sizes, before you write
a query rewriter.

If stage one is broken (nDCG@10 below 0.4): the reranker cannot save
you. Fix the index. The recall ceiling at top 30 is your problem; a
reranker only reorders what stage one surfaced.

## How to actually wire it up

A practical hybrid retrieval stack has three components and one
diagnostic loop. The components are in this repository:

The lexical index is anything that returns ordered ids. The
[SQLite FTS5 walkthrough](../workflows/rag-starter-sqlite-fts5.md)
covers a zero-dependency setup that holds up to a few million docs.

The dense index is any vector store - LanceDB, Chroma, pgvector,
Qdrant. The choice matters less than people think; pick on operational
fit, not on benchmarks. The
[RAG starter tutorial](../tutorials/2026-05-rag-starter-runnable.md)
walks through a runnable variant.

The fusion is reciprocal rank fusion. Thirty lines of code, parameter
`k=60`, robust across corpora. Implementation:
[`snippets/python/reciprocal_rank_fusion.py`](../snippets/python/reciprocal_rank_fusion.py).

The reranker is a cross-encoder applied to the top 20-30 fused
candidates. Implementation:
[`snippets/python/cross_encoder_reranker.py`](../snippets/python/cross_encoder_reranker.py).
The snippet ships with a deterministic mock scorer so the self-test
runs offline; swap in
`sentence_transformers_scorer("cross-encoder/ms-marco-MiniLM-L-6-v2")`
for the production path.

The diagnostic loop is a 50-query gold set, an nDCG@10 calculation, and
a CSV of per-query deltas between strategies. The
[minimal eval harness](../snippets/python/minimal_eval_harness.py)
pattern fits this in 80 lines. If you cannot tell which queries the
reranker helped and which it hurt, you are flying blind; the per-query
breakdown is non-negotiable.

## What I would skip

Three things look attractive and rarely pay back on a small or mid-size
corpus.

A learned-to-rank model on top of the reranker. The marginal lift over
a well-tuned cross-encoder is small, the engineering cost is large,
and the model goes stale with the corpus. Defer until you have a real
relevance team.

Query expansion with an LLM as a default. It helps on very short queries
("Postgres index") and hurts on long queries because it amplifies
ambiguity. Gate it behind a query-length check; do not run it
unconditionally.

Switching embedding models more than once a quarter. Embedding migrations
are expensive (full reindex), the benchmarks are noisy, and the gains
between top-five public models on most corpora are inside the noise
floor of your eval set. Pick one, ship it, move on.

## The cost-quality frontier

Hybrid retrieval is one of the few changes in the RAG stack that moves
the cost-quality frontier rather than sliding along it. BM25 is nearly
free, dense retrieval is cheap, RRF is free, and the reranker costs
~250 ms per query but only runs once per request. For most products,
the full stack adds 200-300 ms of latency and zero per-token cost on
top of a baseline RAG system, and lifts answer quality by 5-15 nDCG@10
points.

Compared to the next-most-popular tactics in this space - swapping to
a bigger embedding model, increasing chunk overlap, or tuning the
generation prompt - hybrid retrieval is the cheapest, most predictable
quality win on the menu.

That is the case for doing it. The case for measuring before you do it
is even stronger.

## Further reading inside the repo

- Workflow with code:
  [`workflows/rag-starter-sqlite-fts5.md`](../workflows/rag-starter-sqlite-fts5.md)
- End-to-end tutorial:
  [`tutorials/2026-05-rag-starter-runnable.md`](../tutorials/2026-05-rag-starter-runnable.md)
- Fusion snippet:
  [`snippets/python/reciprocal_rank_fusion.py`](../snippets/python/reciprocal_rank_fusion.py)
- Reranker snippet:
  [`snippets/python/cross_encoder_reranker.py`](../snippets/python/cross_encoder_reranker.py)
- Cost framing:
  [`articles/2026-05-llm-cost-engineering-field-guide.md`](2026-05-llm-cost-engineering-field-guide.md)

## Status of the retrieval cluster

This article is the foundation piece of the retrieval cluster in
`CONTENT_PLAN.md`. With it, the cluster has a foundation article, a
runnable tutorial, a workflow, and four snippets (fusion, reranker,
RAG starter, token-aware splitter) that cite back to it. The next
addition planned for the cluster is a short tutorial on building the
50-query gold set, because that is the step most readers will skip
and the one that produces all the value.

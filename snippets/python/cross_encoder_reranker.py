"""
Cross-encoder reranker - a second-stage ranking pass for RAG.

Why this exists:
    First-stage retrievers (BM25, FTS5, dense embeddings, or any fusion of
    them) optimise for recall: get the right answer somewhere in the top 50.
    They are fast but they score query and document independently, so they
    miss the kind of fine-grained interaction a real reader needs - the
    difference between "Postgres index" and "Postgres how to index".

    A cross-encoder scores (query, document) jointly. It is 10-100x slower
    per pair than a bi-encoder embedding lookup, but it only runs on the
    top 20-50 candidates from stage one, so the latency cost is bounded.
    Cross-encoder reranking is the cheapest pure-quality win in a RAG
    stack, and the typical lift is 5-15 nDCG@10 points on noisy corpora.

Public API:
    rerank(query, candidates, scorer=None, *, top_n=None) -> list[Hit]
    Hit(.item, .text, .score, .stage1_rank, .stage2_rank)
    mock_scorer(query, text) -> float   # deterministic, std-lib only
    sentence_transformers_scorer(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        - lazy import, returns a scorer compatible with rerank()

Design notes:
    - The default scorer is a deterministic mock that uses lexical overlap
      and a stable hash perturbation. It exists so the snippet self-tests
      pass with zero dependencies, in CI, on an air-gapped laptop. Swap it
      out for a real cross-encoder in production via the `scorer` argument.
    - The function is pure - no I/O, no global state - so it is trivial to
      wrap behind a queue, a cache, or a budget guard.

Dependencies:
    standard library only for the default scorer.
    sentence-transformers (optional) for the production scorer.

Self-test:
    python cross_encoder_reranker.py
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Sequence

Scorer = Callable[[str, str], float]


@dataclass(frozen=True)
class Hit:
    """A reranked candidate, carrying enough metadata to debug a regression."""
    item: Hashable
    text: str
    score: float
    stage1_rank: int
    stage2_rank: int


# Default scorer ────────────────────────────────────────────────────────────

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def mock_scorer(query: str, text: str) -> float:
    """
    A deterministic, dependency-free relevance proxy.

    The score is a combination of:
      - jaccard overlap on lowercase alphanumeric tokens
      - a small bigram bonus
      - a tiny stable perturbation derived from a hash of (query, text),
        so ties break reproducibly across runs

    This is enough to exercise the reranker plumbing in tests. For real
    workloads, use sentence_transformers_scorer() or a hosted reranker.
    """
    q = set(_tokens(query))
    t = set(_tokens(text))
    if not q or not t:
        return 0.0
    jaccard = len(q & t) / len(q | t)

    # Bigram bonus on the original lowercase strings.
    ql = query.lower()
    tl = text.lower()
    bigram_bonus = 0.0
    for i in range(len(ql) - 1):
        if ql[i:i + 2] in tl:
            bigram_bonus += 1.0
    bigram_bonus = min(0.2, bigram_bonus / max(1, len(ql)))

    # Deterministic tie-breaker, < 1e-3, derived from a stable hash.
    h = hashlib.blake2s(f"{query}\0{text}".encode(), digest_size=4).digest()
    perturb = int.from_bytes(h, "big") / 2**32 * 1e-3

    return jaccard + bigram_bonus + perturb


# Optional production scorer ────────────────────────────────────────────────

def sentence_transformers_scorer(
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> Scorer:
    """
    Return a scorer backed by a real sentence-transformers cross-encoder.

    Usage:
        scorer = sentence_transformers_scorer()  # downloads the model once
        hits = rerank(query, candidates, scorer=scorer, top_n=10)

    The import is deferred so the snippet can be vendored without forcing
    sentence-transformers to be installed in the host project.
    """
    from sentence_transformers import CrossEncoder  # type: ignore

    model = CrossEncoder(model_name)

    def _score(query: str, text: str) -> float:
        # CrossEncoder.predict is batchable, but we keep the signature simple
        # here. Callers who care about throughput should batch upstream and
        # call model.predict directly.
        return float(model.predict([(query, text)])[0])

    return _score


# Core API ──────────────────────────────────────────────────────────────────

def rerank(
    query: str,
    candidates: Sequence[tuple[Hashable, str]],
    *,
    scorer: Scorer | None = None,
    top_n: int | None = None,
) -> list[Hit]:
    """
    Rerank stage-one candidates against the query.

    Args:
        query:      the user query string.
        candidates: iterable of (item_id, text) pairs in stage-one order.
                    item_id can be any hashable; text is what gets scored.
        scorer:     a callable (query, text) -> float. Defaults to mock_scorer.
        top_n:      optional cap on returned hits.

    Returns:
        A list of Hit, ordered by descending stage-two score.
    """
    if scorer is None:
        scorer = mock_scorer

    scored: list[Hit] = []
    for stage1_rank, (item, text) in enumerate(candidates, start=1):
        score = float(scorer(query, text))
        scored.append(
            Hit(
                item=item,
                text=text,
                score=score,
                stage1_rank=stage1_rank,
                stage2_rank=0,  # filled in below
            )
        )

    scored.sort(key=lambda h: h.score, reverse=True)
    ranked = [
        Hit(
            item=h.item,
            text=h.text,
            score=h.score,
            stage1_rank=h.stage1_rank,
            stage2_rank=i,
        )
        for i, h in enumerate(scored, start=1)
    ]
    return ranked[:top_n] if top_n is not None else ranked


def rank_changes(hits: Iterable[Hit]) -> list[dict]:
    """
    Diagnostic helper: returns one row per hit with stage-one and stage-two
    ranks, and the delta. Use this to inspect what the reranker actually
    moved during a regression test or an offline eval.
    """
    rows = []
    for h in hits:
        rows.append(
            {
                "item": h.item,
                "score": round(h.score, 6),
                "stage1_rank": h.stage1_rank,
                "stage2_rank": h.stage2_rank,
                "delta": h.stage1_rank - h.stage2_rank,
            }
        )
    return rows


# Self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> int:
    query = "how to index a postgres table"
    # Stage-one returned five candidates. The truly relevant one (id=42)
    # was buried at rank 4 because lexical retrieval pulled keyword-rich
    # but off-topic results to the top. The reranker must surface it.
    candidates = [
        (10, "Postgres release notes for version 16"),
        (11, "Indexing strategies in MongoDB collections"),
        (12, "How to install Postgres on Ubuntu 22.04"),
        (42, "How to index a Postgres table for fast lookups"),
        (13, "Table partitioning patterns in SQL Server"),
    ]

    hits = rerank(query, candidates)
    assert len(hits) == 5, hits
    assert hits[0].item == 42, f"expected 42 first, got {[h.item for h in hits]}"
    assert hits[0].stage1_rank == 4
    assert hits[0].stage2_rank == 1

    # Scores must be monotonically non-increasing.
    for a, b in zip(hits, hits[1:]):
        assert a.score >= b.score, (a, b)

    # top_n
    top3 = rerank(query, candidates, top_n=3)
    assert len(top3) == 3
    assert top3[0].item == 42

    # Empty input
    assert rerank(query, []) == []

    # Determinism: identical inputs must produce identical scores.
    hits2 = rerank(query, candidates)
    for a, b in zip(hits, hits2):
        assert a.item == b.item and a.score == b.score, (a, b)

    # Plug-in scorer: a custom scorer that prefers longer texts must
    # rearrange the list accordingly.
    def length_scorer(_q: str, t: str) -> float:
        return float(len(t))

    by_len = rerank(query, candidates, scorer=length_scorer)
    longest = max(candidates, key=lambda c: len(c[1]))
    assert by_len[0].item == longest[0], by_len

    # Diagnostic helper sanity.
    rows = rank_changes(hits)
    assert rows[0]["item"] == 42 and rows[0]["delta"] == 3, rows[0]

    # Mock-scorer properties: identical query and text -> high score; fully
    # disjoint -> low score.
    assert mock_scorer("alpha beta", "alpha beta") > mock_scorer("alpha beta", "zzz qqq")
    assert mock_scorer("", "anything") == 0.0

    print("ok: cross_encoder_reranker self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())

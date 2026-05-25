"""
rag_eval_gold_set.py - a 200-line evaluation harness for RAG retrievers.

Why this exists:
    Every retrieval change (chunk size, fusion, reranker, embedding
    model) needs a number attached to it before merge. This script
    loads a hand-labelled gold set, runs every retriever variant under
    test against it, and prints nDCG@10 plus MRR side by side. The
    companion tutorial walks through how to build the gold set itself:

        tutorials/2026-05-build-rag-eval-gold-set.md

Public API:
    load_gold_set(path) -> GoldSet
    evaluate(gold, retrievers, k=10) -> dict[name, EvalResult]
    print_table(results) -> None
    print_regressions(gold, results, baseline, variant, top_n=5)
    ndcg_at_k(retrieved, relevant, partial, k) -> float
    mrr(retrieved, relevant) -> float

Design notes:
    - Zero third-party dependencies. The harness is the cheap part; what
      matters is the gold set you bring to it.
    - Retrievers are plain callables: `retrieve(query: str, k: int) ->
      list[str]`. That signature lets you plug in BM25, dense, hybrid,
      reranked, or any future variant by adding one entry to a dict.
    - Two metrics, not ten. Pick nDCG@10 and MRR and live with them; the
      marginal value of adding @20, MAP, Recall@5, etc. is near zero
      compared to the cost of building a second gold set.

Self-test:
    python rag_eval_gold_set.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


Retriever = Callable[[str, int], list[str]]


@dataclass(frozen=True)
class Query:
    id: str
    text: str
    relevant: frozenset[str]
    partial: frozenset[str]
    intent: str = ""
    notes: str = ""


@dataclass(frozen=True)
class GoldSet:
    version: int
    created: str
    corpus_revision: str
    queries: tuple[Query, ...]


@dataclass
class EvalResult:
    name: str
    per_query_ndcg: list[float] = field(default_factory=list)
    per_query_mrr: list[float] = field(default_factory=list)

    @property
    def ndcg(self) -> float:
        return _safe_mean(self.per_query_ndcg)

    @property
    def mrr(self) -> float:
        return _safe_mean(self.per_query_mrr)


def _safe_mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def load_gold_set(path: str | Path) -> GoldSet:
    """Load a gold set JSON file. See the tutorial for the schema."""
    data = json.loads(Path(path).read_text())
    queries = tuple(
        Query(
            id=q["id"],
            text=q["text"],
            relevant=frozenset(q.get("relevant", [])),
            partial=frozenset(q.get("partially_relevant", [])),
            intent=q.get("intent", ""),
            notes=q.get("notes", ""),
        )
        for q in data["queries"]
    )
    return GoldSet(
        version=data.get("version", 1),
        created=data.get("created", ""),
        corpus_revision=data.get("corpus_revision", ""),
        queries=queries,
    )


def _dcg(gains: Iterable[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(
    retrieved: list[str],
    relevant: Iterable[str],
    partial: Iterable[str] = (),
    k: int = 10,
) -> float:
    """nDCG@k with graded relevance: 1.0 for relevant, 0.5 for partial."""
    rel_set = set(relevant)
    par_set = set(partial)
    gains = []
    for doc_id in retrieved[:k]:
        if doc_id in rel_set:
            gains.append(1.0)
        elif doc_id in par_set:
            gains.append(0.5)
        else:
            gains.append(0.0)
    ideal = sorted([1.0] * len(rel_set) + [0.5] * len(par_set), reverse=True)[:k]
    if not ideal:
        return 0.0
    return _dcg(gains) / _dcg(ideal)


def mrr(retrieved: list[str], relevant: Iterable[str]) -> float:
    """Reciprocal rank of the first relevant document, 0 if none in list."""
    rel_set = set(relevant)
    for i, doc_id in enumerate(retrieved):
        if doc_id in rel_set:
            return 1.0 / (i + 1)
    return 0.0


def evaluate(
    gold: GoldSet,
    retrievers: dict[str, Retriever],
    k: int = 10,
) -> dict[str, EvalResult]:
    """Run every retriever against the gold set and collect per-query scores."""
    results: dict[str, EvalResult] = {
        name: EvalResult(name=name) for name in retrievers
    }
    for q in gold.queries:
        for name, retrieve in retrievers.items():
            hits = retrieve(q.text, k)
            results[name].per_query_ndcg.append(
                ndcg_at_k(hits, q.relevant, q.partial, k=k)
            )
            results[name].per_query_mrr.append(mrr(hits, q.relevant))
    return results


def print_table(results: dict[str, EvalResult]) -> None:
    """Print a small summary table for a quick visual diff."""
    header = f"{'retriever':<25} {'nDCG@10':>10} {'MRR':>10}"
    print(header)
    print("-" * len(header))
    for name, res in results.items():
        print(f"{name:<25} {res.ndcg:>10.3f} {res.mrr:>10.3f}")


def print_regressions(
    gold: GoldSet,
    results: dict[str, EvalResult],
    baseline: str,
    variant: str,
    top_n: int = 5,
) -> None:
    """Show the queries where `variant` regressed worst vs `baseline`."""
    if baseline not in results or variant not in results:
        raise KeyError(f"missing {baseline!r} or {variant!r} in results")
    deltas = sorted(
        (
            results[variant].per_query_ndcg[i] - results[baseline].per_query_ndcg[i],
            gold.queries[i].text,
        )
        for i in range(len(gold.queries))
    )
    print(f"\nworst regressions ({variant} vs {baseline}):")
    for delta, text in deltas[:top_n]:
        if delta < 0:
            print(f"  {delta:+.3f}  {text}")


def _selftest() -> None:
    """A minimal end-to-end smoke test with three fake retrievers."""
    gold_data = {
        "version": 1,
        "created": "2026-05-25",
        "corpus_revision": "git:test",
        "queries": [
            {"id": "q1", "text": "alpha beta",
             "relevant": ["doc_a"], "partially_relevant": ["doc_b"]},
            {"id": "q2", "text": "gamma delta",
             "relevant": ["doc_c"], "partially_relevant": []},
            {"id": "q3", "text": "epsilon",
             "relevant": ["doc_d", "doc_e"], "partially_relevant": ["doc_f"]},
        ],
    }
    tmp = Path("/tmp/_gold_selftest.json")
    tmp.write_text(json.dumps(gold_data))
    gold = load_gold_set(tmp)

    def perfect(q: str, k: int) -> list[str]:
        return {
            "alpha beta": ["doc_a", "doc_b", "doc_x"],
            "gamma delta": ["doc_c", "doc_y"],
            "epsilon": ["doc_d", "doc_e", "doc_f"],
        }[q][:k]

    def baseline(q: str, k: int) -> list[str]:
        return {
            "alpha beta": ["doc_x", "doc_a", "doc_b"],
            "gamma delta": ["doc_y", "doc_c"],
            "epsilon": ["doc_f", "doc_d", "doc_e"],
        }[q][:k]

    def broken(q: str, k: int) -> list[str]:
        return ["doc_x", "doc_y", "doc_z"][:k]

    results = evaluate(gold, {"baseline": baseline, "perfect": perfect, "broken": broken})

    assert results["perfect"].ndcg == 1.0, "perfect retriever should hit nDCG=1.0"
    assert results["broken"].ndcg == 0.0, "broken retriever should hit nDCG=0.0"
    assert results["baseline"].ndcg < results["perfect"].ndcg
    assert results["baseline"].mrr < results["perfect"].mrr

    print_table(results)
    print_regressions(gold, results, baseline="perfect", variant="baseline", top_n=3)
    tmp.unlink()
    print("\nself-test passed.")


if __name__ == "__main__":
    _selftest()

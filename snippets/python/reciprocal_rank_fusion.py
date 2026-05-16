"""
Reciprocal Rank Fusion (RRF) - fuse multiple ranked result lists.

Why this exists:
    When you have two or more retrieval signals (lexical BM25/FTS5,
    semantic embeddings, learned-to-rank, business-rule boosts), you need
    a way to combine them that does not depend on the absolute scale of
    each score. RRF does exactly that: it scores each item by 1/(k+rank)
    in each list and sums. It is robust, parameter-light, and consistently
    competitive against more complex fusion methods.

Public API:
    rrf(ranked_lists, *, k=60, top_n=None) -> list[tuple[item, score]]
    rrf_with_origins(ranked_lists, names, *, k=60) -> list[dict]

The item type is the caller's choice (string ID, int chunk_id, dataclass).
RRF only needs equality and hashability.

Dependencies:
    standard library only.

Self-test:
    python reciprocal_rank_fusion.py
"""

from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Sequence


def rrf(
    ranked_lists: Sequence[Sequence[Hashable]],
    *,
    k: int = 60,
    top_n: int | None = None,
) -> list[tuple[Hashable, float]]:
    """
    Fuse multiple ranked lists with Reciprocal Rank Fusion.

    Args:
        ranked_lists: a sequence of ranked lists, each ordered best-first.
        k:           smoothing constant. 60 is the canonical default; tune
                     between 30 and 100 if needed.
        top_n:       optional cap on the returned list length.

    Returns:
        Items sorted by fused score, descending.
    """
    scores: dict[Hashable, float] = defaultdict(float)
    for results in ranked_lists:
        for rank, item in enumerate(results, start=1):
            scores[item] += 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return fused[:top_n] if top_n is not None else fused


def rrf_with_origins(
    ranked_lists: Sequence[Sequence[Hashable]],
    names: Sequence[str],
    *,
    k: int = 60,
    top_n: int | None = None,
) -> list[dict]:
    """
    Like rrf(), but also records which lists contributed each item and the
    rank it had there. Useful for debugging "why did this win".
    """
    if len(names) != len(ranked_lists):
        raise ValueError("names and ranked_lists must have the same length")

    scores: dict[Hashable, float] = defaultdict(float)
    origins: dict[Hashable, dict[str, int]] = defaultdict(dict)
    for name, results in zip(names, ranked_lists):
        for rank, item in enumerate(results, start=1):
            scores[item] += 1.0 / (k + rank)
            origins[item][name] = rank

    rows = [
        {"item": item, "score": scores[item], "ranks": dict(origins[item])}
        for item, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ]
    return rows[:top_n] if top_n is not None else rows


# Self-test ─────────────────────────────────────────────────────────────────

def _self_test() -> int:
    # Two lists with partial overlap.
    lex = ["A", "B", "C", "D", "E"]
    sem = ["C", "A", "F", "B", "G"]
    fused = rrf([lex, sem])
    items = [it for it, _ in fused]
    assert items[0] == "A", f"expected A first, got {items}"
    assert "C" in items[:3], items
    assert "G" in items, items
    # All items appearing in any list should appear in the fused list.
    assert set(items) == set(lex) | set(sem), items

    # Empty input
    assert rrf([]) == []
    assert rrf([[], []]) == []

    # top_n
    top = rrf([lex, sem], top_n=3)
    assert len(top) == 3, top

    # rrf_with_origins
    rows = rrf_with_origins([lex, sem], names=["lex", "sem"], top_n=2)
    assert rows[0]["item"] == "A"
    assert rows[0]["ranks"] == {"lex": 1, "sem": 2}, rows[0]
    assert "score" in rows[0]

    # Score monotonicity: an item ranked 1 in both lists must beat any item
    # ranked deeper in either.
    a = ["X", "P", "Q"]
    b = ["X", "R", "S"]
    fused2 = rrf([a, b])
    assert fused2[0][0] == "X", fused2

    # Length mismatch
    try:
        rrf_with_origins([lex], names=["a", "b"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on length mismatch")

    print("ok: reciprocal_rank_fusion self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())

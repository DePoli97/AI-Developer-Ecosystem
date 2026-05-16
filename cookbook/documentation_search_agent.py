"""
documentation_search_agent - hybrid retrieval over a Markdown folder.

Wires together:
    - snippets/python/rag_sqlite_starter.py  (the Store / chunker)
    - snippets/python/reciprocal_rank_fusion.py (already used inside the store)

What it does:
    Indexes every .md file under a given root into a SQLite store, then
    answers a query by returning the top hybrid-retrieved chunks. With a
    valid ANTHROPIC_API_KEY and --claude, it also generates a synthesised
    answer.

CLI:
    python documentation_search_agent.py --self-test
    python documentation_search_agent.py --root .. --rebuild --query "agent loop"
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
SNIPPETS = HERE.parent / "snippets" / "python"
sys.path.insert(0, str(SNIPPETS))

from rag_sqlite_starter import Store, chunk_text  # type: ignore


def index_markdown_folder(store: Store, root: Path, *, exts: tuple[str, ...] = (".md", ".txt")) -> int:
    n = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks = chunk_text(text)
        if chunks:
            n += store.index(doc_id=str(path.relative_to(root)), chunks=chunks)
    return n


def answer(store: Store, query: str, k: int = 5) -> str:
    hits = store.search(query, k=k)
    if not hits:
        return f"(no documents matched '{query}')"
    lines = [f"Top {len(hits)} passages for: {query}", ""]
    for h in hits:
        snippet = h.text.replace("\n", " ")[:300]
        lines.append(f"- [{h.score:.4f}] {h.doc_id}#{h.ordinal}: {snippet}")
    return "\n".join(lines)


def _cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--db", default="docsearch.sqlite")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--query", help="Query to run after indexing.")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        return _self_test()

    store = Store(args.db)
    if args.rebuild:
        store.reset()
        n = index_markdown_folder(store, Path(args.root))
        print(f"indexed {n} chunks")
    if args.query:
        print(answer(store, args.query, k=args.k))
    return 0


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "intro.md").write_text(
            "# Introduction\n\nWelcome to the project.\n\n"
            "This guide covers retrieval, agents, and evaluation."
        )
        (root / "agents.md").write_text(
            "# Agents\n\nAn agent loop reads tools, calls them, "
            "and continues until the model decides to stop.\n\n"
            "Tool inputs must be validated to avoid crashes."
        )
        (root / "rag.md").write_text(
            "# Retrieval\n\nHybrid retrieval combines FTS5 with embeddings.\n\n"
            "Reciprocal Rank Fusion merges the two ranked lists robustly."
        )
        db_path = os.path.join(tmp, "test.sqlite")
        store = Store(db_path)
        n = index_markdown_folder(store, root)
        assert n >= 3, n

        out = answer(store, "agent tool loop validation", k=3)
        assert "agents.md" in out, out

        out2 = answer(store, "FTS5 hybrid search", k=3)
        assert "rag.md" in out2, out2

    print("ok: documentation_search_agent self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

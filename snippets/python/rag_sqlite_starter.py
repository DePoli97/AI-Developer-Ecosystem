"""
RAG starter, SQLite FTS5 plus embeddings, one file - runnable companion.

Companion to: workflows/rag-starter-sqlite-fts5.md

What it does:
    Builds a tiny retrieval system in a single SQLite file with two
    signals (FTS5 lexical + cosine on stored embedding blobs), fused with
    Reciprocal Rank Fusion. Drop in your own encoder; the default for
    real use is sentence-transformers, but the module also ships a
    deterministic hashing encoder so the --self-test runs offline with
    zero heavy dependencies.

Public API:
    Store(db_path).index(doc_id, chunks)
    Store(db_path).search(query, k=8) -> list[Hit]
    Hit(chunk_id, doc_id, ordinal, text, score)

CLI:
    python rag_sqlite_starter.py --self-test
    python rag_sqlite_starter.py --db notes.sqlite --ingest README.md
    python rag_sqlite_starter.py --db notes.sqlite --query "tool use"

Dependencies:
    Standard library + numpy. sentence-transformers is optional and only
    used if `--encoder=st` is selected.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

DIM = 256  # dimension for the bundled hashing encoder; ST overrides via dim arg


# ── Encoders ─────────────────────────────────────────────────────────────────

def hashing_encoder(dim: int = DIM) -> Callable[[str], np.ndarray]:
    """
    Deterministic, dependency-free encoder. Token-hashing with a unit
    L2-norm output. Not state-of-the-art, but stable enough to demonstrate
    the system and to power the offline self-test.
    """
    rng_seed = 1337
    rng = np.random.default_rng(rng_seed)
    signs = rng.choice([-1.0, 1.0], size=dim).astype("float32")
    _ = signs  # reserved for signed hashing if you want to extend it

    def _tokenise(text: str) -> list[str]:
        return [t for t in re.findall(r"[A-Za-z0-9_]+", text.lower()) if len(t) > 1]

    def encode(text: str) -> np.ndarray:
        vec = np.zeros(dim, dtype="float32")
        for tok in _tokenise(text):
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            bucket = struct.unpack("<Q", h)[0] % dim
            sign = 1.0 if struct.unpack("<Q", h)[0] & 1 else -1.0
            vec[bucket] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    return encode


def sentence_transformer_encoder(model_name: str = "all-MiniLM-L6-v2") -> Callable[[str], np.ndarray]:
    from sentence_transformers import SentenceTransformer  # type: ignore
    model = SentenceTransformer(model_name)

    def encode(text: str) -> np.ndarray:
        return model.encode(text, normalize_embeddings=True).astype("float32")

    return encode


# ── Storage ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id   INTEGER PRIMARY KEY,
    doc_id     TEXT NOT NULL,
    ordinal    INTEGER NOT NULL,
    text       TEXT NOT NULL,
    embedding  BLOB NOT NULL,
    dim        INTEGER NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='chunk_id',
    tokenize = 'porter'
);

CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.chunk_id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.chunk_id, old.text);
END;
"""


@dataclass
class Hit:
    chunk_id: int
    doc_id: str
    ordinal: int
    text: str
    score: float


class Store:
    def __init__(self, db_path: str, encoder: Callable[[str], np.ndarray] | None = None) -> None:
        self.db = sqlite3.connect(db_path)
        self.db.executescript(SCHEMA)
        self.encoder = encoder or hashing_encoder()

    def index(self, doc_id: str, chunks: Iterable[str]) -> int:
        rows = []
        for i, ch in enumerate(chunks):
            vec = self.encoder(ch)
            rows.append((doc_id, i, ch, vec.tobytes(), int(vec.shape[0])))
        self.db.executemany(
            "INSERT INTO chunks(doc_id, ordinal, text, embedding, dim) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.db.commit()
        return len(rows)

    def reset(self) -> None:
        self.db.executescript(
            "DELETE FROM chunks; DELETE FROM chunks_fts;"
        )
        self.db.commit()

    def search(self, query: str, k: int = 8, *, rrf_k: int = 60) -> list[Hit]:
        qvec = self.encoder(query)

        # Lexical: build an FTS5 MATCH expression from the query tokens.
        tokens = re.findall(r"[A-Za-z0-9_]+", query)
        fts_expr = " OR ".join(tokens) if tokens else query
        try:
            lex_rows = self.db.execute(
                "SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY rank LIMIT 50",
                (fts_expr,),
            ).fetchall()
        except sqlite3.OperationalError:
            lex_rows = []
        lex_rank = {row[0]: r + 1 for r, row in enumerate(lex_rows)}

        # Semantic: cosine over stored unit vectors (dot product since L2-normed).
        rows = self.db.execute("SELECT chunk_id, embedding FROM chunks").fetchall()
        scored = []
        for cid, blob in rows:
            v = np.frombuffer(blob, dtype="float32")
            if v.shape[0] != qvec.shape[0]:
                continue
            scored.append((cid, float(np.dot(qvec, v))))
        scored.sort(key=lambda x: x[1], reverse=True)
        sem_rank = {cid: r + 1 for r, (cid, _) in enumerate(scored[:50])}

        # Reciprocal Rank Fusion
        fused: dict[int, float] = defaultdict(float)
        for cid, r in lex_rank.items():
            fused[cid] += 1.0 / (rrf_k + r)
        for cid, r in sem_rank.items():
            fused[cid] += 1.0 / (rrf_k + r)
        top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]

        hits: list[Hit] = []
        for cid, score in top:
            row = self.db.execute(
                "SELECT chunk_id, doc_id, ordinal, text FROM chunks WHERE chunk_id = ?",
                (cid,),
            ).fetchone()
            if row is None:
                continue
            hits.append(Hit(chunk_id=row[0], doc_id=row[1], ordinal=row[2], text=row[3], score=score))
        return hits


# ── Chunker ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, *, target_chars: int = 1200, overlap_chars: int = 200) -> list[str]:
    """Paragraph-aware chunker. Merges paragraphs up to target_chars with
    a sliding overlap to preserve context across boundaries."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in paragraphs:
        if cur_len + len(p) > target_chars and cur:
            chunks.append("\n\n".join(cur))
            # Build overlap from the tail of the previous chunk
            if overlap_chars > 0:
                tail = chunks[-1][-overlap_chars:]
                cur = [tail, p]
                cur_len = len(tail) + len(p)
            else:
                cur, cur_len = [p], len(p)
        else:
            cur.append(p)
            cur_len += len(p)
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli() -> int:
    parser = argparse.ArgumentParser(description="Tiny FTS5+embedding RAG store.")
    parser.add_argument("--db", default="rag.sqlite", help="SQLite database path")
    parser.add_argument("--encoder", choices=["hash", "st"], default="hash",
                        help="hash=bundled deterministic encoder; st=sentence-transformers")
    parser.add_argument("--ingest", action="append", default=[],
                        help="Path of a text/markdown file to ingest. May repeat.")
    parser.add_argument("--query", help="Run a query and print top hits.")
    parser.add_argument("--reset", action="store_true", help="Wipe the store before ingesting.")
    parser.add_argument("--self-test", action="store_true", help="Run offline self-test.")
    parser.add_argument("--k", type=int, default=5, help="Top-k hits.")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    encoder = hashing_encoder() if args.encoder == "hash" else sentence_transformer_encoder()
    store = Store(args.db, encoder=encoder)
    if args.reset:
        store.reset()
    total = 0
    for path in args.ingest:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        chunks = chunk_text(text)
        n = store.index(doc_id=path, chunks=chunks)
        total += n
        print(f"indexed {n} chunks from {path}")
    if total:
        print(f"total chunks added: {total}")
    if args.query:
        hits = store.search(args.query, k=args.k)
        for h in hits:
            preview = h.text.replace("\n", " ")[:140]
            print(f"[{h.score:.4f}] {h.doc_id}#{h.ordinal} {preview}")
    return 0


# ── Self-test ────────────────────────────────────────────────────────────────

def _self_test() -> int:
    import tempfile

    corpus = {
        "doc_python.txt": (
            "Python is a high-level interpreted language created by Guido van Rossum. "
            "It emphasises readability and developer productivity.\n\n"
            "Python is widely used in data science, machine learning, and web development. "
            "Major frameworks include Django and FastAPI."
        ),
        "doc_rust.txt": (
            "Rust is a systems programming language focused on safety and performance. "
            "It uses an ownership model to prevent data races at compile time.\n\n"
            "Rust ships with Cargo, a build tool and package manager."
        ),
        "doc_db.txt": (
            "SQLite is an embedded SQL engine. It supports full-text search via FTS5 "
            "and is a great fit for laptop-scale retrieval systems.\n\n"
            "Vector search can be implemented on top of SQLite by storing embeddings as BLOBs."
        ),
        "doc_llm.txt": (
            "Large language models such as Claude and GPT can be used inside retrieval "
            "pipelines. Hybrid retrieval combines lexical and semantic signals.\n\n"
            "Reciprocal Rank Fusion is a robust way to merge ranked lists."
        ),
    }

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "rag.sqlite")
        store = Store(db_path)
        for doc, text in corpus.items():
            store.index(doc_id=doc, chunks=chunk_text(text, target_chars=400, overlap_chars=50))

        # Query 1: lexical-favouring
        hits = store.search("FTS5 sqlite embeddings", k=3)
        assert hits, "no hits returned"
        assert hits[0].doc_id == "doc_db.txt", [h.doc_id for h in hits]

        # Query 2: semantic-favouring (the word "ownership" appears only in rust)
        hits = store.search("ownership memory safety language", k=3)
        assert hits[0].doc_id == "doc_rust.txt", [h.doc_id for h in hits]

        # Query 3: a topic that lives in multiple docs
        hits = store.search("retrieval ranking llm", k=4)
        top_doc_ids = [h.doc_id for h in hits]
        assert "doc_llm.txt" in top_doc_ids, top_doc_ids

        # Query 4: empty query should not crash
        store.search("", k=3)

        # Verify scores are sorted descending
        hits = store.search("python frameworks", k=4)
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True), scores

        # Reset wipes everything
        store.reset()
        assert store.search("python", k=3) == []

    print("ok: rag_sqlite_starter self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

# RAG starter, SQLite FTS5 plus embeddings, one machine

A working retrieval workflow that runs on a laptop, without a vector database,
without Docker, and without a paid service. The retrieval layer combines
SQLite's full-text search (FTS5) with sentence-transformers embeddings stored
in the same database as a blob. Good enough for a few hundred thousand
documents; trivial to upgrade to pgvector or Qdrant later because the
interface is small.

## When this is the right shape

The setup below is the correct one when you have under roughly 500,000
chunks, when the corpus changes slowly (rebuilds in minutes are acceptable),
and when you want a single-file persistence story. It is the wrong shape if
you need multi-writer concurrency, hybrid filtering on dozens of structured
fields, or sub-50-ms retrieval at high QPS.

## Architecture

The pipeline has four stages.

The first stage is the loader. It reads source documents (`.md`, `.txt`,
`.pdf` after extraction) and yields `(doc_id, text)` pairs. Anything that
produces strings works.

The second stage is the chunker. We split on paragraphs and merge until each
chunk is roughly 400 to 800 tokens, with a 50-token overlap to preserve
context across boundaries. The token-aware splitter in
`snippets/python/token_aware_text_splitter.py` is the exact tool here.

The third stage is dual indexing. For each chunk we compute a
sentence-transformer embedding (`all-MiniLM-L6-v2` is the default; swap for
`bge-small-en` or any model you prefer) and store the float32 vector as a
BLOB in a `chunks` table. The same chunk text is inserted into an FTS5
virtual table for lexical search.

The fourth stage is hybrid retrieval. For a query, we run both an FTS5
search and a cosine-similarity scan over the embedding column. We combine
the two using reciprocal rank fusion (RRF), which is robust to score-scale
differences and produces consistently better results than either signal
alone.

## Schema

    CREATE TABLE chunks (
        chunk_id   INTEGER PRIMARY KEY,
        doc_id     TEXT NOT NULL,
        ordinal    INTEGER NOT NULL,
        text       TEXT NOT NULL,
        embedding  BLOB NOT NULL
    );

    CREATE VIRTUAL TABLE chunks_fts USING fts5(
        text,
        content='chunks',
        content_rowid='chunk_id',
        tokenize = 'porter'
    );

    CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
        INSERT INTO chunks_fts(rowid, text) VALUES (new.chunk_id, new.text);
    END;
    CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
        INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES('delete', old.chunk_id, old.text);
    END;

The triggers keep FTS5 in sync as you insert and delete from `chunks`. This
is the single most common mistake when starting with FTS5; the table is not
auto-maintained.

## Indexing

```python
import sqlite3, struct, numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
DIM = 384

def encode(text: str) -> bytes:
    vec = model.encode(text, normalize_embeddings=True).astype("float32")
    return vec.tobytes()

def index_chunks(db: sqlite3.Connection, doc_id: str, chunks: list[str]) -> None:
    rows = [
        (doc_id, i, ch, encode(ch))
        for i, ch in enumerate(chunks)
    ]
    db.executemany(
        "INSERT INTO chunks(doc_id, ordinal, text, embedding) VALUES (?, ?, ?, ?)",
        rows,
    )
    db.commit()
```

## Retrieval with RRF fusion

```python
def search(db, query: str, k: int = 8) -> list[dict]:
    qvec = np.frombuffer(encode(query), dtype="float32")

    # Lexical search via FTS5
    lex = db.execute(
        "SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ? "
        "ORDER BY rank LIMIT ?", (query, 50)
    ).fetchall()
    lex_ranks = {row[0]: r + 1 for r, row in enumerate(lex)}

    # Semantic search via cosine on the embedding column
    rows = db.execute("SELECT chunk_id, embedding FROM chunks").fetchall()
    scored = []
    for cid, blob in rows:
        v = np.frombuffer(blob, dtype="float32")
        scored.append((cid, float(np.dot(qvec, v))))
    scored.sort(key=lambda x: x[1], reverse=True)
    sem_ranks = {cid: r + 1 for r, (cid, _) in enumerate(scored[:50])}

    # Reciprocal rank fusion
    fused: dict[int, float] = {}
    for cid in set(lex_ranks) | set(sem_ranks):
        score = 0.0
        if cid in lex_ranks:
            score += 1.0 / (60 + lex_ranks[cid])
        if cid in sem_ranks:
            score += 1.0 / (60 + sem_ranks[cid])
        fused[cid] = score
    top = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]

    return [
        dict(zip(("chunk_id", "doc_id", "ordinal", "text"),
                 db.execute(
                     "SELECT chunk_id, doc_id, ordinal, text FROM chunks WHERE chunk_id = ?",
                     (cid,)
                 ).fetchone()))
        for cid, _ in top
    ]
```

The constant 60 in RRF is a smoothing factor; tune between 30 and 100.

## When to graduate

Move to pgvector or Qdrant when any of these become true: the corpus exceeds
roughly half a million chunks, you need concurrent writers, or end-to-end
retrieval latency exceeds 250 ms at p95. The interface above is two
functions (`index_chunks` and `search`); both port cleanly to a vector
database without changing the calling code.

## Pitfalls

The most common failure mode is forgetting to normalise embeddings.
`SentenceTransformer.encode(..., normalize_embeddings=True)` turns the dot
product into cosine similarity. Without it, longer chunks score higher for
trivial reasons.

The second most common failure is over-chunking. Chunks smaller than 200
tokens fragment context; chunks larger than 1000 tokens make the LLM ignore
the middle. The 400 to 800 range is a reliable starting point.

The third is treating retrieval scores as confidence. They are not. Always
include a "no relevant context" path in your generation prompt and a check
that the top score exceeds a floor.

## Companion code

The runnable end-to-end script will live at `snippets/python/rag_sqlite_starter.py`
in a follow-up commit. It will use only `sqlite3`, `numpy`, and
`sentence-transformers`, and will include a `--self-test` flag with a tiny
corpus.

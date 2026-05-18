# Build a runnable RAG starter in 30 minutes, SQLite FTS5 + embeddings

A practical walkthrough that takes the `rag_sqlite_starter.py` snippet
from this repository and turns it into a working retrieval system you
can index your own notes against, search interactively, and extend with
an LLM answer step on top.

The setup runs on a laptop with no vector database, no Docker, and no
paid service. The whole pipeline lives in one SQLite file. By the end
of this tutorial you will have indexed a folder of Markdown files,
queried it with hybrid retrieval (lexical + embeddings + RRF fusion),
and wired a small `answer` function on top that grounds an LLM call
in the retrieved chunks.

If you want the architecture and design rationale, read the companion
workflow first: [`workflows/rag-starter-sqlite-fts5.md`](../workflows/rag-starter-sqlite-fts5.md).
This tutorial is the runnable counterpart.

## Who this is for

You are comfortable reading Python. You want a retrieval layer for a
side project, an internal tool, or a prototype, and you do not want to
stand up Pinecone or pgvector to do it. You expect under roughly half a
million chunks and you are fine with rebuilds that take minutes.

If you need multi-writer concurrency, hybrid filtering on dozens of
structured fields, or sub-50-ms retrieval at high QPS, this is the
wrong shape. Read the workflow's "When this is the right shape" section
for the boundary conditions.

## What you will build

A single SQLite database with two indexes over the same chunk text: an
FTS5 virtual table for lexical search, and a column of float32
embeddings stored as BLOBs. Search runs both signals, fuses the
rankings with reciprocal rank fusion, and returns the top chunks. The
final section adds an `answer` function that sends the retrieved
chunks to Claude and gets a grounded response with citations.

Total time, end to end, is roughly 30 minutes. Indexing throughput on
a modern laptop is around 200 to 800 chunks per second depending on
the encoder.

## Step 1: clone the repository and verify the snippet runs

The snippet ships with a self-test that uses a deterministic hashing
encoder, so it runs without sentence-transformers and without an API
key. Verify it works before doing anything else.

    git clone https://github.com/DePoli97/AI-Developer-Ecosystem.git
    cd AI-Developer-Ecosystem
    python -m pip install numpy
    python snippets/python/rag_sqlite_starter.py --self-test

You should see a passing self-test. If it fails, the rest of the
tutorial will not work.

## Step 2: install the production encoder

The hashing encoder is fine for the self-test. For real use, swap in
sentence-transformers. The `all-MiniLM-L6-v2` model is 22 MB, runs on
CPU, and produces 384-dimensional vectors that are good enough for
most documentation-scale corpora.

    python -m pip install sentence-transformers

The snippet picks up the encoder via the `--encoder=st` flag. Internally
it lazy-imports sentence-transformers, so the snippet still imports
cleanly on machines where it is not installed.

## Step 3: prepare a corpus

Anything that produces strings works. For this tutorial we will index
the Markdown files in this repository, which is enough text to make
search results interesting.

Create a small ingestion script next to the snippet:

    # ingest.py
    from pathlib import Path
    from snippets.python.rag_sqlite_starter import Store, chunk_text

    store = Store("notes.sqlite", encoder="st")
    root = Path(".")
    md_files = list(root.rglob("*.md"))
    print(f"indexing {len(md_files)} files")

    for path in md_files:
        text = path.read_text(encoding="utf-8")
        chunks = chunk_text(text, target_tokens=600, overlap_tokens=50)
        store.index(doc_id=str(path), chunks=chunks)

    print("done")

Run it from the repo root:

    python ingest.py

On the repo's current size this finishes in a few seconds. The
`notes.sqlite` file should land at a few megabytes.

The `chunk_text` helper merges paragraphs until each chunk hits the
target token budget, with a 50-token overlap to preserve context across
boundaries. The token-aware splitter in
[`snippets/python/token_aware_text_splitter.py`](../snippets/python/token_aware_text_splitter.py)
is the underlying tool.

## Step 4: query interactively

The snippet exposes a CLI for ad-hoc queries:

    python snippets/python/rag_sqlite_starter.py \
        --db notes.sqlite --query "how do I version prompts" --k 5

The output lists the top five chunks with their fused score, doc id,
and a short preview. You should see chunks from the prompt versioning
tutorial near the top.

Try a few queries to get a feel for what hybrid retrieval gives you
that single-signal retrieval does not.

    --query "exponential backoff retry"
    --query "claude tool use loop"
    --query "cost engineering"

The lexical signal handles exact terminology (`exponential backoff`,
`FTS5`); the embedding signal handles paraphrase (`how to slow down
when an API errors`). Reciprocal rank fusion combines them without
having to normalise score scales, which is the small but important
win over a naive linear combination.

## Step 5: wire an LLM answer on top

Retrieval on its own is useful, but the standard end-to-end is to
hand the retrieved chunks to an LLM and ask for a grounded answer.
The pattern is small enough to write inline.

Create `answer.py` next to `ingest.py`:

    # answer.py
    import os
    import anthropic
    from snippets.python.rag_sqlite_starter import Store

    SYSTEM = (
        "You are a careful technical writer. Answer the question using only "
        "the provided context. If the context does not contain the answer, "
        "say so. Cite chunks by their numeric id in square brackets."
    )

    def answer(question: str, k: int = 5) -> str:
        store = Store("notes.sqlite", encoder="st")
        hits = store.search(question, k=k)
        if not hits:
            return "No relevant chunks were retrieved."

        context = "\n\n".join(
            f"[{i+1}] (source: {h.doc_id})\n{h.text}"
            for i, h in enumerate(hits)
        )
        prompt = f"Context:\n{context}\n\nQuestion: {question}"

        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=600,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    if __name__ == "__main__":
        import sys
        q = " ".join(sys.argv[1:]) or "How do I version prompts safely?"
        print(answer(q))

Set your API key and run:

    export ANTHROPIC_API_KEY=...
    python answer.py "how do I version prompts"

You should get a short answer that cites chunk ids and refers back to
the prompt-versioning material in the repository.

## Step 6: what to tune first

The two knobs that matter most are chunk size and `k` (the number of
chunks fed to the LLM).

Chunk size controls precision versus recall. Smaller chunks (300 to
400 tokens) increase precision because each chunk talks about one
thing, but they also increase the chance that the relevant sentence
sits across a boundary. Larger chunks (800 to 1,200 tokens) reduce
boundary problems but dilute the embedding signal. Start at 600 with
50 overlap. Move only if you have a concrete failure case to argue
from.

`k` controls how much context the LLM sees. The cost is linear in `k`.
The quality curve is usually a steep climb to `k = 5`, a gentle slope
to `k = 10`, and noise past `k = 15`. Start at 5 and increase only if
answers are clearly missing context that retrieval did surface.

The RRF constant (`k` inside the fusion formula, not the same `k` as
above) defaults to 60. The literature consensus is that values between
30 and 100 are indistinguishable in practice. Leave it alone unless
you have measured otherwise.

## Step 7: when to graduate off SQLite

The single-file architecture starts to hurt around the half-million
chunk mark, and earlier if you need multi-writer concurrency. The good
news is that the `Store` interface is small (`index` and `search`), so
swapping the backend is a contained change.

The natural next steps are pgvector if you already run Postgres, or
Qdrant if you want a dedicated vector database with metadata filtering.
Both keep the same retrieval mental model: a lexical signal, an
embedding signal, and a fusion function on top. Reciprocal rank fusion
ports across unchanged.

## What is next

The snippet is the foundation for several follow-ups already in
[`IDEAS.md`](../IDEAS.md): re-ranking with a cross-encoder, query
rewriting before retrieval, and a cached "answer with citations"
endpoint that you can wrap as a tiny SaaS. Pick one if you want to
extend.

If you spot a bug or want to suggest an improvement, open an issue on
the repository.

## Companion files in this repository

- Workflow: [`workflows/rag-starter-sqlite-fts5.md`](../workflows/rag-starter-sqlite-fts5.md)
- Snippet: [`snippets/python/rag_sqlite_starter.py`](../snippets/python/rag_sqlite_starter.py)
- Snippet: [`snippets/python/token_aware_text_splitter.py`](../snippets/python/token_aware_text_splitter.py)
- Snippet: [`snippets/python/reciprocal_rank_fusion.py`](../snippets/python/reciprocal_rank_fusion.py)

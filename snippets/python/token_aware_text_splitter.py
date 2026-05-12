"""
Token-aware text splitter.

Goal: split long text into chunks that fit within a token budget, while keeping
paragraphs and sentences intact whenever possible.

Strategy:
    1. Split the input by blank-line paragraphs.
    2. If a paragraph fits the budget, emit it.
    3. Otherwise, split the paragraph into sentences and pack sentences into
       chunks under the budget. Sentences longer than the budget are split on
       whitespace as a last resort.

Token counting:
    By default we use the `tiktoken` `cl100k_base` encoding, which is a
    reasonable proxy for modern LLM tokenizers. If `tiktoken` is not available,
    we fall back to a coarse char/4 estimate so the code still runs.

Usage:
    from token_aware_text_splitter import split_text
    chunks = split_text(long_string, max_tokens=512, overlap_tokens=32)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List

try:
    import tiktoken  # type: ignore

    _enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(s: str) -> int:
        return len(_enc.encode(s))

except Exception:  # pragma: no cover

    def count_tokens(s: str) -> int:  # type: ignore[misc]
        # Coarse approximation. Reasonable for English prose.
        return max(1, len(s) // 4)


@dataclass
class Chunk:
    text: str
    tokens: int


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'])")


def _split_paragraphs(text: str) -> List[str]:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _split_sentences(paragraph: str) -> List[str]:
    parts = _SENTENCE_END.split(paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def _split_long_sentence(sentence: str, max_tokens: int, counter: Callable[[str], int]) -> List[str]:
    words = sentence.split()
    out: List[str] = []
    buf: List[str] = []
    buf_tokens = 0
    for w in words:
        t = counter(w + " ")
        if buf and buf_tokens + t > max_tokens:
            out.append(" ".join(buf).strip())
            buf, buf_tokens = [], 0
        buf.append(w)
        buf_tokens += t
    if buf:
        out.append(" ".join(buf).strip())
    return out


def split_text(
    text: str,
    *,
    max_tokens: int = 512,
    overlap_tokens: int = 0,
    counter: Callable[[str], int] = count_tokens,
) -> List[Chunk]:
    """Split `text` into chunks under `max_tokens`, with optional overlap.

    Overlap is implemented by prepending the trailing tokens of the previous
    chunk (rounded to whole sentences when possible) to the next chunk.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be in [0, max_tokens)")

    units: List[str] = []
    for para in _split_paragraphs(text):
        if counter(para) <= max_tokens:
            units.append(para)
            continue
        for sentence in _split_sentences(para):
            if counter(sentence) <= max_tokens:
                units.append(sentence)
            else:
                units.extend(_split_long_sentence(sentence, max_tokens, counter))

    chunks: List[Chunk] = []
    buf: List[str] = []
    buf_tokens = 0

    def flush() -> None:
        if not buf:
            return
        text = "\n\n".join(buf).strip()
        chunks.append(Chunk(text=text, tokens=counter(text)))

    for u in units:
        t = counter(u) + (2 if buf else 0)  # rough overhead for the join
        if buf and buf_tokens + t > max_tokens:
            flush()
            if overlap_tokens > 0 and chunks:
                tail = chunks[-1].text.split("\n\n")[-1]
                if counter(tail) <= overlap_tokens:
                    buf = [tail, u]
                    buf_tokens = counter(tail) + counter(u) + 2
                    continue
            buf, buf_tokens = [u], counter(u)
        else:
            buf.append(u)
            buf_tokens += t
    flush()

    return chunks


def _self_test() -> None:
    sample = ("Sentence one. Sentence two. Sentence three.\n\n" * 20).strip()
    chunks = split_text(sample, max_tokens=64, overlap_tokens=0)
    assert chunks, "should produce at least one chunk"
    assert all(c.tokens > 0 for c in chunks)
    print(f"token_aware_text_splitter self-test: OK ({len(chunks)} chunks)")


if __name__ == "__main__":
    _self_test()

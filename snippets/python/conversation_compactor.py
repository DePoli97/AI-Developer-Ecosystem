"""
conversation_compactor - keep long agent conversations under a token budget.

Why this exists:
    A long-running agent's message list grows unboundedly: each tool call,
    tool result, and assistant turn stays in the array. Eventually you hit
    the context window or, much sooner, your wallet. The fix is to summarise
    older turns into a single condensed system note and keep recent turns
    verbatim.

    This module does that mechanically, without requiring an LLM call for
    the summary. It uses a deterministic heuristic summary so the self-test
    runs offline; in production you typically swap that for a Claude call
    that produces a higher-quality summary.

Public API:
    Compactor(target_tokens, recent_turns_kept=4, summariser=None)
        .compact(messages: list[dict], system: str | None = None)
            -> list[dict]

    estimate_tokens(messages, system=None) -> int

Dependencies:
    standard library only.

Self-test:
    python conversation_compactor.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

# 1 token ≈ 4 characters of English; conservative for code-heavy text.
CHARS_PER_TOKEN = 4


def _text_of(content) -> str:
    """Best-effort flattening of Anthropic-style content (list of blocks or string)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("type")
                if t == "text":
                    parts.append(block.get("text", ""))
                elif t == "tool_use":
                    parts.append(f"[tool_use {block.get('name','?')}({block.get('input','')})]")
                elif t == "tool_result":
                    inner = block.get("content", "")
                    if isinstance(inner, list):
                        inner = " ".join(
                            b.get("text", "") if isinstance(b, dict) else str(b) for b in inner
                        )
                    parts.append(f"[tool_result {str(inner)[:400]}]")
                else:
                    parts.append(str(block))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content)


def estimate_tokens(messages: list[dict], system: str | None = None) -> int:
    total_chars = len(system or "")
    for m in messages:
        total_chars += len(m.get("role", ""))
        total_chars += len(_text_of(m.get("content", "")))
    return max(1, total_chars // CHARS_PER_TOKEN)


def _heuristic_summary(messages: list[dict]) -> str:
    """
    Build a short, deterministic summary of a chunk of conversation.
    Picks short factual-looking sentences from user/assistant turns and
    notes how many tool calls happened.
    """
    user_bits: list[str] = []
    assistant_bits: list[str] = []
    tool_calls = 0
    tool_results = 0
    for m in messages:
        role = m.get("role", "")
        text = _text_of(m.get("content", ""))
        for sent in re.split(r"(?<=[.!?])\s+", text):
            sent = sent.strip()
            if 10 <= len(sent) <= 200:
                if role == "user" and len(user_bits) < 3:
                    user_bits.append(sent)
                elif role == "assistant" and len(assistant_bits) < 3:
                    assistant_bits.append(sent)
        if "[tool_use" in text:
            tool_calls += text.count("[tool_use")
        if "[tool_result" in text:
            tool_results += text.count("[tool_result")

    parts: list[str] = []
    if user_bits:
        parts.append("User said: " + " | ".join(user_bits))
    if assistant_bits:
        parts.append("Assistant said: " + " | ".join(assistant_bits))
    if tool_calls or tool_results:
        parts.append(f"Tools: {tool_calls} call(s), {tool_results} result(s).")
    if not parts:
        parts.append("(no salient content extracted)")
    return " ".join(parts)


@dataclass
class CompactionResult:
    messages: list[dict]
    tokens_before: int
    tokens_after: int
    turns_dropped: int


class Compactor:
    def __init__(
        self,
        target_tokens: int,
        *,
        recent_turns_kept: int = 4,
        summariser: Callable[[list[dict]], str] | None = None,
    ) -> None:
        if target_tokens <= 0:
            raise ValueError("target_tokens must be positive")
        if recent_turns_kept < 1:
            raise ValueError("recent_turns_kept must be >= 1")
        self._target = target_tokens
        self._keep = recent_turns_kept
        self._summarise = summariser or _heuristic_summary

    def compact(
        self,
        messages: list[dict],
        system: str | None = None,
    ) -> CompactionResult:
        tokens_before = estimate_tokens(messages, system)
        if tokens_before <= self._target or len(messages) <= self._keep:
            return CompactionResult(
                messages=list(messages),
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                turns_dropped=0,
            )

        head = messages[: -self._keep]
        tail = messages[-self._keep :]
        summary = self._summarise(head)
        compacted_head: list[dict] = [{
            "role": "user",
            "content": f"[conversation-compacted] Earlier turns summarised: {summary}",
        }]
        new_messages = compacted_head + tail

        # If a single rolling summary is not enough, drop more from the tail until under budget
        # but preserve at least 1 recent turn.
        while (
            estimate_tokens(new_messages, system) > self._target
            and len(tail) > 1
        ):
            tail = tail[1:]
            new_messages = compacted_head + tail

        return CompactionResult(
            messages=new_messages,
            tokens_before=tokens_before,
            tokens_after=estimate_tokens(new_messages, system),
            turns_dropped=len(messages) - len(new_messages),
        )


# ── Self-test ────────────────────────────────────────────────────────────────

def _self_test() -> int:
    # Build a long synthetic conversation
    messages: list[dict] = []
    for i in range(30):
        messages.append({
            "role": "user",
            "content": f"Question {i}: " + "padding " * 40,
        })
        messages.append({
            "role": "assistant",
            "content": f"Answer {i}: " + "filler " * 40,
        })

    system = "You are a helpful assistant."
    before = estimate_tokens(messages, system)
    assert before > 1000, before

    # Compact aggressively
    c = Compactor(target_tokens=500, recent_turns_kept=4)
    result = c.compact(messages, system=system)
    assert result.tokens_after <= 500 or len(result.messages) <= 4 + 1, result.tokens_after
    assert result.turns_dropped > 0, result
    # First message should be the compacted summary
    assert "[conversation-compacted]" in _text_of(result.messages[0]["content"])
    # Last message should be one of the originals (tail preserved)
    assert "Answer 29" in _text_of(result.messages[-1]["content"]) or \
           "Question 29" in _text_of(result.messages[-1]["content"]), result.messages[-1]

    # No-op when already under budget
    short = [{"role": "user", "content": "hi"}]
    c2 = Compactor(target_tokens=1000)
    r2 = c2.compact(short)
    assert r2.turns_dropped == 0
    assert r2.messages == short

    # Mixed content (Anthropic-style blocks)
    msgs2 = []
    for i in range(20):
        msgs2.append({"role": "user", "content": [{"type": "text", "text": f"prompt {i} " * 20}]})
        msgs2.append({"role": "assistant", "content": [
            {"type": "text", "text": f"response {i}"},
            {"type": "tool_use", "name": "calc", "input": {"x": i}},
        ]})
        msgs2.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"tu_{i}", "content": "ok"}
        ]})

    tokens = estimate_tokens(msgs2)
    assert tokens > 0
    c3 = Compactor(target_tokens=200, recent_turns_kept=2)
    r3 = c3.compact(msgs2)
    assert r3.tokens_after < tokens, (r3.tokens_after, tokens)
    summary_text = _text_of(r3.messages[0]["content"])
    assert "Tools:" in summary_text, summary_text

    # Invalid configs
    try:
        Compactor(target_tokens=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    try:
        Compactor(target_tokens=100, recent_turns_kept=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")

    print("ok: conversation_compactor self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())

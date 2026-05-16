"""
Claude Agent SDK starter - single-file agent with three sandboxed tools.

This is the companion code for the tutorial:
    tutorials/2026-05-claude-agent-sdk-quickstart.md

What it provides:
    A minimal, production-shaped agent that can read files, list directories,
    and run shell commands within the current working directory. The goal is
    to give you a starting point that is small enough to fully understand and
    serious enough to extend into a real internal tool.

Design notes:
    - Tools are declared as plain dicts so they translate cleanly to any
      MCP-style transport later. No decorators, no DSL.
    - Every tool runner returns a string. If it raises, the exception is
      caught and returned to the model as a tool_result with is_error=True.
      The model recovers gracefully far more often than you would expect.
    - Path access is restricted to the current working directory via
      _safe_path. This is the single most important guardrail when an LLM
      is calling read_file with model-generated paths.

Public API:
    run(question: str) -> str

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python claude_agent_sdk_starter.py "What does this project do?"

Dependencies:
    pip install anthropic
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from anthropic import Anthropic

client = Anthropic()
MODEL = "claude-sonnet-4-6"
ROOT = Path.cwd().resolve()
MAX_STEPS = 10

SYSTEM = (
    "You are a senior engineer helping the user understand a codebase. "
    "Use tools to inspect files before answering. "
    "Quote short snippets when relevant. "
    "Prefer read_file and list_dir over run_shell. "
    "When you have enough information, stop calling tools and answer."
)

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List the immediate contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_shell",
        "description": (
            "Run a shell command with a 10-second timeout. "
            "Returns combined stdout and stderr."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]


def _safe_path(rel: str) -> Path:
    target = (ROOT / rel).resolve()
    if ROOT not in target.parents and target != ROOT:
        raise ValueError(f"refusing path outside of {ROOT}: {rel}")
    return target


def tool_read_file(path: str) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return f"error: {path} is not a file"
    return p.read_text(encoding="utf-8", errors="replace")[:32_000]


def tool_list_dir(path: str) -> str:
    p = _safe_path(path)
    if not p.is_dir():
        return f"error: {path} is not a directory"
    entries = sorted(e.name + ("/" if e.is_dir() else "") for e in p.iterdir())
    return "\n".join(entries) if entries else "(empty)"


def tool_run_shell(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return "error: command timed out after 10s"
    out = (result.stdout or "") + (result.stderr or "")
    return out[:64_000] or "(no output)"


TOOL_RUNNERS = {
    "read_file": tool_read_file,
    "list_dir": tool_list_dir,
    "run_shell": tool_run_shell,
}


def run(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            runner = TOOL_RUNNERS.get(block.name)
            try:
                output = (
                    runner(**block.input) if runner else f"unknown tool: {block.name}"
                )
                is_error = False
            except Exception as exc:  # noqa: BLE001
                output = f"tool raised {type(exc).__name__}: {exc}"
                is_error = True
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return "(agent exceeded max steps without producing a final answer)"


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What does this project do? Read README first."
    print(run(q))

# Build a working Claude agent in 20 minutes with the Claude Agent SDK

*A quickstart that takes you from an empty folder to an agent that can read files, run shell commands, and answer questions about your project. Single Python file, no orchestration framework, no surprises.*

Last updated: 2026-05.  Estimated time: 20 minutes.  Prerequisites: Python 3.10+ and an Anthropic API key in `ANTHROPIC_API_KEY`.

## What you will build

A command-line agent that can:

1. Read a file you point it at.
2. List the contents of a directory.
3. Run a sandboxed shell command and report the output.
4. Answer questions about the project by combining the three above.

By the end of the tutorial you will understand the tool-use loop, the role of system prompts, and the two or three things that go wrong first when you start adding tools.

## Why the Agent SDK and not raw Messages API

The raw Messages API is fine. You can build the same agent in 200 lines without any SDK at all. The Agent SDK adds three things that pay off the moment your agent has more than two tools: a typed tool registry with automatic schema generation, a clean abstraction over the streaming protocol, and well-defined error surfaces when a tool throws. If your agent is one tool deep, skip the SDK. If you expect five, use it.

## Install

    pip install anthropic
    pip install pydantic

We will not pull in any agent framework. The SDK is built into the Anthropic client.

## The full agent, one file

Create `agent.py`:

```python
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from anthropic import Anthropic

client = Anthropic()
MODEL = "claude-sonnet-4-6"

# Tool definitions ───────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a UTF-8 text file from the working directory. "
                       "Returns the file contents as a single string. "
                       "Use this to inspect source code, config files, or notes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file, e.g. 'src/main.py'.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_dir",
        "description": "List the immediate contents of a directory. "
                       "Returns one entry per line. Use this before reading files "
                       "when you do not yet know what is in the project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path. Use '.' for the current directory.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_shell",
        "description": "Run a single shell command and return stdout and stderr. "
                       "The command runs with a 10-second timeout and a 64 KB output cap. "
                       "Use sparingly; prefer read_file and list_dir when possible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The full shell command, e.g. 'wc -l src/main.py'.",
                }
            },
            "required": ["command"],
        },
    },
]

ROOT = Path.cwd().resolve()


def _safe_path(rel: str) -> Path:
    target = (ROOT / rel).resolve()
    if ROOT not in target.parents and target != ROOT:
        raise ValueError(f"refusing to access path outside of {ROOT}: {rel}")
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


# Agent loop ─────────────────────────────────────────────────────────────────

SYSTEM = (
    "You are a senior engineer helping the user understand a codebase. "
    "Use tools to inspect files before answering. "
    "Quote short snippets when relevant. "
    "Prefer read_file and list_dir over run_shell. "
    "When you have enough information, stop calling tools and answer."
)

MAX_STEPS = 10


def run(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if b.type == "text")

        # Otherwise we have at least one tool_use block. Append the assistant
        # turn verbatim, then append a user turn with all tool_result blocks.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            runner = TOOL_RUNNERS.get(block.name)
            try:
                output = runner(**block.input) if runner else f"unknown tool: {block.name}"
                is_error = False
            except Exception as exc:  # noqa: BLE001
                output = f"tool raised {type(exc).__name__}: {exc}"
                is_error = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
                "is_error": is_error,
            })

        messages.append({"role": "user", "content": tool_results})

    return "(agent exceeded max steps without producing a final answer)"


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What does this project do? Read README first."
    print(run(q))
```

## Run it

    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py "Summarise the README and list the top-level files."

Expected output: a short summary, derived from the model first calling `read_file` on `README.md`, then optionally `list_dir` on `.`, then producing a final natural-language answer.

## Things that go wrong, in the order they will go wrong

The first thing that breaks is the conversation shape. The Messages API is strict about the alternation between assistant tool-use blocks and user tool-result blocks. If you forget to append `response.content` verbatim before sending tool results back, the API will reject the next call. The pattern in the loop above is the only one that works.

The second thing that breaks is tool-input validation. The model will, occasionally, send an `input` that does not match your schema (especially for tools with many optional fields). Catch the exception in the runner and return it as the tool result with `is_error: true`. The model will read your error message and retry. Do not crash the agent on tool errors.

The third thing that breaks is loops. A poorly-described tool, or a system prompt that does not tell the model when to stop, produces agents that call the same tool ten times in a row. Two mitigations: a hard step limit (above we use ten) and explicit stop conditions in the system prompt (above: "when you have enough information, stop calling tools and answer").

## Going further

Add a fourth tool that writes a file. The schema is the same shape; the runner uses `Path.write_text` with the same `_safe_path` guard. Once you have read, list, and write, you have the building blocks of a code-modification agent - at which point the next problem is observability, which is what `snippets/python/streaming_response_logger.py` solves.

The whole agent above is reproduced in [`snippets/python/claude_agent_sdk_starter.py`](../snippets/python/claude_agent_sdk_starter.py) and can be dropped into any project as a starting point.

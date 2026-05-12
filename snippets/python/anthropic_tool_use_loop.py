"""
Minimal Claude tool-use loop.

Pairs with the article: articles/2026-05-claude-tool-use-practical-guide.md

Requires:
    pip install anthropic>=0.39 pydantic>=2.7

Set ANTHROPIC_API_KEY in your environment.

Run:
    python anthropic_tool_use_loop.py "What is 2 + 2, and what time is it in UTC?"

Design goals:
    - Validate every tool input with pydantic before running the tool body.
    - Return structured errors to the model so it can recover.
    - Cap the loop with a hard step limit.
    - Keep the call site small enough to copy into a real project.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable

from anthropic import Anthropic
from pydantic import BaseModel, Field, ValidationError


# --- Tool runner types -------------------------------------------------------


class ToolValidationError(Exception):
    """Raised when a tool's input is invalid in a way the model can fix."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    runner: Callable[[dict[str, Any]], str]


# --- Example tools -----------------------------------------------------------


class AddArgs(BaseModel):
    a: float = Field(..., description="First addend.")
    b: float = Field(..., description="Second addend.")


def run_add(raw: dict[str, Any]) -> str:
    try:
        args = AddArgs.model_validate(raw)
    except ValidationError as e:
        raise ToolValidationError(f"Invalid arguments for `add`: {e}") from e
    return json.dumps({"sum": args.a + args.b})


class UtcTimeArgs(BaseModel):
    """No arguments; kept as an explicit empty model for symmetry."""

    pass


def run_utc_time(raw: dict[str, Any]) -> str:
    UtcTimeArgs.model_validate(raw)  # rejects unexpected keys
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return json.dumps({"utc_now": now})


TOOLS: list[Tool] = [
    Tool(
        name="add",
        description=(
            "Add two numbers and return their sum. "
            "Call this tool whenever you need to compute a + b for any numbers. "
            "Do not use it for non-numeric inputs."
        ),
        input_schema=AddArgs.model_json_schema(),
        runner=run_add,
    ),
    Tool(
        name="utc_time",
        description=(
            "Return the current time in UTC as an ISO 8601 string. "
            "Call this only when the user explicitly asks for the current time."
        ),
        input_schema=UtcTimeArgs.model_json_schema(),
        runner=run_utc_time,
    ),
]


# --- Loop --------------------------------------------------------------------


def run_agent(
    client: Anthropic,
    tools: list[Tool],
    user_message: str,
    *,
    model: str = "claude-sonnet-4-6",
    system: str = "You are a careful assistant. Use tools when they help.",
    max_steps: int = 8,
    max_tokens: int = 1024,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the agent loop until the model ends its turn or the step limit hits.

    Returns (final_assistant_text, full_message_history).
    """
    runners = {t.name: t.runner for t in tools}
    api_tools = [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools
    ]

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    for _ in range(max_steps):
        response = client.messages.create(
            model=model,
            system=system,
            tools=api_tools,
            messages=messages,
            max_tokens=max_tokens,
        )

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return text, messages

        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            runner = runners.get(block.name)
            if runner is None:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "is_error": True,
                        "content": f"Unknown tool: {block.name}.",
                    }
                )
                continue
            try:
                output = runner(block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
            except ToolValidationError as e:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "is_error": True,
                        "content": str(e),
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "[Agent stopped: step limit reached.]", messages


def main() -> int:
    user_message = " ".join(sys.argv[1:]) or "What is 17 + 25?"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your environment.", file=sys.stderr)
        return 1
    client = Anthropic(api_key=api_key)
    text, _ = run_agent(client, TOOLS, user_message)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

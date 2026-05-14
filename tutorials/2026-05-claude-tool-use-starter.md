# Build Your First Claude Tool-Use Agent in 30 Minutes

**Difficulty:** Beginner–Intermediate  
**Time:** ~30 minutes  
**Prerequisites:** Python 3.10+, an Anthropic API key  
**What you'll build:** A working agent that can search a product catalogue and calculate prices — entirely driven by Claude's tool-use loop.

---

## Why tool use matters

Plain chat completion is stateless and limited to what the model already knows. Tool use (also called "function calling") lets Claude decide *when* to call external code and *how* to interpret the result. The model reasons about which tool to invoke, constructs the arguments, and integrates the response into its answer — all in a structured, inspectable loop.

This is the foundation of every real-world agent: RAG pipelines, browser automation, coding assistants, and data-analysis bots are all variations of the same loop you'll build here.

---

## Project structure

```
tool-use-starter/
├── agent.py         # main agent loop
├── tools.py         # tool implementations
└── run.py           # thin CLI entrypoint
```

Create the directory and move into it:

```bash
mkdir tool-use-starter && cd tool-use-starter
pip install anthropic>=0.28
```

Set your key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Step 1 — Define your tools

Claude needs two things for each tool: a **JSON Schema** describing its signature, and a **Python function** to actually run it.

Create `tools.py`:

```python
"""
tools.py  –  Tool implementations and their JSON Schema declarations.

The TOOL_SCHEMAS list is passed verbatim to the Anthropic API.
The dispatch() function routes a tool_use block to the right function.
"""

from __future__ import annotations

# ── Fake product catalogue ────────────────────────────────────────────────────

_CATALOGUE: dict[str, dict] = {
    "gpt-wrapper-pro": {"name": "GPT Wrapper Pro", "price_usd": 29.00, "in_stock": True},
    "vector-db-starter": {"name": "Vector DB Starter Kit", "price_usd": 49.00, "in_stock": True},
    "agent-loop-template": {"name": "Agent Loop Template", "price_usd": 19.00, "in_stock": False},
    "prompt-toolkit": {"name": "Prompt Engineering Toolkit", "price_usd": 39.00, "in_stock": True},
}

# ── Tool implementations ──────────────────────────────────────────────────────

def search_products(query: str) -> list[dict]:
    """Return products whose name contains *query* (case-insensitive)."""
    q = query.lower()
    return [
        {"id": pid, **info}
        for pid, info in _CATALOGUE.items()
        if q in info["name"].lower()
    ]


def get_product_price(product_id: str) -> dict:
    """Return the price and stock status for a single product."""
    if product_id not in _CATALOGUE:
        return {"error": f"Product '{product_id}' not found."}
    info = _CATALOGUE[product_id]
    return {"product_id": product_id, "price_usd": info["price_usd"], "in_stock": info["in_stock"]}


def calculate_cart_total(items: list[dict]) -> dict:
    """
    Sum a cart.
    Each item: {"product_id": str, "quantity": int}
    Returns total_usd and a per-line breakdown.
    """
    lines = []
    total = 0.0
    for item in items:
        pid = item.get("product_id", "")
        qty = int(item.get("quantity", 1))
        if pid not in _CATALOGUE:
            lines.append({"product_id": pid, "error": "not found"})
            continue
        unit = _CATALOGUE[pid]["price_usd"]
        subtotal = unit * qty
        total += subtotal
        lines.append({"product_id": pid, "unit_price_usd": unit, "quantity": qty, "subtotal_usd": subtotal})
    return {"lines": lines, "total_usd": round(total, 2)}


# ── JSON Schema declarations ──────────────────────────────────────────────────
# These go straight into the `tools` parameter of messages.create().

TOOL_SCHEMAS = [
    {
        "name": "search_products",
        "description": (
            "Search the product catalogue by keyword. "
            "Returns a list of matching products with IDs, names, prices, and stock status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keyword to search for, e.g. 'agent' or 'prompt'"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_product_price",
        "description": "Get the exact price and stock status for a product by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "string", "description": "The product's unique slug identifier"}
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "calculate_cart_total",
        "description": "Calculate the total price for a shopping cart of products and quantities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                        "required": ["product_id", "quantity"],
                    },
                    "description": "List of cart items with product IDs and quantities",
                }
            },
            "required": ["items"],
        },
    },
]

# ── Dispatcher ────────────────────────────────────────────────────────────────

_REGISTRY = {
    "search_products": search_products,
    "get_product_price": get_product_price,
    "calculate_cart_total": calculate_cart_total,
}


def dispatch(tool_name: str, tool_input: dict):
    """Call the tool function matching *tool_name* with *tool_input* kwargs."""
    fn = _REGISTRY.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
```

---

## Step 2 — Build the agent loop

The core of any tool-use agent is a loop: send a message → if Claude returns a `tool_use` block, run the tool → send the result back → repeat until Claude returns only text.

Create `agent.py`:

```python
"""
agent.py  –  Minimal production-ready Claude tool-use loop.

Loop shape:
    user message
        → Claude (may request tools)
        → run tools, return results
        → Claude (may request more tools, or finish)
        → ...
        → final text answer

Hard limits:
    MAX_STEPS prevents infinite loops if a tool result triggers more tools.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

from tools import TOOL_SCHEMAS, dispatch

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL = "claude-opus-4-6"
MAX_STEPS = 10  # hard ceiling on tool-call rounds per conversation turn
SYSTEM_PROMPT = """You are a helpful shopping assistant for an AI developer tools store.
Use the available tools to look up products and prices accurately.
Always confirm stock status before recommending a product.
Present prices clearly in USD."""


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(user_message: str, *, verbose: bool = False) -> str:
    """
    Run the full tool-use loop for a single user turn.

    Parameters
    ----------
    user_message:
        The natural-language request from the user.
    verbose:
        If True, print each tool call and result to stdout.

    Returns
    -------
    str
        Claude's final text answer after all tool calls are resolved.
    """
    client = anthropic.Anthropic()

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        # Append Claude's response to the conversation history.
        messages.append({"role": "assistant", "content": response.content})

        # If Claude is done (no tool calls), return the text.
        if response.stop_reason == "end_turn":
            return _extract_text(response.content)

        # If Claude stopped to use tools, run them all and continue.
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                if verbose:
                    print(f"\n[tool_use] {block.name}({json.dumps(block.input, indent=2)})")

                result = dispatch(block.name, block.input)

                if verbose:
                    print(f"[tool_result] {json.dumps(result, indent=2)}")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

            # Feed all results back in a single user turn.
            messages.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason — surface it rather than silently looping.
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason!r}")

    raise RuntimeError(f"Agent exceeded MAX_STEPS ({MAX_STEPS}) without finishing.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(content: list) -> str:
    parts = [block.text for block in content if hasattr(block, "text")]
    return "\n".join(parts).strip()
```

---

## Step 3 — Wire up the CLI

Create `run.py`:

```python
"""
run.py  –  Interactive CLI for the shopping agent.
Run:  python run.py
"""

from agent import run_agent

EXAMPLES = [
    "What agent-related products do you have?",
    "How much does the Prompt Engineering Toolkit cost, and is it in stock?",
    "I want 2 copies of the Vector DB Starter Kit and 1 Prompt Engineering Toolkit. What's my total?",
]

def main():
    print("=== Claude Tool-Use Shopping Agent ===")
    print("Type a question, or press Enter to cycle through examples. Ctrl-C to quit.\n")

    example_idx = 0
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            if example_idx < len(EXAMPLES):
                user_input = EXAMPLES[example_idx]
                example_idx += 1
                print(f"You (example): {user_input}")
            else:
                print("(No more examples — type your own question.)")
                continue

        answer = run_agent(user_input, verbose=True)
        print(f"\nAgent: {answer}\n")


if __name__ == "__main__":
    main()
```

---

## Step 4 — Run it

```bash
python run.py
```

Press Enter three times to cycle through the built-in examples. You should see the tool calls printed in `[tool_use]` / `[tool_result]` blocks, followed by Claude's final answer.

Sample output for "I want 2 copies of the Vector DB Starter Kit and 1 Prompt Engineering Toolkit. What's my total?":

```
[tool_use] calculate_cart_total({
  "items": [
    {"product_id": "vector-db-starter", "quantity": 2},
    {"product_id": "prompt-toolkit", "quantity": 1}
  ]
})
[tool_result] {"lines": [...], "total_usd": 137.0}

Agent: Your cart total is $137.00:
- Vector DB Starter Kit × 2 = $98.00
- Prompt Engineering Toolkit × 1 = $39.00
Both items are in stock.
```

---

## How the loop works — visually

```
User message
     │
     ▼
┌─────────────┐   stop_reason=tool_use   ┌──────────────────┐
│   Claude    │ ────────────────────────▶│  dispatch()      │
│  (API call) │                          │  run tool(s)     │
│             │ ◀────────────────────────│  return results  │
└─────────────┘   tool_result messages   └──────────────────┘
     │
     │ stop_reason=end_turn
     ▼
 Final text answer
```

Multiple tools can be called in a single round. Claude batches all `tool_use` blocks, you run them in parallel if you like, and send all `tool_result` blocks back in one message. This tutorial runs them sequentially for simplicity.

---

## Common mistakes to avoid

| Mistake | Fix |
|---|---|
| Returning a Python dict instead of a JSON string in `tool_result.content` | Always `json.dumps(result)` |
| Forgetting to append Claude's response to `messages` before the next call | The history must include every assistant turn |
| No `MAX_STEPS` ceiling | A buggy tool can cause an infinite loop |
| Mixing tool result order | Match `tool_use_id` exactly — Claude correlates by ID, not position |
| Swallowing tool exceptions silently | Return `{"error": str(exc)}` so Claude can explain the failure |

---

## Next steps

- **Parallelise tool calls** with `asyncio.gather` for latency-sensitive agents.
- **Add streaming** using `client.messages.stream()` to surface partial text as Claude thinks.
- **Add real tools** — web search, a database query, a calculator — by extending `TOOL_SCHEMAS` and `_REGISTRY` in `tools.py`.
- **Persist conversation history** across turns for multi-turn support; `messages` is already the right shape to serialise.
- **Read the companion workflow:** [Agent Loop with Tool Use](../workflows/agent-loop-with-tool-use.md) for production hardening notes.

---

*Part of the [AI Developer Ecosystem](../README.md) — practical guides for AI engineers.*

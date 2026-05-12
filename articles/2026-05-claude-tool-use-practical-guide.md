# A practical guide to Claude tool use

Published: 2026-05-12. Author: Paolo De Poli. License: CC BY 4.0.

Summary: tool use turns Claude from a text generator into something that can act. The mechanics are simple; the hard part is designing tools the model will actually call correctly, validating what it sends you, and recovering when something goes wrong. This article walks through the patterns that hold up in production.

## The mental model

A tool is a function with a name, a description, and a JSON Schema for its inputs. You give Claude the list of tools at the start of a conversation. When Claude decides a tool is the right next step, it emits a structured request with the tool name and the arguments. Your code runs the function and returns the result as a new message. Claude reads the result and continues.

That loop, plus a stopping condition, is the entire agent. Everything else is design.

## Tool definitions that the model calls correctly

The description is the prompt. It is the only thing the model has to decide whether and how to use this tool. The schema constrains the shape; the description teaches the intent. Treat it the way you would treat a function docstring written for another developer who will never read your code.

Three rules pay for themselves.

First, lead with the verb. "Search the customer's order history" beats "A function that you can use to look up orders for the user". The model reads top to bottom; the first phrase carries most of the weight.

Second, describe when not to call it, not just when to call it. If `search_orders` should only be called after you have a confirmed customer ID, say so. The model will hallucinate calls less often when you draw the boundary explicitly.

Third, use `enum` and tight types in the schema wherever the real-world value is finite. "Status" is not a string; it is one of `pending`, `paid`, `shipped`, `cancelled`. The model is much better at picking from a closed set than at producing free-form values that happen to match an internal vocabulary.

## Validate everything the model sends

Tool inputs are untrusted, even when they came from a model you trust. JSON Schema validation at your runtime is non-negotiable. Beyond that, do a second layer of semantic validation: a date that parses is not necessarily a date that makes sense in your domain.

The pattern that works:

1. Parse the tool input against the schema. If it fails, return a structured error to the model with the validation message, not an exception. The model will usually fix and retry on its own.
2. Apply domain rules (date ranges, allowed combinations of fields, authorization checks).
3. Execute.
4. Shape the result into something compact the model can read. Trim noisy fields. Keep response payloads under a few KB when you can.

The point of step four is that every tool result becomes part of the next prompt. Verbose results burn tokens, slow the loop, and dilute the model's attention.

## Returning errors so the agent recovers

The single biggest quality win in agent design is returning structured errors that the model can act on. A 500 with a stack trace is a dead end; a message that says "The order ID `12345` is not in the system. If the user just placed an order, suggest waiting 30 seconds and trying again." is a productive next step.

Three categories cover most situations:

Recoverable, retry-now. The call failed for a transient reason. Tell the model it can retry, and ideally hint at a backoff or a different argument.

Recoverable, change something. The arguments were wrong, the resource is gated, or the request needs to be rephrased. Tell the model exactly what to change.

Terminal. The call cannot succeed for this conversation; the model should explain to the user and stop. Make it unambiguous so the model does not loop.

## Stop conditions

An agent without a stop condition is a budget leak waiting to happen. Two are enough for most workloads.

A hard step limit. Pick a number based on the task (six to twelve is reasonable for many agents) and stop the loop when it is reached. Return a message to the user that explains what was attempted.

A cost limit. Track tokens and tool-call counts per conversation. When either crosses a threshold, stop. The threshold is a product decision: a free-tier chat is not the same as an enterprise workflow.

Both should be enforced outside the model. Asking the model to count its own steps is not a stop condition; it is a suggestion.

## A minimal loop in Python

The shape of a working loop:

```python
def run_agent(client, tools, tool_runners, system, user_message, max_steps=10):
    messages = [{"role": "user", "content": user_message}]
    for step in range(max_steps):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            system=system,
            tools=tools,
            messages=messages,
            max_tokens=2048,
        )
        if response.stop_reason == "end_turn":
            return response, messages
        if response.stop_reason != "tool_use":
            return response, messages
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            runner = tool_runners.get(block.name)
            if runner is None:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "is_error": True,
                    "content": f"Unknown tool: {block.name}",
                })
                continue
            try:
                output = runner(block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
            except ToolValidationError as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "is_error": True,
                    "content": str(e),
                })
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    return None, messages
```

The runner abstraction is what makes this maintainable. Each tool has a single entry point that takes validated input and returns either a value or raises a `ToolValidationError`. Tests target the runners, not the loop.

## Observability

You will not debug an agent from logs of `print(response)` calls. Capture, for each step: the messages going in, the tool definitions in scope, the model output (including any tool calls), the tool input, the tool output, and the wall-clock and token costs. Store these as structured records keyed by a `conversation_id` and a `step_index`. A tiny SQLite table is enough to start. The instant you have this, fixing agents stops feeling like guesswork.

## What we are not covering

Streaming, parallel tool calls, prompt caching, and prompt-injection defenses around tool use each deserve their own article. They are on the backlog in `IDEAS.md`. The shape of the loop above generalizes to all of them.

## See also

The runnable counterpart of this article lives in `snippets/python/anthropic_tool_use_loop.py`. The same pattern as a starter project is on the roadmap as a template.

## Changelog

2026-05-12: first published.

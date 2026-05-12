# Workflow: agent loop with tool use

Use when you are building an LLM-driven agent that takes multiple steps, calling tools between turns, and you want the loop to be predictable, debuggable, and safe to ship.

## The problem

A single LLM call does not solve most real product problems. The agent has to look something up, call an API, transform a result, and only then answer. The naive loop ("keep calling the model until it stops calling tools") is easy to write and very hard to operate: it can run forever, leak budget, return cryptic errors, and silently degrade as prompts drift.

## The shape

There are four moving parts.

The model client. Anthropic's API in our examples, but the pattern is the same elsewhere.

A tool registry. Each tool has a name, a description that explains when to call it (and when not to), a JSON Schema for its inputs, and a single runner function that takes validated input and returns a string the model will read.

A loop with a hard step limit. The loop alternates between asking the model and running tools, and bails out cleanly when a step limit, cost limit, or terminal error is reached.

A trace log. Every step is written to a structured store so failures are diagnosable later.

## Concrete reference

The minimal Python implementation lives in `snippets/python/anthropic_tool_use_loop.py`. The companion article is `articles/2026-05-claude-tool-use-practical-guide.md`. Use the snippet as the spine of your loop and add the parts your product needs:

Streaming, when latency matters more than total cost.

A cost ceiling, when calls can be expensive.

A persistent trace log (SQLite is enough to start) so you can replay any conversation by ID.

Authorization gates inside each tool runner; never assume the conversation has the user's permission for everything the model might decide to do.

## Failure modes to design for

The model picks a tool that almost matches. Tighten the description and add an enum where possible.

The model calls a tool with plausible-but-wrong arguments. Validate strictly and return a structured error; the model will fix it more often than not.

The agent loops because every tool result is unactionable. Cap steps. Add a terminal-error category that ends the loop with a clean user-facing message.

The agent succeeds but the answer is wrong. Add a final-step verification (a second model call that re-reads the conversation and checks the answer) only when the cost is justified.

## Anti-patterns

Letting the model decide when to stop. It will not, reliably. Step limits are external.

Returning raw exception strings to the model. Translate them into something actionable, every time.

Bolting on retries inside the runners and also at the loop level. Pick one place to handle transience.

## See also

- Article: `articles/2026-05-claude-tool-use-practical-guide.md`
- Snippet: `snippets/python/anthropic_tool_use_loop.py`
- Snippet: `snippets/python/retry_with_backoff.py`

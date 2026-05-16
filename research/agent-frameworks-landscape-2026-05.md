# Agent frameworks landscape, May 2026

A field comparison of the agent frameworks that matter for production
Python and TypeScript work, with honest trade-offs and a recommendation
for each project profile. Not a feature checklist; a decision aid.

Scope: frameworks where you can ship a real internal tool with five tools,
sub-agents, durable state, and observability without writing the same
plumbing yourself. Out of scope: low-code orchestrators, GUI agent builders,
and pure prompt-template libraries.

## Frameworks covered

The shortlist, in alphabetical order: Claude Agent SDK, CrewAI, LangGraph,
LlamaIndex Agents, Microsoft AutoGen, Pydantic AI, and the raw Anthropic /
OpenAI SDKs.

Frameworks deliberately excluded: BabyAGI and AutoGPT (archived or
unmaintained), LangChain core (use LangGraph for new work), Semantic Kernel
(in a transition that makes recommending the current version risky).

## Decision axes

The five axes that matter, in rough order of impact on day-to-day work.

The first axis is conversation-state ergonomics. Most failures in agent
code come from mishandling the tool-use protocol's strict alternation
between assistant tool_use blocks and user tool_result blocks. Frameworks
that hide this well (Claude Agent SDK, Pydantic AI) save a category of
bugs. Frameworks that expose the graph directly (LangGraph) give you more
power at the cost of a longer learning curve.

The second axis is tool definition. Plain Python functions with type hints
that produce JSON Schema automatically (Pydantic AI, FastAgents) are the
ergonomic high-water mark. Dict-based definitions (Claude Agent SDK,
OpenAI tools) are explicit and portable. Decorator-heavy systems (some
CrewAI patterns) feel productive at first but make tools harder to test
in isolation.

The third axis is sub-agent orchestration. Once you go beyond five tools,
the right architecture is a planner that fans out to sub-agents. LangGraph
models this as a state graph; AutoGen as message-passing actors; Claude
Agent SDK as nested agent invocations. There is no single correct shape;
the question is whether the framework you pick exposes one cleanly.

The fourth axis is durability and observability. Long-running agents need
checkpointing, replay, and trace inspection. LangGraph and Temporal-based
setups lead here. Lightweight frameworks expect you to add this yourself,
which is fine for prototypes and painful in production.

The fifth axis is ecosystem fit. If the rest of your stack is FastAPI plus
Pydantic, Pydantic AI is the path of least friction. If it is TypeScript,
the Vercel AI SDK and the Mastra framework are the relevant options. If you
are running on the Anthropic API exclusively, the Claude Agent SDK is hard
to beat for ergonomics.

## Framework-by-framework notes

### Claude Agent SDK

The best ergonomics for Anthropic-only projects. Tool definitions are
plain dicts; the conversation loop is exposed but the protocol details are
handled. The SDK ships with first-class support for sub-agents and a
clean error model for tool failures.

When to choose it: you are committed to Anthropic models, you want to
ship something useful in a few days, and your team is comfortable reading
the SDK source when something surprises you. Our
[quickstart](../tutorials/2026-05-claude-agent-sdk-quickstart.md) walks
through the minimal version end-to-end.

When to avoid it: you need to mix models across providers in the same
agent, or you need durable workflows with restart-from-checkpoint.

### LangGraph

The most mature framework for graph-structured agents. State is explicit,
transitions are typed, and checkpointing is built in. The learning curve
is real - you will spend a day reading the conceptual docs before your
first agent feels right - but the payoff is substantial when the agent has
more than a handful of states.

When to choose it: the agent has branching logic that does not fit a
linear tool-use loop, you need durability, or you anticipate a
long-running multi-turn workflow with human-in-the-loop steps.

When to avoid it: a simple tool-use loop is enough, the team does not
have the bandwidth for the conceptual overhead, or you want to minimize
external dependencies.

### Pydantic AI

The most ergonomic option in 2026 for Python teams that already use
Pydantic. Tools are typed functions; the framework derives schemas
automatically; the conversation loop is hidden but escape hatches are
clean. Multi-provider support is first-class.

When to choose it: the rest of your stack is Pydantic-heavy, you want
typed tool inputs out of the box, and you value being able to mix
providers.

When to avoid it: you need very fine-grained control over the
conversation, or you are committed to a non-Python target.

### LlamaIndex Agents

Best when retrieval is the centerpiece. LlamaIndex's retrieval primitives
are excellent; the agent layer is competent but not the headline. If you
are building a "talk to your docs" application that needs to grow into an
agent, starting in LlamaIndex and growing into its agent layer is a
reasonable path.

When to choose it: retrieval-heavy product, knowledge-graph integration,
team already invested in the LlamaIndex ecosystem.

When to avoid it: agents that touch many external systems but few
documents, or projects where the retrieval layer is custom.

### Microsoft AutoGen

A research-grade framework with a strong multi-agent conversation model.
Production maturity is improving but still trails LangGraph. Best for
experiments with novel agent topologies (debate, critique loops,
role-play).

When to choose it: you are exploring multi-agent dynamics, or you have
research goals adjacent to the product.

When to avoid it: you want the boring path to production.

### CrewAI

Quick to get a multi-agent demo running. Production stories are mixed.
Tool definitions feel productive at first but the testing story is
weaker than the alternatives.

When to choose it: time-boxed prototype, internal demo, hackathon.

When to avoid it: production system with quality bars.

### Raw SDKs

The Anthropic SDK and the OpenAI SDK can build a single-tool or two-tool
agent in 200 lines of clear Python. For some teams this is the right
choice for years - the code stays inspectable, dependencies stay small,
and the conceptual model stays simple.

When to choose it: one or two tools, one model provider, small team that
values reading their own code.

When to avoid it: more than five tools, sub-agent orchestration, durable
workflows.

## Recommendations by profile

A solo developer or small team committed to Claude: Claude Agent SDK.
The ergonomics-to-power ratio is the best in this segment.

A team that needs multi-provider routing in production: Pydantic AI.

A team that needs durable, graph-structured workflows: LangGraph.

A retrieval-first product: LlamaIndex Agents.

A team doing research on multi-agent dynamics: AutoGen.

A team that wants to keep dependencies minimal: raw Anthropic SDK.

## What changes next

The most likely consolidation over the next 12 months: LangGraph and
Pydantic AI absorb the design lessons from each other and the gap
narrows. The Claude Agent SDK keeps adding sub-agent ergonomics. AutoGen
either matures into production or stays research-flavoured. The
"frameworks" tier becomes about three serious options for production
work, and the choice becomes routine.

If you are picking today, optimize for the framework that minimizes the
ramp time for your team. The protocol-level skills (tool-use loop, JSON
schema design, prompt-as-code) transfer freely across frameworks; the
framework-specific muscle memory does not, and is the part you have to
re-learn when you switch.

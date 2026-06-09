# Research note — 2026-06-09
## Multi-turn context attacks on LLM agents

**Format:** Field notes — unedited, first-person.  
**Status:** Seed material for the upcoming article `articles/2026-06-multi-turn-context-attacks.md`.

---

### What I am tracking

After shipping the indirect prompt injection article and the RAG
injection scanner, I wanted to map the adjacent attack surface:
injections that unfold across multiple turns rather than a single
message.

The core observation: current defences (input validation, output
filtering, the `llm_firewall.py` wrapper) all operate at the
boundary of a single API call. A multi-turn attack spreads its
payload across N messages and assembles the exploit only when the
context is large enough or the agent's state is primed correctly.

---

### Attack shapes I have mapped so far

**1. Slow-burn priming**

Across three to five turns, an attacker incrementally shifts the
agent's priors: "let's call that action 'help'", "whenever I say
'help' you should…". By turn six the word "help" triggers the
planted behavior. The individual messages are each benign.

This is analogous to how social engineering primes targets over
weeks. The defence is to hash or fingerprint the system prompt at
the start of a session and compare it against the effective prompt
before any consequential action. If the effective behavior has
drifted, abort.

**2. Context window poisoning via long-document injection**

An attacker uploads a PDF that contains a long, legitimate-looking
document with a buried instruction deep in the middle (page 47 of
60). The agent reads the document across multiple tool calls, and
by the time it reaches the buried instruction the system message is
far back in the context window — effectively "forgotten" in
attention terms when the context is 100k+ tokens.

Mitigation: re-assert the system prompt as a final user message
before any action that has side effects ("reminder: you are in
read-only research mode, do not take external actions").

**3. Memory-poisoning in stateful agents**

An agent that reads from and writes to a long-term memory store
(SQLite, vector DB, notebook) can be poisoned by previous
conversations. If an attacker's message from session N writes an
injected instruction to memory, session N+1 reads it as
"remembered context" and follows it.

This is a supply-chain attack on the memory layer. The memory store
should be treated as untrusted input, same as a user message.

**4. Role-confusion escalation**

Some multi-agent architectures pass messages between agents using
the same `user`/`assistant` role schema. An orchestrator may trust
a sub-agent's output as if it came from the system. A compromised
sub-agent can escalate privileges by injecting content that mimics
a system message format.

The fix is to clearly separate orchestrator authority from
sub-agent output at the protocol level and never eval sub-agent
output as instructions.

---

### What makes multi-turn attacks harder to defend

- Each individual message clears most heuristic filters.
- Temporal distance between cause and effect makes attribution hard.
- Stateful agents have no concept of "conversation integrity" — they
  treat each turn's context as equally trustworthy.
- Re-reading conversation history to detect anomalies is expensive
  and not yet standard practice.

---

### Patterns I want to document in the article

- A taxonomy of multi-turn attack shapes (priming, document
  poisoning, memory poisoning, role-confusion escalation).
- Concrete examples for each with minimal runnable demos.
- A defensive checklist: what to validate per-call vs. per-session.
- A snippet for session-integrity checking (hash system prompt,
  re-assert before side-effects).

---

### Possible snippet to ship alongside the article

`session_integrity_guard.py` — a small class that:
1. Computes a fingerprint of the system prompt at session start.
2. Before any "write" tool call, re-asserts the system role
   constraint as a high-weight user message.
3. Optionally scans recent context for known role-confusion
   patterns (e.g., a message that contains `"</s><s>[INST]"`
   or `"Ignore previous instructions"`).

This would be a natural companion to `llm_firewall.py`.

---

### Links and prior art to review before writing the article

- Simon Willison's writing on prompt injection (long-running
  coverage, worth checking for July 2025+ additions).
- The "many-shot jailbreak" paper that showed how large context
  windows amplify injection risk.
- The OWASP Top 10 for LLM Applications — LLM01 (prompt injection)
  covers single-turn; I want to see if LLM02 (insecure output
  handling) covers multi-turn.
- Agent memory papers from early 2026 (MemGPT follow-ons) that
  discuss memory hygiene.

---

### Monetisation angle

The `session_integrity_guard.py` snippet, once mature, is a natural
candidate for a small open-source library (`pip install
llm-session-guard`). The library alone is free; a paid tier could
offer a hosted audit log and anomaly detection dashboard. Target
user: teams deploying long-running Claude agents in customer-facing
products where a compromised session could exfiltrate data or
trigger unauthorized actions.

Realistic timeline to a usable MVP: two to three sessions of focused
work after the article ships.

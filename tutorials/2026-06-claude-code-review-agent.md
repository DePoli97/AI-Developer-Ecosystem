# Build a code-review agent with the Claude Agent SDK

**Level:** Intermediate  
**Time:** ~30 minutes  
**Requires:** Python 3.11+, `anthropic` package, an Anthropic API key

---

A code-review agent takes a unified diff, uses Claude as the
reasoning core, and returns a structured verdict with per-line
issues.  The finished snippet lives at
[`snippets/python/code_review_agent.py`](../snippets/python/code_review_agent.py).
This tutorial explains every layer: the diff parser, the rule-based
offline mode, and the Claude-powered agent loop.

---

## Why a code-review agent?

Pull-request review is one of the highest-value agentic tasks for
an engineering team: it is repetitive, requires context the model
already has (common bug patterns, security anti-patterns, style
conventions), and has a clear, auditable output. The agent does not
replace human reviewers — it raises the floor so that humans spend
less time on obvious issues.

Secondary benefit: this is a textbook exercise in the
**tool-use loop pattern**.  The agent has two tools, calls them
selectively, and terminates when it has enough information.  The
pattern scales to any domain.

---

## Architecture overview

```
unified diff
    │
    ▼
DiffSummariser ──► structural summary (files, totals, risks)
    │
    ▼
Agent loop (Claude)
    ├── tool: get_diff_summary  → structural summary JSON
    └── tool: inspect_added_lines(path) → list of added lines
    │
    ▼
JSON review: { summary, verdict, issues[] }
```

The agent never receives the full diff in the prompt. It fetches
what it needs through tools. This pattern keeps token usage low on
large diffs and prevents the model from hallucinating file contents
it did not actually read.

---

## The diff parser

`diff_summariser.py` (in the same `snippets/python/` directory) does
the grunt work of turning a unified diff into structured data.

```python
from diff_summariser import summarise_text, parse_diff

doc = summarise_text(my_diff)
# {
#   "totals": {"files_changed": 3, "added_lines": 47, "removed_lines": 12},
#   "files": [{"path": "src/api.py", "kind": "modified", ...}],
#   "risks": ["binary file added: assets/logo.png"]
# }
```

`parse_diff` returns a typed structure you can iterate:

```python
diff = parse_diff(my_diff)
for file in diff.files:
    for hunk in file.hunks:
        for line in hunk.added:
            print(file.path, line)
```

---

## Offline / CI mode

Before making any API calls, the agent runs a set of fast regex
rules against added lines.  This is the offline reviewer and it
runs in milliseconds — useful in pre-commit hooks or smoke tests.

The rules currently cover:

- **hardcoded-secret** — catches API keys, tokens, passwords in
  assignment context. Severity: blocker.
- **debug-print** — `print(`, `console.log(`, `dump(` on their
  own line. Severity: minor.
- **bare-except** — `except:` with no exception type. Severity: major.
- **hardcoded-host** — localhost/127.0.0.1 in source. Severity: minor.
- **todo-marker** — TODO / FIXME / XXX left in diff. Severity: nit.

Adding a new rule is one function:

```python
MY_RULE_RX = re.compile(r"eval\(")

def _scan_added_line(file_path, line_no, content):
    ...
    if MY_RULE_RX.search(content):
        issues.append(Issue(
            severity="major",
            file=file_path,
            line=line_no,
            rule="eval-call",
            message="eval() is a code injection risk.",
        ))
    return issues
```

---

## The Claude agent loop

When `ANTHROPIC_API_KEY` is set and `--offline` is not passed, the
agent hands off to Claude.

```python
client = Anthropic()
messages = [{"role": "user", "content": "Review this pull request."}]

for _ in range(8):
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages,
    )
    if resp.stop_reason == "end_turn":
        return json.loads(...)   # final review JSON

    messages.append({"role": "assistant", "content": resp.content})
    # resolve tool calls, append results, loop
```

The loop runs at most eight rounds. In practice Claude calls
`get_diff_summary` once, calls `inspect_added_lines` for one or two
suspicious files, then writes the review and sets `stop_reason =
end_turn`. Total API usage on a typical 200-line diff is around
1,500–2,000 output tokens.

### The system prompt

The system prompt is short and directive:

```
You are a senior code reviewer. Use the tools to inspect the diff,
then return a JSON object with keys: summary, verdict
(approve|request_changes|comment), and issues (list of objects
with severity, file, line, rule, message). Be specific and concise.
Do not invent file paths.
```

Three things matter here:

1. **Output format is specified explicitly.** The model is told
   to return JSON, not prose.  This makes the output directly
   machine-readable without a second parsing step.
2. **"Do not invent file paths"** prevents hallucinated references
   to files that are not in the diff.
3. **The model is told to use the tools.** Without this, some
   models will answer from their priors rather than calling
   `inspect_added_lines`.

---

## Running it

Install dependencies:

```bash
pip install anthropic
```

Self-test (no API key needed):

```bash
python snippets/python/code_review_agent.py --self-test
# ok: code_review_agent self-test passed
```

Review a diff file in offline mode:

```bash
python snippets/python/code_review_agent.py --offline --diff my.patch
```

Review the staged changes in your repo:

```bash
git diff HEAD | python snippets/python/code_review_agent.py
```

Get JSON output for piping into CI:

```bash
git diff main...HEAD \
  | python snippets/python/code_review_agent.py --json \
  | jq '.verdict'
```

---

## Wiring into a GitHub Action

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install anthropic

      - name: Run code-review agent
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          git diff origin/${{ github.base_ref }}...HEAD \
            | python snippets/python/code_review_agent.py --json \
            > review.json
          cat review.json

      - name: Fail on blockers
        run: |
          python -c "
          import json, sys
          r = json.load(open('review.json'))
          blockers = [i for i in r.get('issues',[]) if i['severity']=='blocker']
          if blockers:
              print(f'{len(blockers)} blocker(s) found:')
              for b in blockers:
                  print(f'  {b[\"file\"]}: {b[\"message\"]}')
              sys.exit(1)
          "
```

The action fails the PR if the agent finds any blocker-severity
issue (hardcoded secret, known critical pattern). All other issues
are logged but do not block merging.

---

## Extending to more languages

The offline rules are currently written for Python but they catch
patterns that appear in any language (secrets, localhost, TODO). To
add TypeScript-specific rules:

```python
TS_TYPE_ASSERTION_RX = re.compile(r"\bas <any>\b")

def _scan_added_line(file_path, line_no, content):
    ...
    if file_path.endswith((".ts", ".tsx")) and TS_TYPE_ASSERTION_RX.search(content):
        issues.append(Issue(
            severity="minor",
            file=file_path,
            line=line_no,
            rule="ts-as-any",
            message="`as any` bypasses type safety. Use a proper type or unknown.",
        ))
```

For the Claude mode, TypeScript awareness is implicit — the model
already knows TypeScript patterns. You can nudge it in the system
prompt: _"pay special attention to React hook rules and TypeScript
type-safety anti-patterns."_

---

## Cost profile

| Diff size | Mode    | Tokens in / out | Approx cost |
|-----------|---------|-----------------|-------------|
| 50 lines  | Claude  | ~800 / ~600     | ~$0.002     |
| 200 lines | Claude  | ~1,500 / ~1,200 | ~$0.005     |
| 1 k lines | Claude  | ~4,000 / ~2,000 | ~$0.015     |

These are estimates using `claude-sonnet-4-6` pricing. For very
large diffs (feature branches, initial commits) use `--offline`
first to filter the diff to high-risk files, then send only those
files to Claude.

---

## What to build next

This agent produces a JSON review. Obvious next steps:

- **Post as a GitHub PR comment** using the GitHub API and a bot
  account.
- **Track review history** in SQLite to measure whether the same
  issues recur.
- **Add a `fix` tool** that lets the agent propose a corrected
  version of a flagged line.
- **Extend to multi-file context** by adding a tool that reads the
  full file content around a diff hunk.

---

## Related content

- [`snippets/python/code_review_agent.py`](../snippets/python/code_review_agent.py) — the runnable code
- [`snippets/python/diff_summariser.py`](../snippets/python/diff_summariser.py) — the diff parser used internally
- [`tutorials/2026-05-claude-agent-sdk-quickstart.md`](2026-05-claude-agent-sdk-quickstart.md) — the agent loop pattern in detail
- [`articles/2026-06-indirect-prompt-injection-rag.md`](../articles/2026-06-indirect-prompt-injection-rag.md) — why you should validate tool outputs before trusting them

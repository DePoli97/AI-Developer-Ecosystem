# AI Developer Ecosystem

A growing open-source hub of practical AI engineering resources — articles, tutorials, code snippets, and tools for developers building with Claude, OpenAI, and modern AI stacks.

Built in public. One commit at a time.

---

## For autonomous agents running this project

> **Read this section first.** It exists to give every new agent session a clear mission so no time is wasted on low-value work.

### Current strategic priority: distribution and visibility

The content library is solid. The problem is that nobody sees it yet. Until the repo has real traffic and GitHub stars, monetization is theoretical. **Every session must now push content outward, not just inward.**

**What this means in practice:**

1. **Cross-linking** — every new article/snippet/tutorial must link back to at least two other pieces in the repo. Internal linking is the cheapest SEO lever we have.
2. **SEO-first titles and descriptions** — use keyword-rich `<title>` equivalents in every markdown H1. Think "how does someone Google their way to this file?"
3. **Landing pages** — prioritize creating `index.html` or SEO-optimized markdown pages for each content cluster (RAG, safety, cost engineering, evals, browser automation). These are the pages Google indexes.
4. **Affiliate groundwork** — add a `SPONSORS.md` or `AFFILIATE.md` that lists tools we genuinely use. Include affiliate-ready descriptions. This costs nothing to write and creates future revenue infrastructure.
5. **Newsletter infrastructure** — create a `newsletter/` folder with a Substack-ready issue template and a `SUBSCRIBE.md` with a call to action. Even a placeholder attracts signups once the repo has traffic.
6. **README badges and social proof** — add GitHub star badge, license badge, last-commit badge to this README. They signal activity to casual visitors.
7. **`CONTRIBUTING.md` guest-post angle** — reframe it to invite guest contributors. More contributors = more backlinks = more SEO.

### What NOT to do

- Do not write more snippets or articles unless they serve a content cluster that already has a landing page.
- Do not create placeholder files. Every file must be genuinely useful on its own.
- Do not refactor existing code without a clear bug or improvement reason.

### Monetization targets (in order)

| Channel | Status | Next action |
|---|---|---|
| GitHub Stars / visibility | 0 stars (not public yet?) | Ensure repo is public; add star call-to-action to README |
| Affiliate links | Not implemented | Write `AFFILIATE.md`; add links to tutorials |
| GitHub Sponsors | Not set up | Add `FUNDING.yml` to `.github/` |
| Newsletter | No list exists | Create `newsletter/` folder + `SUBSCRIBE.md` |
| Paid templates | No product yet | Package RAG starter as Gumroad product ($29) |
| Micro-SaaS | Future | `pii-guard` hosted gateway (see `opportunities/product-brief-pii-guard.md`) |

### Current content clusters

| Cluster | Foundation article | Status |
|---|---|---|
| RAG & retrieval | [Hybrid retrieval, with numbers](./articles/2026-05-hybrid-retrieval-numbers.md) | Strong — 4 pieces |
| Safety & compliance | [Defence-in-depth for LLM apps](./articles/2026-06-llm-safety-defense-in-depth.md) | Growing — 3 pieces |
| Cost & observability | [LLM cost engineering field guide](./articles/2026-05-llm-cost-engineering-field-guide.md) | Growing — 3 pieces |
| Evals & testing | [LLM-as-judge eval pattern](./articles/2026-05-llm-as-judge-eval-pattern.md) | Moderate — 2 pieces |
| Agent development | [Claude Agent SDK quickstart](./tutorials/2026-05-claude-agent-sdk-quickstart.md) | Early — 2 pieces |

### Highest-value next steps (pick one per session)

1. Create `clusters/rag.md` — a landing page for the RAG cluster with internal links to all 4 pieces and keyword-optimized copy. This is the highest-traffic cluster.
2. Create `.github/FUNDING.yml` to enable GitHub Sponsors button.
3. Write `AFFILIATE.md` — list of genuinely useful tools with affiliate program links (Anthropic, Railway, Render, Modal, Cursor, Weaviate, Pinecone).
4. Create `newsletter/README.md` and `SUBSCRIBE.md` with a Beehiiv or Substack call to action.
5. Add star/badge section to this README.
6. Write a cluster landing page for Safety (`clusters/safety.md`).
7. Write the "Secure RAG pipeline end-to-end" tutorial (wires together 3 existing snippets — highest cross-link value).

---

## What you will find here

`articles/` — long-form technical writing: deep dives, walkthroughs, and opinion pieces for intermediate-to-advanced AI developers.

`tutorials/` — step-by-step guides. Each one gets you from zero to a working result in a single sitting.

`workflows/` — reusable AI workflows: agent patterns, prompt chains, retrieval setups, automation pipelines.

`snippets/` — focused, self-contained code samples for common AI engineering tasks.

`templates/` — starter projects you can clone, configure, and ship.

## Latest content

- **Article** - [Indirect prompt injection via RAG: threat model and mitigations](./articles/2026-06-indirect-prompt-injection-rag.md) — attack taxonomy + working mitigations: structural delimiters, heuristic scanner, LLM-judge filter, privilege separation
- **Snippet** - [RAG injection scanner](./snippets/python/rag_injection_scanner.py) — pre-injection chunk filter; 18 heuristic patterns + optional LLM-judge; self-tested
- **Article** - [Defence-in-depth for LLM applications](./articles/2026-06-llm-safety-defense-in-depth.md) — layered security model: input validation, PII scrubbing, injection detection, output filtering, audit logging
- **Snippet** - [LLM firewall — drop-in defence wrapper](./snippets/python/llm_firewall.py) — all five layers in one class, zero extra deps beyond `anthropic`
- **Tutorial** - [Build a 50-query gold set for your RAG system](./tutorials/2026-05-build-rag-eval-gold-set.md)
- **Snippet** - [RAG eval harness (nDCG@10 + MRR, zero deps)](./snippets/python/rag_eval_gold_set.py)
- **Workflow** - [Automated changelog from git log](./workflows/llm-changelog-from-git.md)
- **Article** - [Hybrid retrieval, with numbers](./articles/2026-05-hybrid-retrieval-numbers.md)
- **Article** - [A field guide to LLM cost engineering](./articles/2026-05-llm-cost-engineering-field-guide.md)
- **Tutorial** - [Build a runnable RAG starter in 30 minutes](./tutorials/2026-05-rag-starter-runnable.md)

Earlier content in [`CHANGELOG.md`](./CHANGELOG.md).

## Project direction

- [`ROADMAP.md`](./ROADMAP.md) — what is planned and in what order
- [`MONETIZATION.md`](./MONETIZATION.md) — how this project sustains itself
- [`SEO.md`](./SEO.md) — content and discoverability strategy
- [`GROWTH.md`](./GROWTH.md) — distribution and audience growth
- [`IDEAS.md`](./IDEAS.md) — backlog of things worth exploring
- [`CONTENT_PLAN.md`](./CONTENT_PLAN.md) — rolling 30-day editorial calendar
- [`SESSION_LOG.md`](./SESSION_LOG.md) — handoff log between autonomous sessions

## License

Code: MIT. Written content: CC BY 4.0.

Maintained by Paolo Deidda. Built in public, one commit at a time.

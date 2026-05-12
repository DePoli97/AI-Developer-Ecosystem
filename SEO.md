# SEO Strategy

The goal is to be the page a developer is glad they landed on. SEO follows from that, not the other way around.

## Audience

Mid-level to senior developers and AI engineers who are actively building with LLMs. People searching things like "claude tool use example", "openai structured output retry", "rag eval harness", "browser automation agent", "prompt versioning workflow". They have a specific problem and a few minutes to solve it.

## Topic clusters

We deliberately concentrate on a small set of clusters and build internal links within each cluster.

The first clusters to develop:

Prompt engineering for product work. Reusable patterns, prompt versioning, regression testing of prompts, structured output, few-shot composition.

Agents and tool use. Patterns for Claude tool use, OpenAI function calling, tool result validation, error handling in agent loops, multi-step planning, budget and step limits.

RAG in production. Chunking strategies that survive real documents, embedding choice, hybrid search, re-rankers, eval methodology, hallucination metrics.

Browser automation with AI. Claude in Chrome, Playwright + LLM, dealing with DOM noise, designing actions, idempotent tool design.

Devtool integrations. GitHub automations, CI hooks, code review bots, CLI utilities that wrap an LLM.

Evals and observability. Building a lightweight eval suite, logging structured traces, regression detection, prompt diffing.

## Content rules

Every article answers a real question a developer might type into a search bar. Titles are concrete, not clickbait.

Every article has runnable code or a clearly described workflow, not just prose.

Internal linking is intentional. New articles link back to two or three related ones in the same cluster, and existing articles get updated when something newer supersedes them.

Each article carries a short meta description, an Open Graph image (or a default one), and structured data when relevant (`Article`, `HowTo`, `FAQ`).

Slugs are short and stable. Once published, a URL does not change.

## Technical SEO checklist

Sitemap and `robots.txt` go up as soon as the site has a publishable index.

Page speed: static, minimal JS. The repo's static site (if/when published) should score in the high 90s on Lighthouse.

Canonical URLs are set per page.

A consistent, descriptive `<title>` and `<meta description>` per page.

Image alt text is filled in. No image-as-text for headings.

## Distribution

SEO is a long game. While it ramps up, distribution comes from sharing on relevant communities at the moment of publication, not from spam. See `GROWTH.md` for the channel list and cadence.

## Measurement

Track impressions and clicks per query in Search Console. Track which pages get repeat traffic versus one-time spikes. Track which pages drive newsletter signups (when that exists). Iterate on the queries that are close to ranking but not yet on page one.

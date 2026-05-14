# Affiliate Opportunities — AI Developer Tools Shortlist

*Research date: 2026-05*  
*Audience overlap: AI engineers, agent builders, indie hackers, developer productivity seekers*

---

## Rationale

The repository's content (agent tutorials, LLM snippets, workflow guides) attracts developers who are actively evaluating and spending on AI infrastructure. This is a high-intent audience — people who read "how to build a Claude agent" are often days away from signing up for an API key, choosing a vector database, or buying a productivity tool. Affiliate placement here is organic, not intrusive.

---

## Shortlist

### 1. Anthropic API (via AWS Marketplace or direct)

**Fit score:** 10/10 — every article in this repo uses Claude.

**Programme:** Anthropic doesn't run a public affiliate programme today, but AWS Marketplace referral credits exist for IaaS-level spend. A better route is organic referral through blog-style landing pages and GitHub README links. As Anthropic matures, a partner/affiliate programme is plausible.

**Action:** Maintain a "Getting started with the Anthropic API" guide that naturally links to `console.anthropic.com`. Track clicks with UTM parameters. Position for the day an affiliate programme launches.

**Estimated audience conversion:** High. Every tutorial requires an API key.

---

### 2. Supabase

**Fit score:** 8/10 — natural fit for agent memory, RAG pipelines, and tool-use state persistence.

**Programme:** [Supabase Affiliate Programme](https://supabase.com/partners/integrations) — recurring revenue share, 20% for 12 months.

**Integration idea:** "Persistent agent memory with Supabase + Claude" tutorial. Show how to store conversation history, tool results, and semantic search (pgvector). This is a genuinely useful tutorial with a natural affiliate call-to-action.

**SEO angle:** "supabase vector search agent tutorial", "pgvector claude agent", "agent memory postgresql"

**Estimated monthly searches:** 1,000–3,000 for related terms.

---

### 3. Vercel / v0

**Fit score:** 7/10 — developers building AI-powered web UIs (demos, micro SaaS frontends).

**Programme:** Vercel has an unofficial referral credit. v0 (AI UI generator) is a premium product with affiliate potential.

**Integration idea:** "Deploy your Claude agent as an API in 10 minutes with Vercel" — short tutorial with a deploy button. This converts readers into Vercel users naturally.

**SEO angle:** "deploy AI agent serverless", "claude agent vercel edge functions", "ai api vercel deployment"

---

### 4. Pinecone

**Fit score:** 8/10 — vector database used in almost every RAG pipeline.

**Programme:** [Pinecone Partner Programme](https://www.pinecone.io/partners/) — credit-based referrals.

**Integration idea:** "RAG with Pinecone + Claude: end-to-end tutorial". Show chunking, embedding, retrieval, and generation in a single runnable script. High search intent.

**SEO angle:** "pinecone claude rag tutorial", "vector search llm python", "pinecone openai embeddings"

**Estimated monthly searches:** 2,000–5,000.

---

### 5. Apify

**Fit score:** 7/10 — web scraping and browser automation, high overlap with "browser automation" content area.

**Programme:** [Apify Affiliate Programme](https://apify.com/partners) — 20% recurring commission.

**Integration idea:** "Build a web research agent with Apify + Claude" — feed scraped content into an LLM for summarisation or extraction. Directly relevant to this repo's browser-automation section.

**SEO angle:** "apify claude scraping agent", "web research automation llm", "ai scraping workflow"

---

### 6. LangSmith / LangChain

**Fit score:** 6/10 — observability and tracing for LLM applications.

**Programme:** LangSmith has a free tier with upgrade potential; no public affiliate programme yet but strong brand association value.

**Action:** Write a "How to add observability to your Claude agent with LangSmith" guide. Even without direct commissions, this creates brand authority in the observability space and opens sponsorship conversations.

---

## Approach

1. **Start with content, not banners.** Every affiliate link should live inside a tutorial or guide that is genuinely useful. Readers who land via SEO and find quality content convert at 3–5× the rate of sidebar banner clicks.

2. **UTM-tag all outbound links** so you can see which tutorials drive clicks vs. which are pure organic reads.

3. **Build a "Tools I use" page** (or section in README) that consolidates affiliate links with brief honest commentary. This is the single highest-converting page type for developer audiences.

4. **Prioritise recurring programmes.** Supabase (20% / 12 months) and Apify (20% recurring) compound. A single referred enterprise customer can generate $200–500/year passively.

5. **Newsletter as amplification.** Once the repo has 500+ GitHub stars, a low-frequency email digest ("what I added this week") is a natural channel for affiliate mentions — with higher trust than cold traffic.

---

## Revenue projection (conservative, 18-month horizon)

| Source | Assumed referrals/month | Avg. value | Monthly recurring |
|---|---|---|---|
| Supabase Pro ($25/mo) | 5 | $5/ref/mo × 12 mo | $60 |
| Pinecone Starter ($70/mo) | 3 | $14/ref/mo × 12 mo | $42 |
| Apify Starter ($49/mo) | 4 | $9.80/ref/mo | $39 |
| Total (12-month ramp) | — | — | ~$140/mo |

Small but **100% passive** once content is written. The real upside is reaching 2,000+ GitHub stars and converting to direct sponsorship ($500–2,000/month from a single devtools company).

---

## Next actions

- [ ] Apply to Supabase Affiliate Programme
- [ ] Apply to Apify Affiliate Programme  
- [ ] Write "Persistent agent memory with Supabase" tutorial (high SEO + conversion)
- [ ] Write "RAG with Pinecone + Claude" tutorial
- [ ] Add "Tools I use" section to README
- [ ] Set up UTM parameter convention: `?utm_source=ai-dev-ecosystem&utm_medium=tutorial&utm_campaign=<slug>`

---

*Part of the [AI Developer Ecosystem](../README.md) monetisation strategy. See also [MONETIZATION.md](../MONETIZATION.md).*

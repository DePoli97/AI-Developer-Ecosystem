# Tools we use and recommend

This page lists the tools that appear in the code and tutorials across this repository. Where an affiliate program exists, the link is an affiliate link — meaning we earn a small commission if you sign up, at no cost to you. We only list tools we actually use.

---

## AI APIs

**[Anthropic Claude](https://www.anthropic.com)** — the primary API used in every snippet and tutorial in this repo. Claude Sonnet is the default; Haiku for classification tasks; Opus for complex reasoning. [API docs](https://docs.anthropic.com).

**[OpenAI](https://platform.openai.com)** — used in cost comparison examples. The `token_cost_estimator.py` snippet supports GPT-4o and GPT-4o-mini pricing out of the box.

---

## Infrastructure and hosting

**[Railway](https://railway.app)** — the simplest way to deploy a Python API or a small SaaS. Free tier covers experimentation; paid tier is competitive for small production workloads. Used as the default deployment target in the micro-SaaS examples.

**[Render](https://render.com)** — alternative to Railway. Slightly more configuration, good for persistent background workers. Free tier has cold starts.

**[Modal](https://modal.com)** — serverless GPU and CPU compute, billed per second. Excellent for running embedding models or heavier inference without managing infra. The RAG starter tutorial works well deployed on Modal.

---

## Vector databases and search

**[Weaviate](https://weaviate.io)** — open-source vector database with a managed cloud tier. Used in the RAG workflow examples as the production-grade alternative to SQLite FTS5.

**[Pinecone](https://www.pinecone.io)** — managed vector database, easiest to get started with if you want zero infra. Generous free tier for prototyping.

**[Turbopuffer](https://turbopuffer.com)** — newer, very fast vector store. Worth watching if you need low-latency retrieval at scale.

---

## Developer tools

**[Cursor](https://cursor.sh)** — AI-native code editor. Most of the code in this repo was written or refined in Cursor. The agent integration is the best currently available.

**[Warp](https://www.warp.dev)** — modern terminal with AI features. Useful for debugging the shell-heavy parts of the automation scripts.

---

## Books and learning

**[Designing Machine Learning Systems](https://www.oreilly.com/library/view/designing-machine-learning/9781098107956/)** (Chip Huyen, O'Reilly) — the best practical guide to production ML, including data pipelines, monitoring, and deployment. Relevant background for the observability and evals content in this repo.

**[Building LLMs for Production](https://www.packtpub.com/en-us/product/building-llms-for-production-9781836200079)** — covers prompt engineering, fine-tuning, and deployment patterns. Good companion to the cost engineering and evals articles.

---

## Disclosure

Affiliate links are marked where present. We do not accept payment to include tools on this page. If a tool is here, it is because it appeared organically in the repository's code or tutorials.

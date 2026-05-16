# Growth Strategy

This document captures how the project gets in front of the right people. The throughline: do the work, then tell the right communities once, well.

## Audience to reach

Working developers and AI engineers. Indie hackers and small founders building AI products. Tech leads evaluating tools for their teams. The shared trait: they have shipped something with an LLM and have an opinion about it.

## Channels, ranked by long-term value

### Organic search

Highest-leverage channel over a 12-month horizon. Requires patience and steady output. See `SEO.md`.

### Hacker News

A single front-page hit can deliver thousands of qualified readers. Posts succeed when the title is specific and honest, the post is technically deep, and there is something concrete to react to (code, benchmark, opinion). Submit at most once per piece; do not "Show HN" everything.

### Reddit

r/MachineLearning, r/LocalLLaMA, r/LLMDevs, r/ChatGPTPro, r/ClaudeAI, r/SideProject, r/Indiehackers, r/programming. Read each subreddit's rules. Lead with the value, link at the bottom, respond to comments.

### dev.to and Hashnode

Cross-post evergreen pieces with a canonical link back to the repo. Good for tail SEO and for developers who follow the platform.

### Lobsters

Smaller than HN, but higher signal. Best for clearly technical, non-promotional pieces.

### Twitter/X and LinkedIn

Lower SEO value, useful for staying visible to peers and existing followers. One-shot threads tied to a publication, not a constant stream.

### YouTube / short-form video

Optional. Only worth it if a piece would clearly be better explained as a video (live coding, side-by-side comparisons). The text version always exists first.

### Newsletter (own channel)

The most valuable channel once it exists, because it is owned, not rented. See `MONETIZATION.md` Tier 2 and `ROADMAP.md` Phase 4.

## Cadence

Quality over volume. Publish when there is something worth publishing. A realistic baseline is one substantive piece every 1-2 weeks, plus smaller updates (snippets, workflow additions, doc improvements) in between.

## Release routine for a new article

Write and revise. Edit for clarity, cut anything that is not earning its keep. Add internal links to related pieces. Run the code samples once more. Publish. Post to Hacker News at a sensible time for the target timezone. Post to the most relevant subreddits with a different opening sentence for each, addressing that community's interests. Cross-post to dev.to with a canonical link. Mention it in the next newsletter issue.

## What we will not do

No engagement farming. No follow-for-follow. No reposting other people's work without credit. No buying followers or signups. No mass-mailing strangers.

## Measurement

For each release: traffic on day 1, week 1, month 1, month 6. Which channel referred them. How many became repeat readers (sessions over time). How many converted to whatever the call-to-action was for that piece (newsletter signup, GitHub star, repo clone).

## Distribution moments queued (2026-05-16)

Two pieces in the new content set are good HN candidates: the AI devtools
trends article (broad appeal, opinionated, includes negative calls which
generate strong discussion) and the agent frameworks landscape research
note (the comparison format performs well on HN and Lobsters).

The Claude Agent SDK quickstart and the RAG starter workflow are better
fits for r/ClaudeAI, r/LLMDevs, and r/LocalLLaMA, where readers are
looking for runnable code. Cross-post to dev.to with canonical links.

The snippets (rate limiter, minimal eval harness, streaming logger) work
as standalone Twitter/X threads tied to the relevant article. One thread
per snippet, scheduled across the next two weeks.

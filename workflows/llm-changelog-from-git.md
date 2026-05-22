# Automated changelog generator, from git log to release notes

A small workflow that turns a range of git commits into a Markdown
release note, without an LLM in the hot path. The shape is deliberately
boring: parse `git log`, bucket commits by conventional-commit type,
emit one section per bucket. An optional LLM polish pass can rewrite
the bullets later, but the workflow only requires the polish step when
the team actually wants prose. Out of the box, the determinism keeps
CI green and avoids paying for tokens on every release.

The runnable companion to this document is
[`snippets/python/llm_changelog_from_git.py`](../snippets/python/llm_changelog_from_git.py).
It has no third-party dependencies and ships with a passing offline
self-test.

## When this is the right shape

The setup below is the correct one when commit messages already follow
the [Conventional Commits](https://www.conventionalcommits.org/) format
(or a near-cousin like `seo:`, `content:`, `automation:`), when releases
happen often enough that hand-writing notes is painful, and when the team
values reviewability over flowery prose. It is the wrong shape when commit
messages are free-form English with no prefix discipline; in that case
either fix the discipline first, or skip directly to the LLM polish pass
described at the end.

## The two pieces

There are exactly two moving parts.

The first piece is a parser. It accepts the output of
`git log --pretty=format:'%H %s'` (one commit per line, SHA + subject)
and yields `Commit` records. Each record carries the SHA, the
conventional type (`feat`, `fix`, `docs`, ...), an optional scope, a
breaking-change flag (the `!` after the type), and the subject text.
Lines that do not match the conventional pattern are bucketed under
`other` and still surface in the output. Nothing is dropped silently.

The second piece is a renderer. It groups commits by type, orders the
sections in a stable, opinionated order (Added, then Content, then SEO,
then Research, then Automation, then Fixed, and so on), and emits
Markdown. Breaking changes are surfaced first under their own heading so
they never get buried below an "Added" list.

That is the entire workflow. There is no AST, no graph, no LLM call,
no template engine. The whole thing is around 150 lines of Python and
runs in milliseconds.

## End-to-end usage

The minimal flow, for a release that goes from tag `v1.0` to the
current `HEAD`:

    git log --pretty=format:'%H %s' v1.0..HEAD \
        | python snippets/python/llm_changelog_from_git.py --version v1.1

That prints a Markdown section ready to paste at the top of
`CHANGELOG.md` or into the body of a GitHub Release. The same snippet
can also drive the `git log` call itself:

    python snippets/python/llm_changelog_from_git.py \
        --from v1.0 --to HEAD --version v1.1

The `--from`/`--to` form is useful in a release script; the stdin form
is useful in a one-off shell pipe.

## Output shape

For a commit set like:

    abc1234 feat(api): add streaming endpoint
    def5678 fix: handle empty responses
    0011223 docs: update README
    ccddeef feat(agents)!: new agent loop, breaks tool schema
    1234567 seo: improve internal linking

the renderer emits:

    ## v1.1 - 2026-05-22

    ### Breaking changes

    - new agent loop, breaks tool schema *(agents)* (ccddeef)

    ### Added

    - add streaming endpoint *(api)* (abc1234)
    - new agent loop, breaks tool schema *(agents)* (ccddeef)

    ### SEO

    - improve internal linking (1234567)

    ### Fixed

    - handle empty responses (def5678)

    ### Documentation

    - update README (0011223)

Breaking changes appear twice, once in their own section and once in
the type-grouped section, on purpose: skim-readers see the warning at
the top, and the change still appears in its functional bucket below.

## Wiring into a release script

The script returns exit code 0 on success and writes to stdout, which
makes shell composition trivial. The release script we use is roughly:

    #!/usr/bin/env bash
    set -euo pipefail

    LAST_TAG=$(git describe --tags --abbrev=0)
    NEW_TAG="$1"

    NOTES=$(python snippets/python/llm_changelog_from_git.py \
        --from "$LAST_TAG" --to HEAD --version "$NEW_TAG")

    # Prepend to CHANGELOG.md, keeping the existing content below.
    {
        head -n 6 CHANGELOG.md      # title + preamble
        echo "$NOTES"
        tail -n +7 CHANGELOG.md
    } > CHANGELOG.md.new
    mv CHANGELOG.md.new CHANGELOG.md

    git add CHANGELOG.md
    git commit -m "docs: changelog for $NEW_TAG"
    git tag -a "$NEW_TAG" -m "$NOTES"
    git push origin main --tags

The whole release is one command, the notes are deterministic, and the
tag annotation carries the same Markdown body that landed in the
changelog.

## CI: enforce conventional commits

The workflow above only pays off if commit messages actually follow
the convention. A two-line CI check rejects PRs whose commit subjects
do not match the regex:

    grep -E '^(feat|fix|docs|refactor|perf|test|chore|content|seo|build|ci|automation|research)(\([^)]+\))?!?: ' \
        <(git log --pretty=format:'%s' origin/main..HEAD) \
        > /dev/null || { echo "Non-conventional commit subject found"; exit 1; }

That is enough to keep the discipline. We deliberately do not gate
merges on a heavier tool (commitlint, gitlint, husky) because the
single grep above is reviewable in one screen and never fails for
mysterious reasons.

## Optional: LLM polish pass

When the human-readable quality of the notes matters more than the
review effort, route the rendered Markdown through a single LLM call
that rewrites bullets into customer-facing prose. The pattern we like:

1. Render the deterministic Markdown first (the workflow above).
2. Pass it to Claude with a one-shot prompt that says "rewrite each
   bullet under 20 words, keep the section headings, keep the
   parenthesised SHA references, do not invent features."
3. Diff the LLM output against the deterministic input. If any
   section heading or SHA disappeared, reject the rewrite and fall
   back to the deterministic version.

The diff-and-fall-back step is the entire reason to keep the
deterministic renderer at all. Without it, the LLM is the only source
of truth and hallucinated features will eventually ship inside a
release note.

## What this workflow deliberately avoids

There is no commit-body parsing. We deliberately use only the subject
line so the workflow stays robust to multi-line commit bodies that
sometimes contain co-author trailers, issue references, or pasted
stack traces. Anything you want in the changelog goes in the commit
subject; anything you want out of the changelog goes in the body.

There is no GitHub API call. The workflow does not need to know about
pull request titles, labels, or reviewers. Squash-and-merge with a
conventional commit subject is the contract; the workflow's job is to
read that contract back out at release time.

There is no per-author attribution. Changelogs are about what shipped,
not who shipped it. Author credit lives in `git log` and the GitHub
contributors page; mixing it into release notes encourages the wrong
incentives (volume over impact).

## Related material

The companion snippet,
[`snippets/python/llm_changelog_from_git.py`](../snippets/python/llm_changelog_from_git.py),
is the authoritative implementation and ships with offline self-tests.
The CI workflow recipes in [`docs/ci-workflows.md`](../docs/ci-workflows.md)
include a ready-to-paste GitHub Actions job for the conventional-commit
check above.

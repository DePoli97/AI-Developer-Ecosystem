# Claude API starter template

A small, opinionated Python project skeleton for building applications on
top of the Anthropic Claude API. Copy this directory into a new project and
you have a working baseline: environment loading, a typed client wrapper,
streaming support, retry with backoff, structured logging, and a simple
CLI to try it.

## What is in the box

The template is intentionally minimal. Adding files is your job; what is
here exists because every project needs it on day one.

    .
    ├── README.md                  - this file
    ├── pyproject.toml             - dependencies and tooling config
    ├── .env.example               - environment variables to set
    ├── src/
    │   ├── __init__.py
    │   ├── config.py              - typed env loading
    │   ├── client.py              - Anthropic client with retry and logging
    │   ├── prompts/
    │   │   └── system.txt         - the default system prompt
    │   └── cli.py                 - command-line entry point
    └── tests/
        └── test_smoke.py          - one offline smoke test


## Quick start

    cp .env.example .env
    # edit .env to set ANTHROPIC_API_KEY
    pip install -e .
    python -m src.cli "Explain quantum tunneling in two sentences."

## What this template does not include

It does not include a web framework, a database, a queue, or a deploy
configuration. The reason is that those choices vary widely from project
to project, and adding them defensively makes the template worse.

When you need any of those, add them deliberately. The retry wrapper, the
config loader, and the streaming helper will keep working unchanged.

## When to use this

This template is the right starting point for: a CLI tool that talks to
Claude, a small internal automation, the prototype phase of a larger
product, or the LLM module inside an existing Python service.

It is not the right starting point for: a multi-agent system (use the
Claude Agent SDK quickstart instead), a heavy data pipeline (use Prefect
or Airflow), or anything in a non-Python ecosystem.

## Related

- [Claude Agent SDK quickstart](../../tutorials/2026-05-claude-agent-sdk-quickstart.md)
- [Token cost estimator snippet](../../snippets/python/token_cost_estimator.py)
- [Rate-limit aware client](../../snippets/python/rate_limit_aware_client.py)

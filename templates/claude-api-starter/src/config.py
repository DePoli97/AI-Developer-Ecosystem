"""Typed environment loading. One place to read settings, one place to fail loudly."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    max_tokens: int
    log_dir: Path


def load_config() -> Config:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return Config(
        api_key=api_key,
        model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6").strip(),
        max_tokens=int(os.environ.get("CLAUDE_MAX_TOKENS", "2048")),
        log_dir=Path(os.environ.get("LOG_DIR", "./.logs")).resolve(),
    )

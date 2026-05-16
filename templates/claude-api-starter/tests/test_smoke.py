"""
Offline smoke test - imports work and config loads with a placeholder key.
Does not call the API. Run with: pytest -q
"""

from __future__ import annotations

import os


def test_imports():
    from src import client, config
    assert hasattr(client, "ClaudeClient")
    assert hasattr(config, "load_config")


def test_config_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from src.config import load_config
    try:
        load_config()
    except RuntimeError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError when ANTHROPIC_API_KEY is missing")


def test_config_loads_with_key(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    from src.config import load_config
    cfg = load_config()
    assert cfg.api_key == "sk-ant-fake"
    assert cfg.model.startswith("claude-")
    assert cfg.max_tokens > 0

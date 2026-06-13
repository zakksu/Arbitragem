"""Shared pytest fixtures — fast, isolated test environment."""

from __future__ import annotations

import os

# Must run before Settings is first loaded.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("PROFIT_BRIDGE_ENABLED", "false")
os.environ.setdefault("PROFIT_BRIDGE_AUTO_DETECT", "false")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("SCANNER_INCLUDE_BOVA_OPTIONS", "false")
os.environ.setdefault("OLLAMA_ENABLED", "false")
os.environ.setdefault("SCANNER_OLLAMA_ON_SCAN", "false")
os.environ.setdefault("JOURNAL_AUTO_ANALYZE", "false")

import pytest

from src.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

"""Fixtures for autonomous engine + rankings tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import get_session_factory, init_db


@pytest.fixture
def db_session():
    init_db()
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")
    get_settings.cache_clear()
    init_db()
    return TestClient(create_app())

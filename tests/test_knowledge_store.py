"""Knowledge store + 10.0 API smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.knowledge.store import ingest_text, knowledge_status, search_chunks


@pytest.fixture
def client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("KNOWLEDGE_ENABLED", "true")
    db = tmp_path / "knowledge.db"
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(db))
    init_db()
    return TestClient(create_app())


def test_knowledge_ingest_and_search(monkeypatch, tmp_path):
    get_settings.cache_clear()
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    db = tmp_path / "k.db"
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(db))

    result = ingest_text(
        source_uri="test://structures",
        title="Structures",
        text="VWAP reclaim on PETR4 auction failure is a high probability scalp setup. " * 20,
        tags=["vwap", "scalp"],
        symbols=["PETR4"],
    )
    assert result["ok"] is True
    assert result["chunks"] >= 1

    hits = search_chunks("VWAP reclaim", symbol="PETR4", limit=5)
    assert len(hits) >= 1
    assert "VWAP" in hits[0]["excerpt"]

    status = knowledge_status()
    assert status["chunks"] >= 1


def test_knowledge_api(client):
    r = client.get("/api/v1/knowledge/status")
    assert r.status_code == 200
    assert "chunks" in r.json()


def test_daily_briefing_api(client):
    r = client.get("/api/v1/daily-briefing")
    assert r.status_code == 200
    data = r.json()
    assert "bullets" in data
    assert len(data["bullets"]) >= 1


def test_knowledge_library_partial(client):
    r = client.get("/board/partials/knowledge-library")
    assert r.status_code == 200
    assert "Knowledge library" in r.text


def test_daily_briefing_partial(client):
    r = client.get("/board/partials/daily-briefing")
    assert r.status_code == 200
    assert "Daily briefing" in r.text


def test_bootstrap_corpus_if_empty(monkeypatch, tmp_path):
    from src.config import get_settings
    from src.services.knowledge.bootstrap import bootstrap_corpus_if_empty

    get_settings.cache_clear()
    monkeypatch.setenv("GOLDEN_PATH_MODE", "true")
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(tmp_path / "boot.db"))

    out = bootstrap_corpus_if_empty()
    assert out.get("skipped") is not True or out.get("reason") != "knowledge_disabled"
    if out.get("ingested", 0) > 0:
        assert out["chunks"] >= 1
        again = bootstrap_corpus_if_empty()
        assert again.get("reason") == "corpus_exists"

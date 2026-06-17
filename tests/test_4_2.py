"""4.2 — crypto watchlist (Binance) + trade archaeology import."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from src import __version__
from src.config import get_settings
from src.main import create_app
from src.models import init_db
from src.services.crypto_quotes import get_crypto_quotes
from src.services.crypto_universe import load_crypto_universe, symbol_list


def test_version_is_4_2_alpha():
    assert __version__ == "12.0.0"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / '42.db'}")
    monkeypatch.setenv("ARCHAEOLOGY_IMPORT_DIR", str(tmp_path / "archaeology"))
    get_settings.cache_clear()
    monkeypatch.setenv("PROFIT_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("FUTURES_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("CRYPTO_WATCHLIST_ENABLED", "true")
    monkeypatch.setenv("BINANCE_QUOTES_ENABLED", "false")
    monkeypatch.setenv("CRYPTO_PAPER_ENABLED", "true")
    monkeypatch.setenv("PAPER_TRADING_MODE", "true")
    monkeypatch.setenv("BOARD_AUTH_ENABLED", "false")
    init_db()
    return TestClient(create_app())


def test_crypto_universe():
    syms = symbol_list()
    assert syms == ["BTC", "ETH", "SOL"]
    assert len(load_crypto_universe()) == 3


def test_crypto_stub_quotes():
    quotes = get_crypto_quotes()
    assert quotes["BTC"].last > 10_000
    assert quotes["ETH"].last > 100
    assert quotes["SOL"].last > 10


def test_watchlist_includes_crypto(client):
    r = client.get("/api/v1/watchlist/enriched")
    assert r.status_code == 200
    data = r.json()
    assert data["crypto_count"] == 3
    symbols = {row["symbol"] for row in data["symbols"]}
    assert {"BTC", "ETH", "SOL"}.issubset(symbols)
    btc = next(x for x in data["crypto"] if x["symbol"] == "BTC")
    assert btc["asset_class"] == "crypto"
    assert btc["read_only"] is True
    assert btc["auto_trade"] is False
    assert btc["quote_source"] in ("binance", "stub")


def test_universe_crypto_endpoint(client):
    r = client.get("/api/v1/universe/crypto")
    assert r.status_code == 200
    body = r.json()
    assert body["read_only"] is True
    assert body["auto_trade"] is False
    assert len(body["symbols"]) == 3
    assert body["quotes"][0]["binance_pair"].endswith("USDT")


def test_crypto_watchlist_disabled(client, monkeypatch):
    monkeypatch.setenv("CRYPTO_WATCHLIST_ENABLED", "false")
    get_settings.cache_clear()
    data = client.get("/api/v1/watchlist/enriched").json()
    assert data["crypto_count"] == 0
    assert "BTC" not in {r["symbol"] for r in data["symbols"]}


def test_archaeology_import_and_timeline(client, tmp_path):
    csv_text = (
        "Data;Ativo;Tipo;Quantidade;Preco;Resultado\n"
        "01/06/2025;PETR4;C;100;38,50;150,00\n"
        "02/06/2025;PETR4;V;100;39,00;-50,00\n"
    )
    files = {"file": ("trades.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    r = client.post("/api/v1/archaeology/import", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["imported"] == 2

    tl = client.get("/api/v1/archaeology/timeline?symbol=PETR4")
    assert tl.status_code == 200
    events = tl.json()["events"]
    assert len(events) == 2
    assert events[0]["symbol"] == "PETR4"
    assert events[0]["source"] == "archaeology"


def test_archaeology_scan_folder(client, tmp_path, monkeypatch):
    arch_dir = tmp_path / "archaeology_scan"
    arch_dir.mkdir()
    (arch_dir / "hist.csv").write_text(
        "Data;Ativo;Tipo;Quantidade;Preco;Resultado\n"
        "03/06/2025;VALE3;C;50;62,00;80,00\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARCHAEOLOGY_IMPORT_DIR", str(arch_dir))
    get_settings.cache_clear()
    r = client.post("/api/v1/archaeology/scan")
    assert r.status_code == 200
    assert r.json()["imported"] >= 1


def test_paper_crypto_preview(client):
    r = client.get("/api/v1/paper/crypto/preview", params={"symbol": "BTC", "quantity": 0.01})
    assert r.status_code == 200
    body = r.json()
    assert body["symbol"] == "BTC"
    assert body["paper_only"] is True
    assert body["expected_fill"] > 0


def test_paper_crypto_execute(client):
    r = client.post(
        "/api/v1/paper/crypto/execute",
        json={"symbol": "ETH", "side": "buy", "quantity": 0.05},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "paper_crypto"
    assert body["trade_id"]


def test_paper_crypto_blocked_when_live(client, monkeypatch):
    monkeypatch.setenv("PAPER_TRADING_MODE", "false")
    get_settings.cache_clear()
    r = client.post(
        "/api/v1/paper/crypto/execute",
        json={"symbol": "SOL", "side": "buy", "quantity": 1},
    )
    assert r.status_code == 400


def test_board_watchlist_crypto_rows(client):
    r = client.get("/board/partials/watchlist")
    assert r.status_code == 200
    html = r.text
    assert "BTC" in html
    assert "ETH" in html
    assert "SOL" in html
    assert "bb-watch-row-crypto" in html
    assert "bb-watch-section-crypto" in html
    assert "READ" in html


def test_board_archaeology_timeline(client, tmp_path):
    csv_text = (
        "Data;Ativo;Tipo;Quantidade;Preco;Resultado\n"
        "01/06/2025;PETR4;C;100;38,50;150,00\n"
    )
    files = {"file": ("trades.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")}
    client.post("/api/v1/archaeology/import", files=files)
    r = client.get("/board/partials/archaeology")
    assert r.status_code == 200
    assert "bb-archaeology" in r.text
    assert "PETR4" in r.text


def test_board_crypto_paper_partial(client):
    r = client.get("/board/partials/symbol/BTC/crypto-paper")
    assert r.status_code == 200
    assert "bb-crypto-paper" in r.text
    assert "Paper buy" in r.text

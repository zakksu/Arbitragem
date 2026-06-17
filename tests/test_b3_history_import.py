"""B3 CEI Excel import — archaeology pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import Trade, init_db
from src.services.b3_history_import import import_b3_history_excel, preview_excel_rows


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'b3imp.db'}")
    from src.config import get_settings

    get_settings.cache_clear()
    init_db()
    from src.models import get_session_factory

    session = get_session_factory()()
    yield session
    session.close()


SAMPLE_CSV = """Data do Negócio;Tipo de Movimentação;Mercado;Código de Negociação;Quantidade;Preço;Valor
13/11/2025;Venda;Mercado à Vista;PETR4;100;38.50;3850
13/11/2025;Compra;Mercado à Vista;PETR4;100;38.20;3820
"""


def test_b3_cei_csv_import(db_session, tmp_path):
    path = tmp_path / "b3.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8")
    from src.services.trade_archaeology import import_trade_csv

    result = import_trade_csv(db_session, path)
    db_session.commit()
    assert result["imported"] == 2
    rows = db_session.query(Trade).filter(Trade.source == "archaeology").all()
    assert len(rows) == 2
    assert {r.symbol for r in rows} == {"PETR4"}


def test_archaeology_summary(db_session, tmp_path):
    path = tmp_path / "b3.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8")
    from src.services.archaeology_backtest import build_archaeology_summary
    from src.services.trade_archaeology import import_trade_csv

    import_trade_csv(db_session, path)
    db_session.commit()

    body = build_archaeology_summary(db_session)
    assert body["total_trades"] >= 2
    assert any(s["symbol"] == "PETR4" for s in body["top_symbols"])
    assert body["lanes"]["cash"] >= 2


def test_preview_excel_requires_file(tmp_path):
    assert preview_excel_rows(tmp_path / "nope.xlsx").get("error") == "file_not_found"

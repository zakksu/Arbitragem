"""Strategy Store — scan ProfitChart NTSL files, extract logic, link to Strategy rows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import get_logger
from src.models import StoredStrategy, Strategy
from src.services.ntsl_parser import content_hash, extract_ntsl_features

logger = get_logger(__name__)

_PACK_VERSION_PATH = PROJECT_ROOT / "data" / ".dev" / "ntsl_pack_version.json"


def read_ntsl_pack_version() -> dict[str, Any]:
    if not _PACK_VERSION_PATH.is_file():
        return {}
    try:
        import json

        return json.loads(_PACK_VERSION_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _pack_diff(session: Session) -> dict[str, Any]:
    pack = read_ntsl_pack_version()
    if not pack:
        return {"pack_version": None, "new_since_pack": 0, "removed_since_pack": 0}
    indexed = {r.file_path for r in session.query(StoredStrategy).all()}
    pack_files = set(pack.get("files") or [])
    return {
        "pack_version": pack.get("version"),
        "pack_generated_at": pack.get("generated_at"),
        "new_since_pack": len(indexed - pack_files),
        "removed_since_pack": len(pack_files - indexed),
    }


def _strategy_name_from_path(path: Path) -> str:
    return path.stem.replace(" ", "_")[:120]


def scan_ntsl_file(session: Session, path: Path, *, source_dir: str | None = None) -> StoredStrategy:
    """Index one .ntsl file — idempotent on content hash."""
    text = path.read_text(encoding="utf-8", errors="replace")
    digest = content_hash(text)
    existing = (
        session.query(StoredStrategy)
        .filter(StoredStrategy.file_path == str(path.resolve()))
        .first()
    )
    if existing and existing.content_hash == digest:
        existing.last_scanned_at = datetime.utcnow()
        return existing

    features = extract_ntsl_features(text)
    tags = list(features.get("structure_hints") or [])
    if features.get("order_ops"):
        tags.extend(features["order_ops"])
    symbols = features.get("symbols") or []

    row = existing or StoredStrategy(
        name=_strategy_name_from_path(path),
        file_path=str(path.resolve()),
    )
    row.content_hash = digest
    row.ntsl_code = text[:50000]
    row.extracted_logic = features
    row.tags = tags[:20]
    row.symbols = symbols
    row.source_dir = source_dir or str(path.parent)
    row.last_scanned_at = datetime.utcnow()
    if not existing:
        session.add(row)
    session.flush()
    _maybe_link_strategy(session, row)
    return row


def _maybe_link_strategy(session: Session, stored: StoredStrategy) -> None:
    """Upsert matching Strategy row for WFO / replay picker."""
    strat = (
        session.query(Strategy)
        .filter(Strategy.name == stored.name)
        .first()
    )
    if not strat:
        strat = Strategy(
            name=stored.name,
            description=(stored.extracted_logic or {}).get("summary"),
            ntsl_code=stored.ntsl_code,
            status="active",
            parameters={"source": "strategy_store", "stored_id": stored.id},
        )
        session.add(strat)
        session.flush()
    else:
        strat.ntsl_code = stored.ntsl_code
        strat.description = (stored.extracted_logic or {}).get("summary")
    stored.strategy_id = strat.id


def scan_strategy_directories(session: Session, paths: list[Path] | None = None) -> dict[str, Any]:
    """Walk configured dirs for *.ntsl — keeps RAM low via generator-style loop."""
    settings = get_settings()
    if not settings.strategy_store_enabled:
        return {"scanned": 0, "indexed": 0, "skipped": True}

    dirs = paths or settings.strategy_store_scan_paths
    indexed = 0
    errors: list[str] = []
    for base in dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.glob("**/*.ntsl")):
            try:
                scan_ntsl_file(session, path, source_dir=str(base))
                indexed += 1
            except OSError as exc:
                errors.append(f"{path.name}:{exc}")
    session.commit()
    diff = _pack_diff(session)
    logger.info("strategy_store_scan", indexed=indexed, dirs=len(dirs))
    return {
        "scanned": indexed,
        "indexed": indexed,
        "dirs": [str(d) for d in dirs],
        "errors": errors,
        **diff,
    }


def list_stored_strategies(session: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        session.query(StoredStrategy)
        .order_by(StoredStrategy.last_scanned_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "symbols": r.symbols or [],
            "tags": r.tags or [],
            "summary": (r.extracted_logic or {}).get("summary"),
            "strategy_id": r.strategy_id,
            "file_path": r.file_path,
            "last_scanned_at": r.last_scanned_at.isoformat() if r.last_scanned_at else None,
        }
        for r in rows
    ]


def get_stored_strategy(session: Session, stored_id: int) -> dict[str, Any] | None:
    row = session.get(StoredStrategy, stored_id)
    if not row:
        return None
    return {
        "id": row.id,
        "name": row.name,
        "ntsl_code": row.ntsl_code,
        "extracted_logic": row.extracted_logic,
        "symbols": row.symbols,
        "tags": row.tags,
        "strategy_id": row.strategy_id,
        "file_path": row.file_path,
    }


_STRUCTURE_MATCH_TERMS: dict[str, tuple[str, ...]] = {
    "stock_scalp_vwap": ("vwap", "s1", "s1_vwap", "reclaim", "scalp"),
    "opening_range_break": ("orb", "opening", "s2", "range", "break"),
    "mean_reversion_band": ("mean", "reversion", "s3", "bb", "fade"),
    "archaeology_bias_long": ("archaeology", "s4", "bias", "history"),
    "pulse_scalp": ("pulse", "s5", "radar", "scalp"),
    "scalp_long": ("scalp", "long", "vwap", "s1"),
    "scalp_short": ("scalp", "short"),
    "scalp": ("scalp",),
}


def match_ntsl_for_structure(
    session: Session,
    structure_type: str,
    *,
    symbol: str | None = None,
) -> dict[str, Any] | None:
    """Best stored NTSL row for trade product + replay (W11.3)."""
    from src.services.structure_types import replay_strategy_for_structure

    st = (structure_type or "scalp").strip().lower()
    replay_strategy = replay_strategy_for_structure(st)
    terms = {st, st.replace("_", " "), replay_strategy}
    terms.update(_STRUCTURE_MATCH_TERMS.get(st, ()))

    rows = list_stored_strategies(session, limit=80)
    sym = symbol.strip().upper() if symbol else None
    best: dict[str, Any] | None = None
    best_score = -1
    for row in rows:
        hay = " ".join(
            [row.get("name") or "", row.get("summary") or ""]
            + [str(t) for t in (row.get("tags") or [])]
        ).lower()
        score = 0
        for term in terms:
            if term and term.lower() in hay:
                score += 2
        if sym and sym in (row.get("symbols") or []):
            score += 4
        if score > best_score:
            best_score = score
            best = row

    if best and best_score > 0:
        return {
            **best,
            "replay_strategy": replay_strategy,
            "structure_type": st,
            "match_score": best_score,
        }
    return {
        "name": replay_strategy,
        "replay_strategy": replay_strategy,
        "structure_type": st,
        "file_path": None,
        "tags": [],
        "match_score": 0,
        "summary": "No indexed NTSL — use exports/profit/ or run Strategy Store scan",
    }

"""SQLite FTS knowledge store — separate DB keeps main WAL slim (~few MB hot)."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)

_CHUNK_WORDS = 420
_OVERLAP_WORDS = 60


def knowledge_db_path() -> Path:
    settings = get_settings()
    if settings.knowledge_db_path:
        return Path(settings.knowledge_db_path)
    return PROJECT_ROOT / "data" / "knowledge.db"


def _connect() -> sqlite3.Connection:
    path = knowledge_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_knowledge_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_uri TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                chunk_text TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                symbols TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                chunk_text, source_uri, title, tokenize='unicode61'
            );
            CREATE INDEX IF NOT EXISTS idx_kc_source ON knowledge_chunks(source_uri);
            """
        )
        conn.commit()


def _chunk_text(text: str) -> list[str]:
    words = re.split(r"\s+", text.strip())
    if not words or words == [""]:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(words):
        piece = words[i : i + _CHUNK_WORDS]
        if piece:
            chunks.append(" ".join(piece))
        i += max(1, _CHUNK_WORDS - _OVERLAP_WORDS)
    return chunks


def ingest_text(
    *,
    source_uri: str,
    text: str,
    title: str = "",
    tags: list[str] | None = None,
    symbols: list[str] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Chunk + index text. Runs offline only — not for motor hot path."""
    settings = get_settings()
    if not offline and not settings.knowledge_runtime_enabled:
        return {"ok": False, "reason": "knowledge_disabled"}
    if offline and not settings.knowledge_enabled:
        return {"ok": False, "reason": "knowledge_disabled"}

    from src.services.knowledge.poison_guard import validate_ingest_text

    guard = validate_ingest_text(text, source_uri=source_uri)
    if not guard.get("ok"):
        return guard

    init_knowledge_db()
    tag_json = json.dumps(tags or [])
    sym_json = json.dumps([s.upper() for s in (symbols or [])])
    now = datetime.now(timezone.utc).isoformat()
    pieces = _chunk_text(text)
    if not pieces:
        return {"ok": False, "reason": "empty_text", "chunks": 0}

    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
        max_chunks = settings.knowledge_max_chunks
        if count + len(pieces) > max_chunks:
            return {
                "ok": False,
                "reason": "max_chunks",
                "chunks": 0,
                "current": count,
                "max": max_chunks,
            }
        old_ids = conn.execute(
            "SELECT id FROM knowledge_chunks WHERE source_uri = ?", (source_uri,)
        ).fetchall()
        for (rid,) in old_ids:
            try:
                conn.execute(
                    "INSERT INTO knowledge_fts(knowledge_fts, rowid, chunk_text, source_uri, title) "
                    "VALUES('delete', ?, '', '', '')",
                    (rid,),
                )
            except sqlite3.OperationalError:
                pass
        conn.execute("DELETE FROM knowledge_chunks WHERE source_uri = ?", (source_uri,))
        added = 0
        for piece in pieces:
            cur = conn.execute(
                """
                INSERT INTO knowledge_chunks (source_uri, title, chunk_text, tags, symbols, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_uri, title, piece, tag_json, sym_json, now),
            )
            row_id = cur.lastrowid
            conn.execute(
                "INSERT INTO knowledge_fts (rowid, chunk_text, source_uri, title) VALUES (?, ?, ?, ?)",
                (row_id, piece, source_uri, title),
            )
            added += 1
        conn.commit()
    logger.info("knowledge_ingested", source=source_uri, chunks=added)
    return {"ok": True, "source_uri": source_uri, "chunks": added}


def _read_file_text(path: Path) -> tuple[str | None, str | None]:
    """Return (text, skip_reason). skip_reason set when file is intentionally skipped."""
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt", ".ntsl", ".vtt"):
        return path.read_text(encoding="utf-8", errors="replace"), None
    if suffix == ".pdf":
        for mod_name in ("pypdf", "PyPDF2"):
            try:
                mod = __import__(mod_name)
                reader_cls = getattr(mod, "PdfReader", None)
                if reader_cls is None:
                    continue
                reader = reader_cls(str(path))
                pages = [page.extract_text() or "" for page in reader.pages]
                text = "\n".join(pages).strip()
                if text:
                    return text, None
                return None, "pdf_empty"
            except ImportError:
                return None, "pdf_library_missing"
            except Exception as exc:
                return None, f"pdf_read_error:{exc.__class__.__name__}"
        return None, "pdf_library_missing"
    return None, "unsupported_type"


def ingest_file(
    path: Path,
    *,
    tags: list[str] | None = None,
    symbols: list[str] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "reason": "not_found", "path": str(path)}
    text, skip_reason = _read_file_text(path)
    if skip_reason:
        return {"ok": False, "reason": skip_reason, "path": str(path), "skipped": True}
    if not text:
        return {"ok": False, "reason": "empty_text", "path": str(path)}
    return ingest_text(
        source_uri=str(path.resolve()),
        text=text,
        title=path.name,
        tags=tags,
        symbols=symbols,
        offline=offline,
    )


def knowledge_status() -> dict[str, Any]:
    settings = get_settings()
    if not knowledge_db_path().exists():
        return {
            "enabled": settings.knowledge_runtime_enabled,
            "chunks": 0,
            "sources": 0,
            "db_mb": 0.0,
        }
    init_knowledge_db()
    with _connect() as conn:
        chunks = conn.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
        sources = conn.execute("SELECT COUNT(DISTINCT source_uri) FROM knowledge_chunks").fetchone()[0]
    db_mb = round(knowledge_db_path().stat().st_size / (1024 * 1024), 2)
    return {
        "enabled": settings.knowledge_runtime_enabled,
        "chunks": int(chunks),
        "sources": int(sources),
        "db_mb": db_mb,
        "max_chunks": settings.knowledge_max_chunks,
    }


def search_chunks(
    query: str,
    *,
    symbol: str | None = None,
    tags: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.knowledge_runtime_enabled:
        return []
    if not query.strip():
        return []

    init_knowledge_db()
    limit = max(1, min(limit, 20))
    q = query.strip().replace('"', '""')
    fts_query = f'"{q}"' if " " in q else f"{q}*"

    with _connect() as conn:
        try:
            rows = conn.execute(
                """
                SELECT c.id, c.source_uri, c.title, c.chunk_text, c.tags, c.symbols,
                       bm25(knowledge_fts) AS rank
                FROM knowledge_fts f
                JOIN knowledge_chunks c ON c.id = f.rowid
                WHERE knowledge_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit * 3),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                """
                SELECT id, source_uri, title, chunk_text, tags, symbols, 0 AS rank
                FROM knowledge_chunks
                WHERE chunk_text LIKE ?
                LIMIT ?
                """,
                (f"%{query.strip()[:80]}%", limit * 3),
            ).fetchall()

    sym_filter = symbol.strip().upper() if symbol else None
    tag_filter = tags.strip().lower() if tags else None
    out: list[dict[str, Any]] = []
    for row in rows:
        syms = json.loads(row["symbols"] or "[]")
        tgs = json.loads(row["tags"] or "[]")
        if sym_filter and syms and sym_filter not in syms:
            continue
        if tag_filter and tag_filter not in [t.lower() for t in tgs]:
            continue
        excerpt = (row["chunk_text"] or "")[:320]
        out.append(
            {
                "id": row["id"],
                "source_uri": row["source_uri"],
                "title": row["title"],
                "excerpt": excerpt,
                "tags": tgs,
                "symbols": syms,
                "rank": float(row["rank"] or 0),
            }
        )
        if len(out) >= limit:
            break
    return out

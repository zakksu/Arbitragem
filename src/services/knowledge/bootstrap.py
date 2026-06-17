"""Bootstrap default knowledge corpus on first setup (10.0 — offline, not motor hot path)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, get_settings
from src.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_SOURCES = (
    ("docs/STRUCTURES.md", ["structure", "scalp"], ["PETR4"]),
)


def bootstrap_corpus_if_empty(*, force: bool = False) -> dict[str, Any]:
    """Ingest bundled docs when corpus is empty and knowledge is enabled."""
    settings = get_settings()
    if not settings.knowledge_enabled and not settings.golden_path_mode:
        return {"skipped": True, "reason": "knowledge_disabled"}

    from src.services.knowledge.store import ingest_file, knowledge_status

    status = knowledge_status()
    if status.get("chunks", 0) > 0 and not force:
        return {"skipped": True, "reason": "corpus_exists", "chunks": status.get("chunks")}

    ingested = 0
    chunks = 0
    errors: list[str] = []
    for rel, tags, symbols in _DEFAULT_SOURCES:
        path = PROJECT_ROOT / rel
        if not path.is_file():
            errors.append(f"missing:{rel}")
            continue
        try:
            result = ingest_file(path, tags=tags, symbols=symbols, offline=True)
            if result.get("ok"):
                ingested += 1
                chunks += int(result.get("chunks") or 0)
            else:
                errors.append(f"{rel}:{result.get('error', 'fail')}")
        except OSError as exc:
            errors.append(f"{rel}:{exc}")

    out = {
        "ingested": ingested,
        "chunks": chunks,
        "status": knowledge_status(),
        "errors": errors,
    }
    if ingested:
        logger.info("knowledge_bootstrap", **{k: v for k, v in out.items() if k != "status"})
    return out

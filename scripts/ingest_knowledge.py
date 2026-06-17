#!/usr/bin/env python3
"""Offline knowledge ingest — PDF/text/md → chunked FTS index (10.0-alpha)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into knowledge.db")
    parser.add_argument("--path", required=True, help="File or directory to ingest")
    parser.add_argument("--symbol", default="PETR4", help="Tag symbol filter")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from src.services.knowledge.store import ingest_file, ingest_text, knowledge_status

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    symbols = [args.symbol.strip().upper()] if args.symbol else []
    path = Path(args.path)
    results: list[dict] = []

    if path.is_dir():
        for fp in sorted(path.rglob("*")):
            if fp.suffix.lower() in (".md", ".txt", ".ntsl", ".vtt"):
                results.append(ingest_file(fp, tags=tags, symbols=symbols))
    else:
        results.append(ingest_file(path, tags=tags, symbols=symbols))

    ok = sum(1 for r in results if r.get("ok"))
    total_chunks = sum(int(r.get("chunks") or 0) for r in results)
    status = knowledge_status()

    if args.json:
        import json

        print(json.dumps({"ingested": ok, "files": len(results), "chunks": total_chunks, "status": status}, indent=2))
    else:
        print(f"[ingest] {ok}/{len(results)} files · {total_chunks} chunks")
        print(f"[ingest] corpus: {status['chunks']} chunks, {status['db_mb']} MB")

    return 0 if ok > 0 or total_chunks > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

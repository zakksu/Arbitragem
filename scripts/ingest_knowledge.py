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

    suffixes = (".md", ".txt", ".ntsl", ".vtt", ".pdf", ".json")
    if path.is_dir():
        for fp in sorted(path.rglob("*")):
            if fp.suffix.lower() in suffixes:
                if fp.suffix.lower() == ".json" and "insights" in fp.name.lower():
                    from src.services.knowledge.insights_ingest import ingest_b3_insights

                    results.append(ingest_b3_insights(path=str(fp), offline=True))
                else:
                    results.append(ingest_file(fp, tags=tags, symbols=symbols, offline=True))
    else:
        if path.suffix.lower() == ".json":
            from src.services.knowledge.insights_ingest import ingest_b3_insights

            results.append(ingest_b3_insights(path=str(path), offline=True))
        else:
            results.append(ingest_file(path, tags=tags, symbols=symbols, offline=True))

    ok = sum(1 for r in results if r.get("ok"))
    skipped = sum(1 for r in results if r.get("skipped"))
    total_chunks = sum(int(r.get("chunks") or 0) for r in results)
    status = knowledge_status()

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "ingested": ok,
                    "skipped": skipped,
                    "files": len(results),
                    "chunks": total_chunks,
                    "status": status,
                },
                indent=2,
            )
        )
    else:
        print(f"[ingest] {ok}/{len(results)} files · {total_chunks} chunks · {skipped} skipped")
        print(f"[ingest] corpus: {status['chunks']} chunks, {status['db_mb']} MB")

    return 0 if ok > 0 or total_chunks > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

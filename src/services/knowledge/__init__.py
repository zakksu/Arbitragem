"""Knowledge corpus — offline ingest, FTS search (10.0-alpha)."""

from src.services.knowledge.store import ingest_file, ingest_text, knowledge_status, search_chunks

__all__ = ["ingest_file", "ingest_text", "knowledge_status", "search_chunks"]

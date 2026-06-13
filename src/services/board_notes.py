"""Blackboard notes persistence per symbol."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.models import BoardNote


class BoardNotesService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, symbol: str) -> BoardNote | None:
        return (
            self.session.query(BoardNote)
            .filter(BoardNote.symbol == symbol.upper())
            .order_by(BoardNote.updated_at.desc())
            .first()
        )

    def save(self, symbol: str, content: str, levels: dict | None = None) -> BoardNote:
        sym = symbol.upper()
        note = self.get(sym)
        if not note:
            note = BoardNote(symbol=sym, content=content, levels=levels or {})
            self.session.add(note)
        else:
            note.content = content
            if levels is not None:
                note.levels = levels
            note.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(note)
        return note

    def save_ai_report(self, symbol: str, report: str) -> BoardNote:
        sym = symbol.upper()
        note = self.get(sym)
        if not note:
            note = BoardNote(symbol=sym, content="", ai_report=report)
            self.session.add(note)
        else:
            note.ai_report = report
            note.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(note)
        return note

    def to_dict(self, note: BoardNote | None) -> dict:
        if not note:
            return {"symbol": "", "content": "", "levels": {}, "ai_report": None}
        return {
            "symbol": note.symbol,
            "content": note.content,
            "levels": note.levels or {},
            "ai_report": note.ai_report,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }

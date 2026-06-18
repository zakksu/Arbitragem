"""Blackboard layout presets — SQLite persistence (3.0-rc)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.models import BoardLayout

DEFAULT_PRESETS: dict[str, dict] = {
    "scalp": {"watch_w": "220px", "board_w": "1fr", "ideas_w": "300px"},
    "structure": {"watch_w": "200px", "board_w": "1.2fr", "ideas_w": "340px"},
    "learn": {"watch_w": "240px", "board_w": "1fr", "ideas_w": "320px"},
    "archaeology": {"watch_w": "200px", "board_w": "1.4fr", "ideas_w": "280px"},
    "golden": {"watch_w": "0px", "board_w": "1fr", "ideas_w": "360px"},
    "options_hedge": {"watch_w": "200px", "board_w": "1.2fr", "ideas_w": "340px"},
    "pairs": {"watch_w": "240px", "board_w": "1fr", "ideas_w": "280px"},
}


class BoardLayoutService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_presets(self) -> list[dict]:
        rows = self.session.query(BoardLayout).order_by(BoardLayout.name).all()
        if not rows:
            return [
                {"name": k, "preset": k, "columns": v, "is_default": k == "scalp"}
                for k, v in DEFAULT_PRESETS.items()
            ]
        return [self._to_dict(r) for r in rows]

    def save_preset(self, name: str, columns: dict, *, is_default: bool = False) -> dict:
        if is_default:
            for row in self.session.query(BoardLayout).all():
                row.is_default = False
        row = self.session.query(BoardLayout).filter(BoardLayout.name == name).first()
        if row:
            row.columns = columns
            row.preset = name
            row.is_default = is_default
        else:
            row = BoardLayout(name=name, preset=name, columns=columns, is_default=is_default)
            self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return self._to_dict(row)

    def get_active(self) -> dict:
        row = self.session.query(BoardLayout).filter(BoardLayout.is_default.is_(True)).first()
        if row:
            return self._to_dict(row)
        return {"name": "scalp", "preset": "scalp", "columns": DEFAULT_PRESETS["scalp"], "is_default": True}

    @staticmethod
    def _to_dict(row: BoardLayout) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "preset": row.preset,
            "columns": row.columns or {},
            "is_default": row.is_default,
        }

    def seed_defaults(self) -> None:
        if self.session.query(BoardLayout).count() > 0:
            return
        for i, (name, cols) in enumerate(DEFAULT_PRESETS.items()):
            self.session.add(
                BoardLayout(name=name, preset=name, columns=cols, is_default=(i == 0))
            )
        self.session.commit()

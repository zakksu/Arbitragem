"""Replay lab — delegates to Replay Training Engine (10.0)."""

from __future__ import annotations

from src.services.replay_engine import get_replay, start_replay

__all__ = ["start_replay", "get_replay"]

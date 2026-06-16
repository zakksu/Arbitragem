"""World market clocks — B3, NY, LON, TYO, SHA (4.0-alpha)."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

_MARKETS = (
    {"id": "b3", "label": "B3 SP", "tz": "America/Sao_Paulo", "open": time(10, 0), "close": time(17, 0)},
    {"id": "ny", "label": "NY", "tz": "America/New_York", "open": time(9, 30), "close": time(16, 0)},
    {"id": "lon", "label": "LON", "tz": "Europe/London", "open": time(8, 0), "close": time(16, 30)},
    {"id": "tyo", "label": "TOK", "tz": "Asia/Tokyo", "open": time(9, 0), "close": time(15, 0)},
    {"id": "sha", "label": "SHA", "tz": "Asia/Shanghai", "open": time(9, 30), "close": time(15, 0)},
)

_WEEKEND = {5, 6}  # Sat, Sun


def _session_status(local_dt: datetime, open_t: time, close_t: time) -> str:
    if local_dt.weekday() in _WEEKEND:
        return "closed"
    now_t = local_dt.time()
    if open_t <= now_t < close_t:
        return "open"
    if now_t < open_t:
        return "pre"
    return "closed"


def _minutes_to_open(local_dt: datetime, open_t: time) -> int | None:
    if local_dt.weekday() in _WEEKEND:
        return None
    open_dt = local_dt.replace(hour=open_t.hour, minute=open_t.minute, second=0, microsecond=0)
    if local_dt.time() < open_t:
        return int((open_dt - local_dt).total_seconds() // 60)
    return None


def get_market_clocks() -> dict:
    markets = []
    for m in _MARKETS:
        tz = ZoneInfo(m["tz"])
        local_dt = datetime.now(tz)
        status = _session_status(local_dt, m["open"], m["close"])
        markets.append(
            {
                "id": m["id"],
                "label": m["label"],
                "local_time": local_dt.strftime("%H:%M"),
                "status": status,
                "next_event": "open" if status in ("closed", "pre") else "close",
                "minutes_to_open": _minutes_to_open(local_dt, m["open"]),
            }
        )
    return {"markets": markets, "as_of": datetime.utcnow().isoformat() + "Z"}

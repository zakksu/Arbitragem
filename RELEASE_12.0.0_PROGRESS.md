# Release 12.0.0 — Progress tracker

**Version:** `12.0.0` (GA)

## 12.0 GA checklist

| ID | Owner | Deliverable | Status |
|----|-------|-------------|--------|
| A12.1 | Backend | `clear_cost_model.py` + `data/clear_costs.json` | ✅ |
| A12.2 | Backend | `GET /costs/scalp/{symbol}` | ✅ |
| A12.3 | Backend | `MOTOR_FIXED_LOT_SHARES=100` in capital manager | ✅ |
| A12.4 | Backend | `scripts/premarket_check.py` | ✅ |
| A12.5 | Backend | `GET /ops/live-radar` | ✅ |
| A12.6 | Backend | Breakeven gate on confirm | ✅ |
| W12.1 | Worker | Cost chip on confirm step | ✅ |
| W12.2 | Worker | Live Radar lamps (HTMX poll) | ✅ |
| W12.4 | Worker | Outbox copy hint in Live Radar | ✅ |

## Out of scope (12.0)

- **Crypto live** — watchlist/paper off by default; no broker fee/margin model
- **DLL auto-live** — Phase C gate (`ready_to_execute` stays false)

## Tests

| Suite | Status |
|-------|--------|
| `tests/test_live_radar.py` | ✅ |
| `tests/test_clear_cost_model.py` | ✅ |
| Full `pytest tests/` | 342+ pass |

# Release 14.1 — Execution ladder + session prep

**Status:** shipped — tag `v14.1.1` on `main`

| 14.1h | Desk command strip (radar + prep merged), weekly strategy sim report |

## Shipped

| Increment | Deliverable |
|-----------|-------------|
| 14.1a | `profit_execution_ladder.py` — paper / manual / NTSL / DLL modes |
| 14.1b | `GET /api/v1/integrations/profit/execution-ladder` |
| 14.1c | Live Radar mode + outbox auto-copy |
| 14.1d | `scripts/profit_manual_assist.py`, `archive_profit_outbox.py` |
| 14.1e | `session_prep.py` + `GET /api/v1/session/prep` |
| 14.1f | `scripts/session_prep.py` + board session prep strip |
| 14.1g | `docs/MARKET_SESSION_ROUTINE.md` — Filipe pre/during checklist |

## Before next session

```powershell
python scripts/dev.py start --wait --open
python scripts/session_prep.py
```

Paper mode (default): motor + journal — no Profit clicks.

Manual mode: set `PAPER_TRADING_MODE=false`, use Live Radar outbox hint.

## Tests

```powershell
pytest tests/test_profit_execution_ladder.py tests/test_session_prep.py -q
```

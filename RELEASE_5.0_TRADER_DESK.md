# Release 5.0 — Trader Desk + Trader Agent (Phase A & B)

**Hosting:** deferred. Use `python scripts/launch.py` locally.

## Phase A — Fast board (shipped)

- [x] **Trader Desk** footer replaces pulse rail (risk + blotter + motor log)
- [x] News/calendar **lazy-loaded** via `<details>` (no RSS on first paint)
- [x] **SSE** `/board/stream/trader-desk` (10s push) + HTMX initial load
- [x] Watchlist fast path (synthetic ATR in paper mode)

## Phase B — Trustworthy agent (shipped)

- [x] `MotorJournal` model + `motor_journal` service
- [x] `TraderAgent.run_trader_cycle()` — unified motor entry + journal
- [x] Background motor + `POST /orchestrator/run` use trader agent
- [x] Blotter: positions, pipeline, profit tickets, today trades
- [x] Risk **budget** panel (loss room, net Δ, paper capital)

## Phase C — Live path (gated)

See [docs/PHASE_C_GATE.md](docs/PHASE_C_GATE.md). Ship only when paper journal proves:

- Win rate / PF thresholds met on journal
- No unexplained motor errors for N sessions
- Profit DLL or Chart Trading loop verified

## Launcher

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/launch.py
```

Or: `python scripts/dev.py launch` (alias)

## Status tick (agent / manual)

```powershell
python scripts/status_tick.py
```

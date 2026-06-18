# Market session routine — Filipe (manual + paper)

**Use this before your next 2-hour B3 session.**  
One command: `python scripts/session_prep.py`

---

## Night before / morning (T−30 min)

| # | Action | Command / where |
|---|--------|-----------------|
| 1 | Start stack | `python scripts/dev.py start --wait --open` |
| 2 | Session checklist | `python scripts/session_prep.py` |
| 3 | Open ProfitChart | Already running at `%APPDATA%\Nelogica\Profit\profitchart.exe` |
| 4 | Profit account | **Paper:** Sim **3368** · **Live manual:** Day account per `.env` |
| 5 | Board | http://localhost:8000/board → **Desk** tab |
| 6 | Sleeves | Status bar → **CASH** = green (open) |
| 7 | Mode check | Live Radar shows `Exec: paper_stub` (learning) or `manual_outbox` (live clicks) |

If `session_prep.py` shows blockers → fix before open.

---

## Pre-open (T−10 min)

| # | Action |
|---|--------|
| 1 | Live Radar — lamps mostly green; note any yellow |
| 2 | Watchlist loaded (Core5 symbols) |
| 3 | Day loss limit in status bar (default R$ 100 on R$ 1k) |
| 4 | Clear old outbox if needed: `python scripts/archive_profit_outbox.py` |

---

## During market — **PAPER** (recommended now)

`PAPER_TRADING_MODE=true` · motor auto-fills · **no Profit clicks**

| # | You do | System does |
|---|--------|-------------|
| 1 | Stay on **Desk** tab | Live Radar refreshes every 15s |
| 2 | Optional: **Scan** (toolbar) | Idea Stack refreshes |
| 3 | Click top idea → **Confirm** (modal) | Cost chip + gates |
| 4 | — | Motor executes via stub → journal fill |
| 5 | **Journal** tab | Blotter + grades |
| 6 | **PnL** tab | Intraday curve (SSE 5s) |
| 7 | If red day P&L hits limit | Stop — sleeves / gate block new trades |

**Keyboard:** `S` scan · `1-9` watchlist · `Enter` top idea · `R` refresh

---

## During market — **MANUAL** (Profit open, no DLL)

`PAPER_TRADING_MODE=false` · `PROFIT_EXEC_LADDER=manual_outbox`

| # | You do | System does |
|---|--------|-------------|
| 1 | ProfitChart: Chart Trading panel open, correct account | — |
| 2 | Desk → **Confirm** → **Execute** | Writes outbox ticket |
| 3 | Live Radar **Outbox** — hint auto-copied | e.g. `C Mercado · 100 · PETR4` |
| 4 | **Paste in Profit** Chart Trading + send | Real fill in Profit |
| 5 | Or: `python scripts/profit_manual_assist.py` | Clipboard + opens `exports/ntsl/` |
| 6 | **Journal** tab | Reconcile with Profit blotter |
| 7 | Blackboard levels | Entry / stop / target beside chart |

---

## During market — **NTSL backtest** (not live clicks)

`PROFIT_EXEC_LADDER=ntsl_export` or `PROFIT_NTSL_ON_EXECUTE=true`

| # | Action |
|---|--------|
| 1 | Confirm/execute idea |
| 2 | Open `exports/ntsl/` (Explorer may auto-open) |
| 3 | Profit → Editor → Importar → run Tick-a-Tick |
| 4 | Export CSV → watcher promotes backtest proof |

---

## Post-session (15 min)

| # | Action |
|---|--------|
| 1 | **Journal** tab → Export CSV |
| 2 | `python scripts/golden_path_record_session.py` if all green |
| 3 | Review **PnL** tab — day curve |
| 4 | Optional: `python scripts/dev.py stop` |

---

## Execution ladder (reference)

| Mode | When |
|------|------|
| `paper_stub` | Learning, Phase C paper days (**default**) |
| `manual_outbox` | Profit open, no DLL |
| `ntsl_export` | Backtest in Profit Editor |
| `dll_auto` | After Nelogica installs ProfitDLL |

See [PROFIT_EXECUTION_LADDER.md](PROFIT_EXECUTION_LADDER.md).

---

## API

- `GET /api/v1/session/prep` — machine-readable checklist  
- `GET /api/v1/integrations/profit/execution-ladder` — active mode

# Agent A ↔ Agent B integration contract

## API surface (Agent A owns `src/api/routes.py`)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /risk/summary` | Day P&L, loss limits, paper mode, `pnl_source`, `profit_day_pnl` | Live Monitor, risk cockpit |
| `GET /health` | Integrations + `scanner_mode`, symbol count | Sidebar, Settings |
| `GET /alerts/status` | Telegram/Discord configured | Settings |
| `POST /alerts/test` | Send test notification | Settings |
| `GET /integrations/profit/test` | Profit bridge probe | Settings |
| `GET /scanner/insights` | Top scalp candidates (reliability) | Scanner, Home |
| `GET /universe/ibov-top20` | IBOV Top 20 universe CSV | Scanner tab |
| `GET /system/events` | Recent errors/warnings | Settings |
| `GET /backtests` | Backtest run history | Backtest page |
| `GET /optimizations` | Optimization history | Backtest page |
| `POST /optimizations/{id}/apply` | Apply best params to strategy | Backtest page |
| `POST /backtest/upload` | Profit CSV upload + parse | Backtest page |
| `POST /optimize` | grid / genetic / walk_forward | Backtest page |
| `POST /strategies/{id}/start` | 400 if risk check fails | Live Monitor |
| `PATCH /strategies/{id}` | NTSL / description | Strategies |

### 2.0 Blackboard (Supervisor API · Worker HTMX UI)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /board` | HTMX workspace shell | Browser (Worker `src/web/`) |
| `GET /universe/filipe-core14` | Core14 + sector baskets | Watchlist partial |
| `GET /ideas` | Idea Stack list | `partials/idea_stack.html` |
| `POST /ideas/generate` | Build ideas from latest scan | Scanner run / manual |
| `POST /ideas/{id}/confirm` | Paper confirm + risk gate | W2.4 modal |
| `POST /backtest/run` | Profit bridge backtest job (symbol/strategy/period) | W2.8 proof badge |
| `POST /exports/scan` | Manual trigger — ingest `exports/profit/*.csv` | W2.8 / ops |
| `GET /setup/status` | Integration wizard steps | W2.6 Settings / board |
| `POST /setup/test` | Probe Profit/Clear/BOVA | W2.6 test button |
| `GET /integrations/profit/test` | Includes `bova_chain` | Settings |

### 2.0-rc → GA (Supervisor)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /stream/quotes?symbols=PETR4,VALE3` | SSE quote batch + 15s heartbeat | W2.1 watchlist (`EventSource`) |
| `GET /symbols/{sym}/report?force=false` | AI report card (24h cache) | W2.5 Report tab |
| `POST /ideas/{id}/confirm?paper_override=false` | Lifecycle gate → `confirmed` | W2.4 modal step 1 |
| `POST /ideas/{id}/execute` | Paper fill (spread + 1 tick) → `executed` | W2.4 modal step 2 |
| `POST /risk/kill-switch` | `{"active":true,"reason":"..."}` blocks confirm/execute | Sidebar STOP + board |

`GET /risk/summary` now includes `kill_switch_active`, `kill_switch_reason`, `can_confirm_ideas`, `can_execute_ideas`, `pnl_source` (`journal` | `profit` | `clear`), and `profit_day_pnl` when the bridge exposes `/account`.

#### Day P&L truth (3.0.1)

Priority: **journal** (today's `Trade` rows) → **Profit** bridge (`GET /account` or sum of `/trades/today`) → **Clear** mock/live `day_pnl`.

```json
{
  "day_pnl": 16.0,
  "journal_pnl": 0.0,
  "profit_day_pnl": 16.0,
  "broker_day_pnl": 125.5,
  "pnl_source": "profit",
  "paper_trading_mode": true
}
```

Worker: show **one** Day P&L in status bar; use `pnl_source` label (Profit / Journal / Clear).

#### `GET /setup/status` (3.0.1)

Adds `profit_dll_detect`:

```json
{
  "profit_dll_detect": {
    "found": true,
    "count": 1,
    "candidates": ["C:\\Nelogica\\Profit\\ProfitDLL.dll"],
    "recommended": "C:\\Nelogica\\Profit\\ProfitDLL.dll",
    "platform": "win32"
  }
}
```

ProfitDLL step includes `candidates[]` and `auto_detected` when path resolved without manual `.env`.

CLI: `python scripts/detect_profit_dll.py` (exit 0 = found, 2 = not found).

Profit bridge stub: `GET /account` → `{day_pnl, balance_brl, source}`.

#### Drawdown metrics (3.0.1)

Backtest CSV parse and python backtest emit `max_drawdown_pct` only when computable — **never default to 100%** when absent. Gate: missing DD passes; explicit DD > 8% fails.

#### Idea lifecycle (A2.10)

`detected` → `backtested` (PF ≥ 1.3, DD ≤ 8%) → `confirmed` → `executed`

- Confirm rejects without passing `backtest_proof` unless `paper_override=true`.
- Execute requires `status=confirmed`; writes `Trade` + journal with slippage model `spread_plus_1_tick`.

#### `GET /stream/quotes` (SSE)

```json
{"type":"quotes","ts":1718467200.1,"quotes":{"PETR4":{"last":38.01,"bid":38.00,"ask":38.02,"volume":12000}}}
{"type":"heartbeat","ts":1718467215.0}
```

#### `GET /symbols/PETR4/report`

```json
{
  "symbol": "PETR4",
  "sector": "Energia",
  "narrative": "...",
  "quote": {"last": 38.01, "bid": 38.0, "ask": 38.02, "volume": 12000},
  "scan": {"spike_score": 72.5, "pattern_tags": ["vwap_reclaim"]},
  "backtest_proof": {"profit_factor": 1.42, "max_drawdown_pct": 5.8},
  "cached": false
}
```

#### `POST /risk/kill-switch`

Request: `{"active": true, "reason": "manual stop"}`  
Response: `{"active": true, "activated_at": "...", "reason": "...", "paused_strategies": 1, "rejected_ideas": 2}`

### 3.0 Structure Deck (GA)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /signals/opportunity-rail` | PETR/PRIO + steel z-scores | `opportunity_rail.html` footer |
| `GET /portfolio/backtest` | Combined Core14 book simulation | Setup drawer partial |
| `GET /board/layouts` | Layout preset list | Status bar presets |
| `POST /board/layout/{preset}` | Activate column layout | HTMX preset buttons |
| `GET /risk/cockpit` | Net delta, sectors, margin | Risk strip |
| `POST /ideas/from-structure` | Create multi-leg idea | Structure builder |
| `POST /walk-forward/promote` | Promote gated ideas | Scheduler / manual |
| `POST /strategies/pause-all` | Kill switch alias (`active: true`) | STOP ALL button |

### 4.0-alpha — Scalper Cockpit (Supervisor API · Worker HTMX)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /risk/profile` | Persisted risk limits (singleton SQLite row) | W4.1 risk drawer |
| `PUT /risk/profile` | Update limits | W4.1 risk drawer |
| `GET /profit/pnl` | Day P&L truth (`pnl_source`, journal/profit/clear) | W4.2 KPI strip |
| `GET /market/clocks` | B3/NY/LON/TOK/SHA status + local time | W4.4 clocks row |
| `GET /watchlist/enriched` | Core14 + quotes + `atr_pct`, `est_cost_brl`, `idea_score`, `bias` | W4.3 watchlist |
| `GET /ideas?symbol=PETR4` | Per-symbol filtered idea stack | W4.5 focus mode |

#### `GET /risk/profile`

```json
{
  "max_daily_loss_brl": 500.0,
  "max_open_positions": 5,
  "cost_per_trade_brl": 50.0,
  "max_net_delta": 0.5,
  "sector_caps": {"default": 40.0},
  "updated_at": "2026-06-16T12:00:00"
}
```

`PUT /risk/profile` accepts partial updates to the same fields.

#### `GET /profit/pnl`

Same shape as `resolve_day_pnl()` — use for header KPI instead of duplicating Clear mock.

#### `GET /market/clocks`

```json
{
  "markets": [
    {"id": "b3", "label": "B3 SP", "local_time": "10:30", "status": "open", "next_event": "close", "minutes_to_open": null}
  ],
  "as_of": "2026-06-16T13:30:00Z"
}
```

Status: `open` | `closed` | `pre`.

#### `GET /watchlist/enriched`

```json
{
  "count": 14,
  "symbols": [
    {
      "symbol": "PETR4",
      "sector": "Energia",
      "last": 38.01,
      "bid": 38.0,
      "ask": 38.02,
      "atr_pct": 2.1,
      "est_cost_brl": 52.0,
      "idea_score": 72,
      "bias": "long"
    }
  ]
}
```

Sorted by `idea_score` desc. Worker may client-sort columns; API default = best edge first.

#### Idea score (A4.3)

Each idea dict from `GET /ideas` includes `idea_score` (0–100) from `score_idea()`: reliability × backtest gate × walk-forward × vol-fit tags.

Scheduler: `profit_pnl_sync` every **2 min** (stub refresh via `resolve_day_pnl`).

ProfitDLL: `python scripts/detect_profit_dll.py` · `GET /setup/status` → `profit_dll_detect`.


#### `POST /backtest/run` (API proxy → bridge)

Request body:

```json
{
  "symbol": "PETR4",
  "strategy": "scalp_default",
  "period": "90d"
}
```

Response (stub / bridge):

```json
{
  "job_id": "uuid",
  "status": "completed",
  "symbol": "PETR4",
  "strategy": "scalp_default",
  "period": "90d",
  "profit_factor": 1.42,
  "max_drawdown_pct": 5.8,
  "trades": 156,
  "win_rate_pct": 52,
  "source": "stub"
}
```

Gate for Idea Stack promotion: `profit_factor >= 1.3`, `max_drawdown_pct <= 8` (see `backtest_gates` in `/setup/status`).

#### `POST /exports/scan`

Scans `exports/profit/*.csv`, parses via `parse_profit_backtest_csv`, records `BacktestRun`, attaches `backtest_proof` to matching `TradeIdea` (or creates promoted idea).

Response: `{"imported": 1, "promoted": 1}`

#### Sector pair ideas (A2.5a)

Scanner emits `sector_corr_break` on energy (`PETR4/PRIO3`) and steel (`GGBR4/CSNA3/USIM5`) baskets when intraday spread exceeds threshold. Ideas use `structure_type: "pair_relative"` with two legs; symbol label `LONG/SHORT`.

## When Agent A adds a backend feature

1. Add route + schema in `src/api/schemas.py`
2. Run `pytest -v`
3. Run `python scripts/dev.py restart --wait`
4. Update this table
5. Tell Agent B which page should call it

## When Agent B adds a UI feature

1. Use `dashboard/utils.py` (`api_get`, `api_post`, `api_patch`, `api_upload_csv`)
2. Never import `src/` in Streamlit — always HTTP to API
3. Add view under `dashboard/views/` and register in `dashboard/app.py`
4. If API missing, add a thin route (coordinate with Agent A)

## Shared dev loop

```bash
python scripts/dev.py start --wait --json
pytest -v
# refresh http://localhost:8501
```

## Current gaps

- [ ] Real ProfitDLL ctypes callbacks (use `scripts/profit_dll_bridge.py` scaffold on Windows)
- [ ] Clear API live Smart Trader endpoints (credentials in `.env`)
- [ ] Walk-forward on real tick data (Agent A)
- [ ] In-dashboard alert token editor (still `.env` only)

## Performance (Supervisor)

- `GET /health` caches integration probes ~30s
- `dashboard/api_cache.py` — `get_sidebar_context()` bundles sidebar fetches
- Scanner uses `get_quotes_batch()` — one bridge call for IBOV top 20
- Set `SCANNER_OLLAMA_ON_SCAN=false` to skip slow AI during bulk scans
- Set `OLLAMA_ENABLED=false` to disable AI probes entirely

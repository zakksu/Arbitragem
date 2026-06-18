# Agent A ↔ Agent B integration contract

## API surface (Agent A owns `src/api/routes.py`)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /risk/summary` | Day P&L, loss limits, paper mode, `pnl_source`, `profit_day_pnl` | Live Monitor, risk cockpit |
| `GET /health` | Integrations + `scanner_mode`, symbol count | Sidebar, Settings |
| `GET /alerts/status` | Telegram/Discord configured | Settings |
| `POST /alerts/test` | Send test notification | Settings |
| `GET /integrations/profit/test` | Profit bridge probe | Settings |
| `GET /integrations/profit/execution-ladder` | Paper/manual/NTSL/DLL ladder status | Live radar, setup wizard |
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

#### `GET /integrations/profit/execution-ladder` (14.1)

Resolves active execution rung without requiring ProfitDLL.

**Env:** `PROFIT_EXEC_LADDER=auto` · `PROFIT_NTSL_ON_EXECUTE=true` · `PROFIT_MANUAL_AUTO_COPY=true`

```json
{
  "configured": "auto",
  "active_mode": "paper_stub",
  "paper_trading_mode": true,
  "dll_found": false,
  "dll_loadable": false,
  "rungs": [
    {"id": "paper_stub", "label": "Paper + stub", "active": true, "available": true},
    {"id": "manual_outbox", "label": "Manual outbox", "active": false, "available": true},
    {"id": "ntsl_export", "label": "NTSL export", "active": false, "available": true},
    {"id": "dll_auto", "label": "DLL auto", "active": false, "available": false}
  ],
  "ntsl_dir": "exports/ntsl",
  "outbox_dir": "data/profit_outbox",
  "doc": "/docs/PROFIT_EXECUTION_LADDER.md"
}
```

`active_mode`: `paper_stub` | `manual_outbox` | `ntsl_export` | `dll_auto` (never `auto`).

CLI: `python scripts/profit_manual_assist.py` — prints ladder status + latest outbox hint.

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

### 4.0-beta — Trade Product + pulse (Supervisor API · Worker HTMX)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /symbols/{sym}/trade-product` | Trade Product card JSON (thesis, odds, levels, legs) | W4.7 `trade_product.html` |
| `GET /symbols/{sym}/odds` | Pattern win rate from journal + backtest | W4.12 odds widget |
| `GET /pulse` | News / calendar / lesson thirds | W4.9 pulse rail |
| `GET /board/partials/pulse-rail` | **Alias → trader desk** (`bb-trader-desk`) | Board footer (Phase A) |
| `GET /board/partials/pulse-rail-legacy` | Classic 33/33/33 pulse + social chips | W4.20 social chips |
| `GET /board/partials/market-context` | Lazy news/calendar snippet | Trader desk expand |
| `POST /replay/run` | Sandbox replay job id | W4.11 replay UI |
| `POST /ntsl/arm` | Export NTSL to `exports/ntsl/` (optional `legs[]`; auto-resolves from structure builder when omitted) | W4.10 arm flow |

#### `GET /symbols/PETR4/odds`

```json
{
  "symbol": "PETR4",
  "structure_type": "scalp",
  "win_rate_pct": 52.0,
  "sample_size": 20,
  "journal_trades": 0,
  "backtest_trades": 0,
  "profit_factor": null,
  "source": "stub",
  "lookback_days": 90
}
```

`source`: `journal` (≥3 trades) · `backtest` · `stub`. Merged into `trade-product.odds` when DB session available.

#### `POST /replay/run`

```json
{"strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox"}
```

Response includes `job_id`, `mode: "sandbox"`, `message` (manual ProfitChart hint when DLL cannot auto-start).



### 4.0-rc — KPI history, paper realism, education (Supervisor API · Worker HTMX)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /kpi/history?range=today\|5d\|20d\|3mo\|ytd` | P&L, trades, win rate, PF-20, avg slippage | W4.13 KPI chips |
| `GET /education` | Full pack (axioms + structures + daily) | W4.17 HelpTip / Learn preset |
| `GET /education/axioms` | Trading axioms list | Pulse rail, tour |
| `GET /education/structures` | Structure blurbs map | Structure builder |
| `GET /education/daily` | Rotating daily axiom | W4.9 pulse `lesson` third |
| `GET /education/structures/{type}` | Single structure blurb | Trade Product education |

#### `GET /kpi/history?range=5d`

```json
{
  "range": "5d",
  "pnl_brl": 120.5,
  "trades": 8,
  "win_rate_pct": 62.5,
  "profit_factor_20": 1.42,
  "avg_slippage_ticks": 1.5,
  "pnl_source": "journal"
}
```

`avg_slippage_ticks`: mean spread+1-tick model from executed paper trades (`raw_payload.slippage_model`).

#### `POST /ideas/{id}/confirm` — paper fill preview (A4.16)

When `paper_trading_mode=true`, confirm response adds `paper_fill_preview`:

```json
{
  "id": 12,
  "status": "confirmed",
  "symbol": "PETR4",
  "paper_fill_preview": {
    "slippage_model": "spread_plus_1_tick",
    "paper_trading_mode": true,
    "total_slippage_brl": 4.0,
    "total_fees_brl": 0.874,
    "legs": [
      {
        "symbol": "PETR4",
        "side": "buy",
        "quantity": 100,
        "ideal_price": 38.0,
        "expected_fill": 38.04,
        "slippage_ticks": 4.0,
        "slippage_brl": 4.0,
        "fees_brl": 0.874,
        "quote_bid": 37.98,
        "quote_ask": 38.02
      }
    ]
  }
}
```

`fees_brl` per leg from `clear_cost_model.b3_fee_per_leg` (cash equities only). `POST /ideas/{id}/execute` includes the same `paper_fill_preview` when paper mode is on.

Worker: show ideal vs expected per leg in confirm modal before execute.

`GET /symbols/{sym}/trade-product` now includes `structure_education` from `data/education/structures.json`.

`GET /pulse` → `lesson` uses `daily_axiom()`; `axioms_count` = total axioms in pack.

### 4.0.0 GA — paper validation (Supervisor API · Worker W4.18)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /paper/validation` | Paper week #3 checklist + `gate_pass` | W4.18 GA banner / settings |
| `GET /paper/journal/export?format=json` | Trades + ideas + journal bundle | W4.18 export button |
| `GET /paper/journal/export?format=csv` | CSV download | W4.18 export |
| `POST /paper/journal/export` | Write `exports/journal/paper_journal_*.csv` | Ops / CLI parity |

#### `GET /paper/validation`

```json
{
  "week": "paper_week_3",
  "gate_pass": false,
  "paper_trading_mode": true,
  "checklist": [
    {"id": "structure_confirms", "current": 4, "target": 10, "ok": false},
    {"id": "journal_trades", "current": 2, "target": 5, "ok": false},
    {"id": "trade_products_journaled", "current": 1, "target": 3, "ok": false},
    {"id": "distinct_structures", "current": 1, "target": 2, "ok": false}
  ],
  "cli": "python scripts/paper_validation.py"
}
```

`gate_pass`: `structure_confirms >= 10` AND `trade_products_journaled >= 3`.

### 4.1-alpha — futures + social read-only (Supervisor API · Worker HTMX)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /watchlist/enriched` | Core14 + **WINFUT/WDOFUT** rows + `futures[]` | W4.19 watchlist styling |
| `GET /universe/futures` | Futures metadata + quote stubs | W4.19 session badges |
| `GET /signals/social?limit=12` | RSS + curated Twitter read-only cards | W4.20 pulse news third |

**Env:** `FUTURES_WATCHLIST_ENABLED=true` · `SOCIAL_SIGNALS_ENABLED=true`

#### Futures row (`GET /watchlist/enriched`)

```json
{
  "symbols": [
    {
      "symbol": "WINFUT",
      "name": "Mini Ibovespa",
      "asset_class": "future",
      "underlying": "IBOV",
      "last": 128450,
      "bid": 128445,
      "ask": 128455,
      "session_status": "open",
      "session_label": "B3 day",
      "quote_source": "stub",
      "watch_score": 42,
      "atr_pct": 0.45
    }
  ],
  "futures_count": 2,
  "futures": ["..."]
}
```

`session_status`: `open` | `pre` | `closed` — B3 futures day session (09:00–18:25 BRT).

#### `GET /signals/social`

```json
{
  "signals": [
    {
      "id": "tw-b3_official",
      "source": "twitter",
      "author": "@B3_Official",
      "text": "Ibovespa futures volume above 30-day average...",
      "symbols": ["WINFUT", "BOVA11"],
      "sentiment": "bullish",
      "read_only": true,
      "auto_trade": false,
      "published_at": "2026-06-16T12:00:00Z"
    }
  ],
  "count": 6,
  "read_only": true,
  "auto_trade": false,
  "disclaimer": "Read-only signals — never auto-trade from social feeds.",
  "sources": ["rss", "twitter"],
  "sources_active": ["rss", "twitter"],
  "fetched_at": "2026-06-16T12:05:00Z",
  "freshness_minutes": 5,
  "session": {"market": "b3_futures", "session_status": "open", "session_label": "B3 day"}
}
```

**No auto-trade** — signals are display-only; confirm/execute paths ignore this feed.

### 4.2-alpha — crypto watch + trade archaeology (Supervisor API · Worker HTMX)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /watchlist/enriched` | Core14 + futures + **BTC/ETH/SOL** + `crypto[]` | W4.22 crypto watchlist section |
| `GET /universe/crypto` | Crypto metadata + Binance/stub quotes | W4.22 read-only badges |
| `GET /archaeology/timeline?limit=100&symbol=` | Imported historical trades (newest first) | W4.21 history timeline |
| `POST /archaeology/import` | Upload Profit trade-list CSV | W4.21 import button |
| `POST /archaeology/scan` | Scan `exports/archaeology/*.csv` | W4.21 folder watcher UI |

**Env:** `CRYPTO_WATCHLIST_ENABLED=true` · `BINANCE_QUOTES_ENABLED=true` · `ARCHAEOLOGY_IMPORT_DIR=exports/archaeology`

#### Crypto row (`GET /watchlist/enriched`)

```json
{
  "symbol": "BTC",
  "asset_class": "crypto",
  "binance_pair": "BTCUSDT",
  "read_only": true,
  "auto_trade": false,
  "last": 95012.5,
  "quote_source": "binance",
  "market": "binance_spot"
}
```

**Watch-only** — no Clear routing; paper fills via `POST /paper/crypto/execute` (A4.24).

#### Shared watchlist builder (A4.25a)

Board + API must use the same pipeline:

```python
from src.services.enriched_watchlist import build_enriched_watchlist
payload = build_enriched_watchlist(db)  # symbols, futures[], crypto[]
```

#### Crypto paper stub (A4.24)

| Endpoint | Purpose |
|----------|---------|
| `GET /paper/crypto/preview?symbol=BTC&side=buy&quantity=0.01` | Binance-based fill preview |
| `POST /paper/crypto/execute` | Paper fill → `trades` + journal (`source=paper_crypto`) |

```json
POST /paper/crypto/execute
{ "symbol": "BTC", "side": "buy", "quantity": 0.01, "note": "optional" }
```

Requires `PAPER_TRADING_MODE=true` and `CRYPTO_PAPER_ENABLED=true`. Crypto ideas on confirm/execute also route to paper-only (no NTSL/Clear/Profit).

#### Archaeology insights (A4.32)

`GET /archaeology/symbol/{sym}/insights` — merges imported trade stats + `BacktestRun` rows for timeline badges.

| `GET /universe/filipe-core14` | Core14 symbols + sector baskets |
| `GET /universe/filipe-core17` | Core17 symbols (14 + BOVA11, RADL3, MGLU3), `sectors` map, `CORE17_SECTOR_BASKETS` — pairs **W11.4** sector strip |

**Env:** `SCANNER_MODE=filipe_core17` expands motor/scanner universe to 17 names.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/options/core17/refresh` | POST | Verify option tickers vs Profit bridge; writes `data/.dev/core17_options_meta.json` |
| `/options/core17/status` | GET | Last refresh metadata |

Strategy store scan response includes `pack_version`, `new_since_pack`, `removed_since_pack` when `data/.dev/ntsl_pack_version.json` exists (from `generate_core14_ntsl_pack.py`).

#### Knowledge ingest (A11.6)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/knowledge/ingest/insights` | POST | Chunk `data/.dev/b3_history_insights.json` into FTS |
| `/knowledge/ingest/replays` | POST | Recent replay sessions |
| `/knowledge/ingest/strategies` | POST | Indexed NTSL strategies |

CLI: `python scripts/ingest_knowledge.py --path data/.dev/b3_history_insights.json`

| `/replay/archaeology/batch` | POST | Top archaeology symbols replay (A11.7) — `{"limit":10,"symbols":[]}` |
| `/journal/sync/clear` | POST | Clear API fills → `Trade` rows (A12.8) |
| `/quotes/futures` | GET | WIN/WDO rows + B3 session badge (A4.20) |

#### Archaeology summary (A11.3)

`GET /archaeology/summary?limit=15` — top symbols by trade count, win rate, net P&L, lane split, and **`fifo`** block (round trips, FIFO net P&L). Reads archaeology `Trade` rows first; falls back to `data/.dev/b3_history_insights.json` when DB is empty.

`GET /archaeology/timeline` — events include `lane` (futures/cash/options) plus `fifo` aggregate.

Futures watchlist rows include `front_month` from `futures_roll.resolve_futures_quote_symbol()` (WINFUT → active `WIN*` series).

```json
{
  "total_trades": 9770,
  "net_pnl": 12450.5,
  "symbol_count": 142,
  "source": "db",
  "top_symbols": [
    {
      "symbol": "WINV25",
      "trade_count": 8420,
      "win_rate": 0.512,
      "net_pnl": 8200.0
    },
    {
      "symbol": "PETR4",
      "trade_count": 186,
      "win_rate": 0.548,
      "net_pnl": 420.5
    }
  ],
  "lanes": {
    "futures": 8420,
    "cash": 1120,
    "options": 273
  }
}
```

`source` is `"db"` when archaeology trades exist, else `"b3_history_insights.json"`.

#### CEI parser + import (A4.31)

`POST /cei/parse` — upload B3 CEI CSV; returns `preview[]` + `row_count` (no DB write).

`POST /cei/import` — same upload; persists rows via archaeology pipeline (`import_trade_csv`), response includes `source_format: "cei"`.

#### Idea lifecycle gates (A2.10)

`GET /ideas/{id}/gates` — `{ can_confirm, can_execute, blockers[], backtest_gate_pass }`.

`POST /ideas/{id}/confirm` and `POST /ideas/{id}/execute` responses include a `gates` object (same shape).

#### Clear live router (A2.6b)

`GET /execution/clear/status` — `{ clear_configured, live_enabled, paper_trading_mode }`.

Clear execute path journals fills via `JournalService.sync_trades_from_clear()` after order submission (only when `clear_configured`).

#### Journal sync (A12.8)

`POST /api/v1/journal/sync` — imports Profit fills always; Clear fills **only when** `CLEAR_API_KEY` is set.

```json
{
  "clear_configured": false,
  "imported_clear": 0,
  "imported_profit": 2,
  "imported": 2,
  "analyzed": 0
}
```

`POST /api/v1/journal/sync/clear` — Clear-only import; same `clear_configured` + `imported_clear` shape.

When `clear_configured` is false, scheduler and autonomous sync skip Clear mock trades (no `MOCK-T-*` pollution).

#### Profit bridge health (A11.14)

Bridge stub `GET /health` (port 9100):

```json
{
  "status": "ok",
  "dll_mode": "stub",
  "is_paper": true,
  "account_profile": "day",
  "version": "12.0.0"
}
```

`GET /api/v1/ops/profit-bridge/health` — API passthrough when bridge reachable.

`GET /api/v1/ops/live-radar` — `bridge` object includes `dll_mode`, `is_paper`; `lamps.bridge` echoes both for W11.7 outbox polish.

#### VWAP reclaim (A2.5b)

Scanner `raw_data` includes `session_vwap`, `vwap_distance_pct`, `vwap_reclaim_long` when session candles available.

`GET /symbols/{sym}/session-vwap` — symbol panel bundle:

```json
{
  "symbol": "PETR4",
  "last": 38.5,
  "bid": 38.49,
  "ask": 38.51,
  "session_vwap": 38.2,
  "vwap_distance_pct": 0.786,
  "vwap_reclaim_long": false,
  "vwap_reclaim_short": false
}
```

#### `GET /archaeology/timeline`

```json
{
  "events": [
    {
      "id": 1,
      "symbol": "PETR4",
      "side": "buy",
      "quantity": 100,
      "price": 38.5,
      "pnl": 150.0,
      "executed_at": "2025-06-01T00:00:00",
      "source": "archaeology"
    }
  ],
  "count": 1,
  "symbol_filter": null
}
```

#### ProfitChart co-start (A4.15)

`.env`:

```
PROFITCHART_EXE=C:/Nelogica/Profit/ProfitChart.exe
PROFITCHART_CO_START=true
```

`python scripts/dev.py start` on Windows launches ProfitChart when exe exists (optional). Setup wizard step `profitchart` in `GET /setup/status`.

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

### Blocked — requires external deps (Supervisor cannot ship without)

| Item | Blocker | Safe stub today |
|------|---------|-----------------|
| ProfitDLL live quote callbacks | Windows `ProfitDLL.dll` + Nelogica login/subscribe API | `scripts/profit_dll_bridge.py` loads DLL via ctypes when path exists; `probe_dll_loadable()` in health; HTTP fallback to stub |
| Clear Smart Trader live orders | `CLEAR_API_KEY`, `CLEAR_API_SECRET`, `CLEAR_ACCOUNT_ID` in `.env` | `ClearAPIClient` mock mode + `GET /execution/clear/status` |
| Walk-forward on tick-a-tick data | ProfitChart tick export or DLL tick stream | Python WFO uses synthetic bars; set `WALK_FORWARD_USE_BRIDGE_CANDLES=true` for bridge session OHLC when online |
| In-dashboard alert token editor | Product scope | Tokens remain `.env` only |

### Worker-owned (not Supervisor)

- W4.21 archaeology timeline UI · W4.22 crypto watchlist · W4.22b `build_enriched_watchlist()` on board

#### `GET /setup/status` — autonomous ops (4.3)

Response includes `autonomous_ops` and wizard step `autonomous_ops`:

```json
{
  "autonomous_ops": {
    "engine_enabled": true,
    "rankings_sync": true,
    "rankings_sync_interval_hours": 6,
    "walk_forward_auto_promote": true,
    "walk_forward_use_bridge_candles": false,
    "autonomy_motor_enabled": false
  },
  "profit_dll_detect": {
    "found": true,
    "probe": { "loadable": false, "callbacks_wired": false, "reason": "..." }
  }
}
```

## Performance (Supervisor)

- `GET /health` caches integration probes ~30s
- `dashboard/api_cache.py` — `get_sidebar_context()` bundles sidebar fetches
- Scanner uses `get_quotes_batch()` — one bridge call for IBOV top 20
- Set `SCANNER_OLLAMA_ON_SCAN=false` to skip slow AI during bulk scans
- Set `OLLAMA_ENABLED=false` to disable AI probes entirely

## 7.0 — Golden path + symbol factory (Supervisor API · Worker HTMX)

**Env:** `GOLDEN_PATH_MODE=true` — PETR4-only scanner, watchlist, motor seed, quote SSE default.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/golden-path` | GET | Full 7-item checklist + session count |
| `/api/v1/golden-path/reconcile` | GET | PETR4 P&L reconcile (journal vs Profit) |
| `/api/v1/ops/memory` | GET | RAM, motor_cycle_ms, motor_cycle_p95_ms, test badge |
| `/api/v1/ops/live-radar` | GET | Six lamps (api, bridge, motor, scanner, mind, sleeves), `all_green`, `ready_to_scan`, `ready_to_execute` (false until Phase C), `outbox`, `blockers` |
| `/api/v1/ops/profit-bridge/health` | GET | `dll_mode`, `is_paper`, `account_profile` from bridge `/health` (A11.14) |
| `/api/v1/symbol-factory/status` | GET | Factory locked/unlocked, shadow list, Core14 candidates |
| `/api/v1/symbol-factory/shadow` | POST | `{"symbol":"PRIO3"}` — add shadow symbol (409 if locked) |
| `/api/v1/symbol-factory/promote` | POST | `{"symbol":"PRIO3"}` — promote after 3 shadow sessions |

**Board partials (Worker):**

| Partial | Purpose |
|---------|---------|
| `GET /board/partials/golden-path` | Checklist UI |
| `GET /board/partials/ops-panel` | RAM + motor ms + test badge |

**Scripts:**

- `python scripts/test_worker.py --once` — writes `data/.dev/test_status.json`
- `python scripts/status_tick.py --json` — includes `golden_path`, `symbol_factory`, `ram_mb`, `live_radar`, `phase_c`, `autonomy_gates`

### Autonomy motor + Phase C (11.0)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/orchestrator/run` | POST | One paper motor cycle (scan + autonomy confirm/execute + journal FILL) |
| `/api/v1/orchestrator/status` | GET | Motor session, sleeves, last autonomy actions |
| `/api/v1/autonomy/status` | GET | Autonomy engine last run + sleeve map |
| `/api/v1/autonomy/gates` | GET | `golden_path` + `phase_c` + `paper_validation` snapshot |
| `/api/v1/phase-c/status` | GET | Phase C criteria (5 paper days, 20 fills, motor error rate) |

**Scripts (dev — no manual B3 session required when `PAPER_TRADING_MODE=true`):**

```bash
python scripts/autonomy_autopilot.py --cycles 10
python scripts/autonomy_autopilot.py --cycles 5 --fast-track-days 5   # needs AUTONOMY_FAST_TRACK=true
python scripts/autonomy_loop.py --max-cycles 20
python scripts/paper_motor_now.py   # POST orchestrator via running API
python scripts/autonomy_today.py    # scan + S1 replay + one autonomy cycle
```

**Structure types S1–S5** (`stock_scalp_vwap` … `pulse_scalp`) map to replay templates `s1_vwap_reclaim` … `s5_pulse` via `structure_types.replay_strategy_for_structure()`.

### 11.0-beta — Strategy Lab strip (Desk) + NTSL match (Worker W11.1–W11.3)

| Partial | Query | Purpose |
|---------|-------|---------|
| `GET /board/partials/strategy-lab-strip` | — | Collapsible Desk strip: S1–S5 structure chips, rankings, strategy store, link to `/board/strategy-lab` |
| `GET /board/partials/rankings-table` | `detail_target=strategy-lab-detail-slot`, `type={structure_id}` | Rankings filtered by structure; row click targets `#strategy-lab-detail-slot` on Desk |
| `GET /board/partials/replay-player` | `symbol`, `structure_type` | Default replay strategy from `match_ntsl_for_structure()` |
| `GET /board/partials/trade-product` | — | NTSL match chip + “Replay {strategy}” → `#replay-player-slot` |

**Service:** `strategy_store.match_ntsl_for_structure(session, structure_type, symbol=)` scores indexed NTSL rows by tags/name/symbol; falls back to `replay_strategy_for_structure()` when no index hit.

**Env flags:** `ORCHESTRATOR_SCHEDULER_ENABLED=true` (background tick), `AUTONOMY_FAST_TRACK=true` (spread journal across weekdays for Phase C dev only — not production sign-off).

**Streamlit slim:** `GOLDEN_PATH_MODE=true` or `STREAMLIT_SLIM_MODE=true` limits nav to Home, Performance, Journal, Settings.

---

### 10.0-alpha — Replay Training + Strategy Store + Engine Mind

#### `POST /replay/run`

Runs one replay session (tick-sim or Profit bridge when available). Persists `ReplaySession` + fills; feeds journal, `BacktestRun`, optional WFO + Ollama.

```json
{ "strategy": "scalp_default", "symbol": "PETR4", "speed": 10, "mode": "sandbox" }
```

Response includes `job_id`, `status`, `source` (`tick_sim` | `profit_bridge`), `metrics`, `fill_count`.

#### `GET /replay/sessions` · `GET /replay/{job_id}`

List recent sessions or fetch fills for one job.

#### `POST /replay/training/run`

Scheduler/manual trigger — scans strategy store, runs parallel replays per `REPLAY_PARALLEL_WORKERS`.

#### Strategy store

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/strategy-store/scan` | POST | Index `*.ntsl` from export dirs + `PROFITCHART_STRATEGIES_DIR` |
| `/api/v1/strategy-store` | GET | List indexed strategies with extracted logic summary |
| `/api/v1/strategy-store/{id}` | GET | Full NTSL + `extracted_logic` JSON |

#### `GET /engine/mind`

Real-time motor state: `phase`, `sources`, `cycle_breakdown`, `resources` (RAM/GPU fractions, replay workers).

**Config:** see `.env.example` §10.0 (`REPLAY_TRAINING_*`, `STRATEGY_STORE_*`, `RESOURCE_RAM_FRACTION`).

#### Knowledge ingest (replay + NTSL)

| Endpoint | Purpose |
|----------|---------|
| `POST /knowledge/ingest/replays` | Index recent replay metrics into FTS |
| `POST /knowledge/ingest/strategies` | Index stored NTSL strategies |

#### B3 Excel history

`POST /archaeology/import/excel` — upload `.xlsx` trade history (requires `openpyxl`).

#### Self-healing

`GET /self-healing/breakers` — circuit breaker states (`replay_training`, etc.).

---

### 10.0.0 GA — Theory Deck + Decision Brief + Learning Rail

#### Decision brief + theory cards

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/ideas/{id}/brief` | POST | Build decision brief + conflict scan for confirm step |
| `GET /board/partials/ideas/{id}/confirm-step` | GET | Includes `decision_brief.html` + `theory_card_chips.html` |
| `GET /board/partials/symbol/{sym}/trade-product` | GET | Trade product thesis + theory chips from structure/tags |
| `GET /board/partials/symbol/{sym}` | GET | Symbol panel; theory chips when top idea has patterns |

Theory cards come from `build_theory_cards()` → FTS `search_chunks()` on `data/knowledge.db`.

#### Patch proposals + learning rail

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/v1/patches` | GET | Pending patch proposals |
| `POST /api/v1/patches/{id}/approve` | POST | Approve patch |
| `POST /api/v1/patches/{id}/reject` | POST | Reject patch |
| `GET /board/partials/learning-rail` | GET | Learning rail shell |
| `POST /board/partials/learning-rail/generate` | POST | Generate new patch proposals |
| `GET /board/partials/patches/{id}` | GET | Patch review card |
| `GET /board/partials/decision-queue` | GET | Pending decisions queue |

#### Graduation + health

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/graduation/{symbol}` | Paper graduation gates per symbol |
| `GET /api/v1/self-healing/health` | Degraded services snapshot |
| `GET /board/partials/watchlist` | `bb-grad` badge when gates pass |

`scripts/status_tick.py --json` adds `degraded`, `circuits`, `self_healing`.

#### Board partials (10.0 GA)

| Partial | Purpose |
|---------|---------|
| `GET /board/partials/engine-mind` | Motor phase + cycle breakdown (`M` shortcut) |
| `GET /board/partials/replay-player` | Visual replay canvas per symbol |
| `GET /board/partials/knowledge-library` | FTS search UI |
| `GET /board/partials/daily-briefing` | Morning briefing bullets |
| `GET /board/partials/strategy-store` | NTSL strategy index |
| `GET /board/partials/profitchart-companion` | ProfitChart sidecar stub |
| `GET /board/partials/degraded-banner` | Self-healing degraded chip (status bar) |
| `GET /board/partials/opportunity-rail` | Pair z-scores + scanner theory chips |

#### Layout presets

`BoardLayoutService.DEFAULT_PRESETS`: `scalp`, `structure`, `learn` (+ legacy `options_hedge`, `pairs`).

`POST /api/v1/board/layout/{preset}` · `GET /board/partials/layout-presets`

#### Knowledge bootstrap

`scripts/dev.py setup` calls `bootstrap_corpus_if_empty()` — ingests `docs/STRUCTURES.md` when corpus empty.

`profile_snapshot()` includes `knowledge_enabled` for `/ops/memory` and status tick.

### Release 14.0 — 3-tab cockpit (alpha/beta)

#### Tab metadata (A14.1)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/board/tabs` | `{ default_tab, tabs: [{id, label, route, partial}] }` |

#### PnL (A14.2–A14.4)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/pnl/intraday` | Today buckets `{ts, cumulative_brl, fees_brl}` + lane split CASH/WIN/OPT |
| `GET /api/v1/pnl/range?range=5d\|20d` | Multi-day cumulative buckets + lanes |
| `GET /api/v1/pnl/tab?range=today\|5d\|20d` | Full tab payload: `{ intraday, projection, risk, lanes, range_key }` |
| `GET /api/v1/pnl/projection` | Expectancy × remaining trades estimate (`model: expectancy_estimate`) |
| `GET /board/stream/pnl?range=today\|5d\|20d` | SSE `event: pnl` every 5s — same payload as tab build |

#### Journal tab

| Endpoint | Purpose |
|----------|---------|
| `GET /board/partials/journal-tab` | Full journal UI; query `range=today\|5d`, `symbol`, `setup_tag` |
| `GET /api/v1/journal/desk` | JSON desk; same filter query params |
| `PATCH /api/v1/trades/{id}/note` | Body `{ "note": "..." }` — journal note edit |
| `GET /board/partials/pnl-tab` | PnL tab partial (Worker styles in W14.5+) |


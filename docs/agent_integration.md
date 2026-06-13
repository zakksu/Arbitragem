# Agent A ↔ Agent B integration contract

## API surface (Agent A owns `src/api/routes.py`)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `GET /risk/summary` | Day P&L, loss limits, paper mode | Live Monitor |
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
| `GET /setup/status` | Integration wizard steps | W2.6 Settings / board |
| `POST /setup/test` | Probe Profit/Clear/BOVA | W2.6 test button |
| `GET /integrations/profit/test` | Includes `bova_chain` | Settings |

### 2.0 — coming (Supervisor builds, Worker wires)

| Endpoint | Purpose | UI consumer |
|----------|---------|-------------|
| `POST /backtest/run` (bridge) | Profit backtest job | W2.8 proof badge |
| `GET /symbols/{sym}/report` | AI symbol report card | W2.5 panel |
| `GET /stream/quotes` | SSE Core14 quotes | Watchlist live prices |
| `POST /risk/kill-switch` | Block all execution | Sidebar + board |
| `POST /ideas/{id}/execute` | Paper/live send | W2.4 confirm step 2 |

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

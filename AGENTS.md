# Agent instructions — Arbitragem Dashboard

**Current sprint:** [RELEASE_2.0.0.md](RELEASE_2.0.0.md) — **2.0-beta** (backtest pipeline + board polish).  
**Done:** 2.0-alpha (Core14 + blackboard shell).

## Two-agent workflow (always on)

Work **together** on the `Arbitragem` folder. Split by layer, not by “who’s free.”

| Agent | Role | Owns |
|-------|------|------|
| **Supervisor (Alpha)** | Backend, API, integrations, performance, `scripts/dev.py`, tests | `src/`, `scripts/`, `tests/`, `dashboard/api_cache.py` |
| **Worker** | Streamlit + HTMX blackboard UX | `dashboard/views/`, `dashboard/scanner_ui.py`, `dashboard/components/` (except `api_cache`), `src/web/` |

**Rules**
1. Start each response with **Joint plan** — who does what this turn.
2. Do **not** duplicate work (e.g. Worker does not rewrite `api_cache.py`).
3. After mutations, call `invalidate_cache()` from dashboard or `python scripts/dev.py restart --wait`.
4. Both agents run `python scripts/dev.py start --wait` before asking Filipe to test.

## Full developer autonomy

Agents must **run the stack themselves** using `scripts/dev.py`. Do not delegate setup to Filipe unless automation fails.

### Start everything (use this first)

```bash
python scripts/dev.py start --wait --json
```

Exit `0` = API + Streamlit healthy at http://localhost:8501  
**Blackboard (2.0):** http://localhost:8000/board

### Supervisor (backend) — **2.0-beta sprint**

```
A2.4a  POST /backtest/run on Profit bridge
A2.4b  CSV export folder watcher → TradeIdea.backtest_proof
A2.5a  Sector pair signals in scanner
A2.8   SSE /stream/quotes
A2.9   GET /symbols/{sym}/report
A2.10  Idea lifecycle + backtest gates
A2.6   Paper execute + Clear router + kill switch
```

### Worker (frontend) — **parallel, no blockers on W2.4/W2.6**

```
W2.4   Idea Stack confirm modal (HTMX → POST /ideas/{id}/confirm)
W2.6   Setup wizard UI (/setup/status)
W2.3   Board notes persist
W2.5   AI report panel (after A2.9)
W2.7   Sector strip + correlation map (after A2.5a)
```

Full split: [RELEASE_2.0.0.md §11](RELEASE_2.0.0.md)

- After API changes: `python scripts/dev.py restart --wait`
- Tests: `pytest tests/ -q`
- Logs: `logs/api.log`

### Worker (frontend)

- After UI changes: refresh http://localhost:8501 (Streamlit hot-reloads)
- If sidebar shows "API offline": `python scripts/dev.py restart --wait`
- Use `cached_get()` from `dashboard/api_cache.py` — never raw `api_get` on every rerun
- Blackboard: edit `src/web/templates/` + `blackboard.css`; test at http://localhost:8000/board
- Logs: `logs/dashboard.log`

### Filipe (beginner)

One command only:

```powershell
python scripts/dev.py start --wait --open
```

Then use the dashboard in the browser. Stop with `python scripts/dev.py stop`.

## Agent handoff

See [docs/agent_integration.md](docs/agent_integration.md) for the API contract between backend and frontend.

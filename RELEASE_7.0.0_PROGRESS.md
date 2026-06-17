# Release 7.0.0 — Progress Tracker

Scope: [RELEASE_7.0_LOCAL.md](RELEASE_7.0_LOCAL.md) · GA: [RELEASE_7.0.0.md](RELEASE_7.0.0.md)

**Version:** `7.0.0`

## 7.0-alpha — Golden path visible

- [x] `GOLDEN_PATH_MODE` env + `golden_path_mode` in `src/config.py`
- [x] PETR4-only scanner universe when golden path mode on
- [x] PETR4-only watchlist (no futures/crypto rows) when mode on
- [x] PETR4-only motor seed symbols when mode on
- [x] Golden path service — `src/services/golden_path.py` (7 checklist items + session persistence)
- [x] Golden path dashboard partial — `/board/partials/golden-path`
- [x] Ops panel v0 — `/board/partials/ops-panel` (RAM, motor ms, test badge)
- [x] Board wiring when `golden_path_mode` (banner + ops footer strip)
- [x] Staged HTMX delays (watchlist 80ms, ideas 250ms, desk 400ms) for fast first paint
- [x] `scripts/test_worker.py` + `data/.dev/test_status.json`
- [x] `dev.py start` spawns test worker (non-blocking) + `dev.py test-worker` subcommand
- [x] `status_tick.py --json` (api, motor, sleeves, test_status, golden_path, ram_mb)
- [x] Tests — `tests/test_golden_path_petr4.py`, `tests/test_golden_path_mode.py`
- [x] Quote cache TTL 1s in `profit_bridge.get_quotes_batch`
- [x] Trader desk SSE interval 30s in golden path mode
- [x] PETR4-only quote SSE default + 30s heartbeat when single symbol
- [ ] Board first paint < 800 ms (**manual verify**)
- [ ] Total stack RSS ≤ 1.2 GB with desk + motor (**manual verify**)

**Alpha exit:** Board loads with golden path checklist + ops strip; background tests non-blocking.

## 7.0-beta — Paper truth automated

- [x] PETR4 P&L reconciliation job — `src/services/pnl_reconcile.py` + scheduler every 5 min
- [x] `GET /api/v1/golden-path/reconcile`
- [x] Trust scorecard wired (5.2) — `src/services/trust_scorecard.py` → golden path item #7
- [x] Motor cycle timing + p95 — `ops_panel.motor_cycle_p95_ms`
- [x] Journal retention policy — `src/services/journal_maintenance.py` (30d hot, JSONL archive, nightly cron)
- [x] Streamlit slim mode — `STREAMLIT_SLIM_MODE` / auto with `GOLDEN_PATH_MODE`
- [x] `GET /api/v1/ops/memory`
- [ ] Golden path tests green in background loop 7 days (**operational**)
- [ ] 5 consecutive B3 sessions green on checklist (**manual + paper**)

## 7.0-rc — Symbol factory

- [x] Symbol factory backend — `src/services/symbol_factory.py`
- [x] `GET /api/v1/symbol-factory/status`
- [x] `POST /api/v1/symbol-factory/shadow` + `promote`
- [x] Factory blocked when test_status red, RAM > budget, or golden path not green
- [x] Shadow mode state in `data/symbol_factory.json`
- [x] `status_tick.py --json` includes `symbol_factory` + stack `ram_mb`
- [x] Symbol factory UI — `/board/partials/symbol-factory` + footer button (locked/unlocked)
- [x] Tests — `tests/test_symbol_factory.py` (API + partial 200)
- [ ] PRIO3 shadow checklist in production — **manual**

## 7.0 GA

- [x] `RELEASE_7.0.0.md` GA announcement + runbook
- [x] `scripts/ram_snapshot.py` → `data/.dev/ram_snapshot.json`
- [x] `scripts/golden_path_record_session.py` (dev session recording)
- [x] Ops panel reads stack RSS via psutil + snapshot
- [x] `psutil` in requirements.txt
- [x] Version bump `7.0.0` in `src/__init__.py`
- [x] Background test worker includes golden path + symbol factory tests
- [ ] Golden path green 5 sessions — **manual / paper**
- [ ] Factory proven with one shadow symbol — **manual**
- [ ] Background tests green 7 days — **operational**
- [ ] RAM budget met — **manual verify**
- [ ] Phase C gate paper criteria signed — **manual**

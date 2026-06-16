# Release 7.0.0 — Progress Tracker

Scope: [RELEASE_7.0_LOCAL.md](RELEASE_7.0_LOCAL.md)

## 7.0-alpha — Golden path visible

- [x] `GOLDEN_PATH_MODE` env + `golden_path_mode` in `src/config.py`
- [x] PETR4-only scanner universe when golden path mode on
- [x] PETR4-only watchlist (no futures/crypto rows) when mode on
- [x] PETR4-only motor seed symbols when mode on
- [x] Golden path service — `src/services/golden_path.py` (7 checklist items + session persistence)
- [x] Golden path dashboard partial — `/board/partials/golden-path`
- [x] Ops panel v0 — `/board/partials/ops-panel` (RAM, motor ms, test badge)
- [x] Board wiring when `golden_path_mode` (banner + ops footer strip)
- [x] `scripts/test_worker.py` + `data/.dev/test_status.json`
- [x] `dev.py start` spawns test worker (non-blocking) + `dev.py test-worker` subcommand
- [x] `status_tick.py --json` (api, motor, sleeves, test_status, golden_path, ram_mb)
- [x] Tests — `tests/test_golden_path_petr4.py`, `tests/test_golden_path_mode.py` (9/9 green)
- [x] Quote cache TTL 1s in `profit_bridge.get_quotes_batch`
- [x] Trader desk SSE interval 30s in golden path mode
- [ ] Board first paint < 800 ms (manual verify)
- [ ] Total stack RSS ≤ 1.2 GB with desk + motor (manual verify)

**Alpha exit:** Board loads with golden path checklist + ops strip; background tests non-blocking.

## 7.0-beta — Paper truth automated

- [ ] PETR4 P&L reconciliation job
- [ ] Trust scorecard wired (5.2)
- [ ] Golden path tests green in background loop 7 days
- [ ] Motor cycle timing + journal retention policy
- [ ] Streamlit slim mode

## 7.0-rc — Symbol factory

- [ ] Symbol factory UI (locked/unlocked)
- [ ] Shadow mode for 2nd symbol
- [ ] Factory blocked when test_status red or RAM > budget
- [ ] Docs + status_tick complete

## 7.0 GA

- [ ] Golden path green 5 sessions
- [ ] Factory proven with one shadow symbol
- [ ] Background tests green 7 days
- [ ] RAM budget met
- [ ] Phase C gate paper criteria signed

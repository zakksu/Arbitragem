# Release 4.0.0 — Progress tracker

**Sprint:** **4.3-alpha** autonomous + GA debt — **Supervisor: ALL COMPLETE**  
**Version:** `4.3.0-alpha`  
**Last updated:** 2026-06-16 (Supervisor close-out: DLL probe, WFO bridge-candle hook, autonomous ops in setup — **240 tests green**)

---

## Supervisor close-out (2026-06-16 — final)

| Item | Status |
|------|--------|
| All A4.x / A2.x GA-debt matrix items | ✅ shipped |
| `probe_dll_loadable()` + bridge health `dll_probe` | ✅ safe ctypes load without callbacks |
| `WALK_FORWARD_USE_BRIDGE_CANDLES` → `data_source: bridge_candles` in python BT | ✅ opt-in when bridge online |
| `GET /setup/status` → `autonomous_ops` + wizard step | ✅ |
| `docs/agent_integration.md` gaps → explicit blocked table | ✅ |
| Full `pytest tests/ -q` | ✅ (see test count below) |

### Blocked — cannot complete without external deps

| Item | Why blocked |
|------|-------------|
| ProfitDLL quote/order callbacks | Nelogica subscribe API + logged-in Profit session on Windows |
| Clear live Smart Trader execution | Real `CLEAR_API_*` credentials + `PAPER_TRADING_MODE=false` |
| Walk-forward tick-a-tick | ProfitChart tick export or DLL tick stream (bridge OHLC is interim only) |
| Worker W4.21–W4.22b | HTMX UI — Worker scope |

**Supervisor next trigger:** Worker ships W4.21–W4.22b → tag `4.2.0-beta`; or new 4.4 phase; or bug filed from Worker QA.

---

## 3.0.1 — polish ✅

- [x] All DoD items · version `3.0.1-alpha`

---

## 4.0-alpha — cockpit foundation ✅

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.1 | RiskProfile + `GET/PUT /risk/profile` | [x] |
| A4.2 | `GET /profit/pnl` + scheduler sync | [x] |
| A4.3 | Idea score 0–100 | [x] |
| A4.4 | `GET /watchlist/enriched` | [x] |
| A4.5 | `GET /ideas?symbol=` | [x] |
| A4.6 | `GET /market/clocks` | [x] |
| A4.7 | ProfitDLL detect + dev.py | [x] |

### Worker (W4.x)

| ID | Task | Status |
|----|------|--------|
| W4.1 | Risk drawer UI | [x] |
| W4.2 | Scalper header + KPI strip | [x] |
| W4.3 | Watchlist cols/sort/reset | [x] |
| W4.4 | World clocks row | [x] |
| W4.5 | Per-symbol idea stack | [x] |
| W4.6 | HelpTips watchlist + cockpit | [x] |

### Definition of done (4.0-alpha)

- [x] Risk Profile drawer persists defaults (R$ 500/day)
- [x] Watchlist: vol, cost, score columns + sort + reset
- [x] Profit P&L in header (stub or live DLL)
- [x] World clocks row with open/closed state
- [x] Idea stack filters by active symbol
- [x] Idea score on cards and watchlist
- [x] ProfitDLL detect script + wizard step
- [x] `tests/test_4_0_alpha.py` + API tests green

---

## 4.0-beta — Trade Product + pulse ✅ (backend)

### Supervisor (A4.x) — all shipped this phase

| ID | Task | Status |
|----|------|--------|
| A4.8 | Trade Product schema (`/symbols/{sym}/trade-product`) | [x] |
| A4.9 | Chart levels E/S/T on trade product | [x] |
| A4.10 | NTSL arm `POST /ntsl/arm` | [x] |
| A4.11 | Pulse rail `GET /pulse` | [x] |
| A4.12 | Replay lab `POST /replay/run` | [x] |
| A4.13 | Odds panel `GET /symbols/{sym}/odds` + journal/BT | [x] |

### Worker (W4.x)

| ID | Task | Status |
|----|------|--------|
| W4.7 | Trade Product blackboard template | [x] |
| W4.8 | Chart entry/stop/target overlays | [x] |
| W4.9 | Bottom pulse rail 33/33/33 | [x] |
| W4.10 | Builder → Arm NTSL flow | [x] |
| W4.11 | Replay lab UI | [x] |
| W4.12 | Odds panel widget (`odds.source` badge) | [x] |

### Definition of done (4.0-beta)

- [x] Trade Product API live for Core14
- [x] Chart E/S/T overlays verified in browser (W4.8)
- [x] One-click NTSL arm flow end-to-end (W4.10)
- [x] Bottom pulse rail 33/33/33
- [x] Replay lab v0 (sandbox API)
- [x] Odds panel shows `source` from journal/BT (W4.12)
- [x] Version `4.0.0-beta`; pytest green (152)

### Perf (alpha carry-over)

- [x] Watchlist enrich ATR cache (30s TTL) + skip candle fetch when bridge offline

---

## 4.0-rc — complete ✅

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.14 | KPI history + `avg_slippage_ticks` | [x] |
| A4.15 | Profit co-start in `dev.py` | [x] |
| A4.16 | Paper slippage on confirm payload | [x] |
| A4.17 | Education pack `data/education/` | [x] |

### Worker (W4.x) — parallel with Supervisor

| ID | Task | Status |
|----|------|--------|
| W4.13 | KPI date-range chips (today/5d/20d/YTD) | [x] wired `GET /kpi/history` |
| W4.14 | Keyboard shortcuts + footer hints | [x] S/K/1-9/R/Enter |
| W4.15 | Layout presets v2 (Scalp/Structure/Learn) | [x] Learn hides idea stack |
| W4.16 | First-run tour (optional) | [x] 5-step overlay |
| W4.17 | Full HelpTip coverage sections 0–10 | [x] `docs/tooltips/*.json` |

### Definition of done (4.0-rc)

- [x] KPI history filters wired to `GET /kpi/history`
- [x] Education copy on Trade Product / structures
- [x] Keyboard shortcuts documented + working
- [x] Layout presets v2
- [x] Profit co-start optional in dev.py
- [x] Paper realism on confirm modal (A4.16 live preview)
- [x] Version `4.0.0-rc`; pytest green

---

## 4.0.0 GA — complete ✅

### Worker (W4.x)

| ID | Task | Status |
|----|------|--------|
| W4.18 | GA polish — performance empty states, mobile banner, pulse education | [x] |

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.18 | Paper validation API + journal export | [x] |
| A4.19 | Docs `SCALPER_COCKPIT.md` + README 4.0 | [x] |

### Definition of done (4.0.0 GA)

- [x] Paper week gate — `GET /paper/validation` + `scripts/paper_validation.py`
- [x] Journal export — `GET/POST /paper/journal/export`
- [x] Performance empty state + board mobile risk banner (W4.18)
- [x] Pulse lesson shows daily axiom + PT term + axioms count
- [x] Tag **v4.0.0** (version `4.0.0`)
- [x] Full HelpTips sections 0–10
- [x] pytest green

---

## Parallel split — active protocol

**Rule:** When Supervisor picks **A4.x**, Worker starts mapped **W4.x** same sprint turn.

| Phase | Supervisor (backend) | Worker (HTMX/UI) | Status |
|-------|---------------------|------------------|--------|
| 3.0.1 | DD, P&L truth, DLL detect | Chart, header, HelpTips | ✅ |
| 4.0-alpha | A4.1–A4.7 APIs | W4.1–W4.6 cockpit | ✅ |
| 4.0-beta | A4.8–A4.13 Trade Product + pulse | W4.7–W4.12 blackboard | ✅ |
| 4.0-rc | A4.14–A4.17 history + education | W4.13–W4.17 shortcuts + KPI chips | ✅ |
| 4.0.0 GA | A4.18–A4.19 paper gate + docs | W4.18 mobile + empty states | ✅ |
| **4.1** | **A4.20 WIN/WDO quotes · A4.21 RSS/Twitter signals** | **W4.19 futures styling · W4.20 pulse social chips** | **✅** |
| **4.2** | **A4.22–A4.24 archaeology + crypto + paper** | **W4.21 timeline · W4.22 crypto UI** | **✅** |

---

## 4.1 — futures + social (backend ✅)

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.20 | WIN/WDO universe + quotes in watchlist API | [x] |
| A4.21 | Twitter/RSS ingest → read-only `Signal` cards | [x] |

### Worker (W4.x) — parallel with Supervisor

| ID | Task | Status |
|----|------|--------|
| W4.19 | Futures row styling + session badges | [x] |
| W4.20 | Social signal chips on pulse rail (news third) | [x] |

### Definition of done (4.1)

- [x] WIN/WDO in enriched watchlist with session badges (A4.20 API)
- [x] RSS/Twitter signals API (read-only, no auto-trade)
- [x] Pulse rail news column shows social chips from API (W4.20)
- [x] pytest green; version `4.1.0-alpha`

---

## 4.2 — crypto + archaeology (backend ✅)

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.22 | Profit CSV history import → `GET /archaeology/timeline` | [x] |
| A4.23 | Binance quote adapter (BTC/ETH/SOL) in watchlist | [x] |
| A4.24 | Crypto paper stub executor | [x] |

### Worker (W4.x) — parallel with Supervisor

| ID | Task | Status |
|----|------|--------|
| W4.21 | History timeline UI | [x] wire `GET /archaeology/timeline` |
| W4.22 | Crypto watchlist section (read-only) | [x] wire `crypto[]` from enriched watchlist |

### Definition of done (4.2)

- [x] BTC/ETH/SOL in enriched watchlist (`crypto_count`, read-only flags)
- [x] Archaeology CSV import + timeline API
- [x] Board UI for timeline + crypto rows (W4.21/W4.22)
- [x] pytest green; version `4.2.0-alpha`

---

## 4.2+ follow-on (backlog)

---

## 4.3 — Autonomous Engine + Strategy Lab (in progress)

### Supervisor (A4.x)

| ID | Task | Status |
|----|------|--------|
| A4.25 | `src/autonomous/` engine, scheduler, optimizer, risk guardian | [x] |
| A4.26 | `BacktestRanking` model + `backtest_rankings` service | [x] |
| A4.27 | `GET/POST /api/v1/backtest/rankings` + sync + promote | [x] |
| A4.28 | Nightly WFO → rankings auto-sync in scheduler | [x] |
| A4.29 | `POST /api/v1/autonomous/run` daily routine | [x] |
| A4.30 | Ollama strategist commentary on ranking detail | [x] |

### Worker (W4.x)

| ID | Task | Status |
|----|------|--------|
| W4.23 | Strategy Lab page `/board/strategy-lab` | [x] |
| W4.24 | Sortable rankings table + filters (HTMX) | [x] |
| W4.25 | Row detail — equity curve, folds, promote button | [x] |
| W4.26 | Sidebar link + status bar Strategy Lab | [x] |

### Definition of done (4.3)

- [x] Autonomous folder structure + background scheduler hooks
- [x] Rankings SQLite table + API
- [x] Strategy Lab UI with Lightweight Charts equity
- [x] Promote to Idea Stack from lab
- [x] `tests/autonomous/` green (4 passed)
- [x] Version bump `4.3.0-alpha`

---

## Sprint split — 4.2 close-out + next lanes (2026-06-16)

**Rule:** Supervisor ships API contract first; Worker wires HTMX in the **same sprint** (no waiting once contract is in `docs/agent_integration.md`).

### Lane A — 4.2 close-out (this week)

| Owner | ID | Task | Depends on | Status |
|-------|-----|------|------------|--------|
| **Supervisor** | A4.22–24 | Archaeology + crypto quotes + paper stub | — | ✅ done |
| **Supervisor** | A4.25a | `build_enriched_watchlist()` shared service | A4.23 | ✅ done |
| **Worker** | W4.21 | Archaeology timeline partial + import/scan buttons | `GET /archaeology/timeline` | [x] |
| **Worker** | W4.22 | Crypto watchlist section + paper preview button | `crypto[]`, `POST /paper/crypto/*` | [x] |
| **Worker** | W4.22b | Board watchlist → `build_enriched_watchlist()` (drop stale `_enriched_watchlist_sync`) | A4.25a | [x] |

**4.2 DoD:** board shows BTC/ETH/SOL + archaeology timeline; pytest green; tag `4.2.0-beta` when W lane ships.

### Lane B — 4.3 CEI + insights (Supervisor ✅)

| Owner | ID | Task | Status |
|-------|-----|------|--------|
| **Supervisor** | A4.25–30 | Autonomous engine + rankings | ✅ |
| **Supervisor** | A4.31 | CEI export parser `POST /cei/parse` | ✅ |
| **Supervisor** | A4.32 | Archaeology insights `GET /archaeology/symbol/{sym}/insights` | ✅ |
| **Worker** | W4.23–26 | Strategy Lab UI | ✅ |

### Lane C — 2.0 GA debt (Supervisor ✅)

| Owner | ID | Task | Status |
|-------|-----|------|--------|
| **Supervisor** | A2.5b | VWAP reclaim in scanner + `GET /symbols/{sym}/session-vwap` | ✅ |
| **Supervisor** | A2.10 | `GET /ideas/{id}/gates` + gates on confirm/execute | ✅ |
| **Supervisor** | A2.6b | `GET /execution/clear/status` + Clear journal sync on execute | ✅ |
| **Supervisor** | A4.31b | `POST /cei/import` (DB persist) | ✅ |

### Handoff — Worker `W4.22b`

Replace `src/web/router.py` `_enriched_watchlist_sync` with:

```python
from src.services.enriched_watchlist import build_enriched_watchlist
rows = (await _to_thread(_with_db, build_enriched_watchlist))["symbols"]
```

Ensures board watchlist includes **futures + crypto** without duplicating Supervisor logic.

---

## Supervisor idle — handoff to Worker (2026-06-16)

**Status:** **Supervisor: ALL COMPLETE** at `4.3.0-alpha` · pytest green (verified close-out session).

### Session 2026-06-16 (Supervisor close-out)

| Item | Status |
|------|--------|
| `probe_dll_loadable()` — ctypes load probe without Nelogica callbacks | ✅ |
| `profit_dll_bridge.py` health exposes `dll_probe` + `callbacks_wired: false` | ✅ |
| `WALK_FORWARD_USE_BRIDGE_CANDLES` opt-in bridge OHLC for python backtest/WFO | ✅ |
| `GET /setup/status` autonomous_ops block + wizard step | ✅ |
| `docs/agent_integration.md` — blocked vs stub table | ✅ |

### Session 2026-06-16 (Supervisor polish — earlier)

| Item | Status |
|------|--------|
| `tests/conftest.py` — force `BOARD_AUTH_ENABLED=false` in CI (fixes 34 board 401s when `.env` tunnel auth on) | ✅ |
| `test_watchlist_atr_cache` — `PAPER_TRADING_MODE=false` for bridge candle path | ✅ |
| Pulse partial tests → `pulse-rail-legacy` (contract: `/pulse-rail` aliases trader desk) | ✅ |
| Rankings promote gate — PF/DD check before `POST /backtest/rankings/{id}/promote` (400 on fail) | ✅ |
| `docs/agent_integration.md` — pulse-rail / trader-desk / legacy routing | ✅ |

### Completed Supervisor scope (all phases)

| Phase | IDs | Notes |
|-------|-----|-------|
| 3.0.1 | A0.6 | Version bump |
| 4.0-alpha | A4.1–A4.7 | Risk, P&L, watchlist, clocks, DLL detect |
| 4.0-beta | A4.8–A4.13 | Trade Product, pulse, replay, odds |
| 4.0-rc | A4.14–A4.17 | KPI history, education, paper slippage |
| 4.0 GA | A4.18–A4.19 | Paper validation + docs |
| 4.1 | A4.20–A4.21 | WIN/WDO quotes + social signals |
| 4.2 | A4.22–A4.24, A4.25a | Archaeology, crypto, paper stub, shared watchlist |
| 4.3 | A4.25–A4.32 | Autonomous engine, rankings, CEI, insights |
| 2.0 GA debt | A2.5b, A2.10, A2.6b, A4.31b | VWAP, gates, Clear journal sync, CEI import |

### Open Worker items (blocks 4.2-beta tag)

**All shipped** — tag `4.2.0-beta` ready when Supervisor bumps version.

| ID | Task | API ready |
|----|------|-----------|
| W4.21 | Archaeology timeline + import/scan buttons | ✅ |
| W4.22 | Crypto watchlist section + paper preview | ✅ |
| W4.22b | Board → `build_enriched_watchlist()` | ✅ |

### Code TODOs (backlog — blocked on external deps)

| Location | Item | Trigger |
|----------|------|---------|
| `scripts/profit_dll_bridge.py` | Nelogica login/subscribe callbacks after `probe_dll_loadable()` | Windows DLL + logged-in Profit |
| ~~`src/services/ntsl_arm.py`~~ | ~~Wire legs from structure builder~~ | **Done** — `legs[]` + `TradeIdeaService._legs_for_structure` fallback |
| `docs/agent_integration.md` §gaps | Clear API live, tick-a-tick WFO | Live Clear credentials / Profit tick feed |
| `src/web/router.py` | W4.22b enriched watchlist swap | **Worker** — not Supervisor |

### What triggers next Supervisor work

1. **Worker ships W4.21–W4.22b** → tag `4.2.0-beta`; Supervisor idle unless bugs filed.
2. **New release phase** (e.g. 4.4) scoped in `RELEASE_4.0.0.md` §6.
3. **Integration blockers:** ProfitDLL ctypes on Windows, Clear live router hardening, real tick walk-forward.
4. **Bug/regression** from Worker QA on shipped APIs (gates, VWAP, archaeology, crypto paper).
5. **Autonomous ops:** tune nightly WFO sync, Ollama strategist prompts, ranking promote rules.

**Next action:** Worker picks **W4.22b** (quick win — swap `_enriched_watchlist_sync`) then **W4.21 + W4.22** for 4.2-beta DoD.

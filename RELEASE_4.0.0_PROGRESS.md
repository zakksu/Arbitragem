# Release 4.0.0 — Progress tracker

**Sprint:** 4.0.0 GA — **complete**  
**Last updated:** 2026-06-16

---

## 3.0.1 — polish

- [x] All DoD items (see prior commits)

---

## 4.0-alpha — cockpit foundation

| ID | Task | Status |
|----|------|--------|
| A4.1 | RiskProfile + GET/PUT `/api/v1/risk/profile` | **done** |
| A4.2 | GET `/api/v1/profit/pnl` | **done** |
| A4.3 | Idea score service | **done** |
| A4.4 | Watchlist enrich API | **done** |
| A4.5 | Per-symbol ideas filter | **done** |
| A4.6 | GET `/api/v1/market/clocks` | **done** |
| A4.7 | ProfitDLL detect + dev.py hook | **done** |
| W4.1 | Risk drawer UI | **done** |
| W4.2 | Scalper header + KPI strip | **done** |
| W4.3 | Watchlist cols/sort | **done** |
| W4.4 | World clocks row | **done** |
| W4.5 | Per-symbol idea stack | **done** |
| W4.6 | HelpTips on watchlist + cockpit | **done** |

### Definition of done (4.0-alpha)

- [x] Risk Profile drawer persists defaults (R$ 500/day)
- [x] Watchlist: vol, cost, score columns + sort + reset
- [x] Profit P&L in header (stub or live DLL)
- [x] World clocks row with open/closed state
- [x] Idea stack filters by active symbol
- [x] Idea score on cards and watchlist
- [x] ProfitDLL detect script + wizard step
- [x] Version `4.0.0-alpha`; `tests/test_4_0_alpha.py`

---

## 4.0-beta — Trade Product + pulse

| ID | Task | Status |
|----|------|--------|
| A4.8 | Trade Product schema | **done** |
| A4.9 | Chart levels E/S/T | **done** |
| A4.10 | NTSL one-click arm | **done** |
| A4.11 | Pulse rail feeds | **done** |
| A4.12 | Replay lab API v0 | **done** |
| W4.7 | Trade Product blackboard | **done** |
| W4.8 | Chart overlays | **done** |
| W4.9 | Bottom pulse rail 33/33/33 | **done** |
| W4.10 | Arm NTSL flow | **done** |
| W4.11 | Replay lab stub script | **done** |

### Definition of done (4.0-beta)

- [x] Trade Product blackboard template live for Core14
- [x] Chart entry/stop/target overlays
- [x] One-click NTSL arm flow
- [x] Bottom pulse rail 33/33/33
- [x] Replay lab v0 (sandbox)
- [x] Version `4.0.0-beta`

---

## 4.0-rc — history + habits

| ID | Task | Status |
|----|------|--------|
| A4.14 | KPI history service | **done** |
| A4.15 | Profit co-start in dev.py | **done** |
| A4.17 | Education axioms pack | **done** |
| W4.13 | KPI date-range chips | **done** |
| W4.14 | Keyboard shortcuts | **done** |
| W4.17 | HelpTip coverage expanded | **done** |

### Definition of done (4.0-rc)

- [x] KPI history filters (today / 5d / 20d / 3mo)
- [x] Education copy on structures
- [x] Keyboard shortcuts documented + working
- [x] Profit co-start optional
- [x] Version `4.0.0-rc`

---

## 4.0.0 — GA

| ID | Task | Status |
|----|------|--------|
| A4.18 | Paper validation script | **done** |
| A4.19 | Docs README + SCALPER_COCKPIT | **done** |
| Both | Tag v4.0.0 | **done** |

### Definition of done (4.0.0 GA)

- [x] Paper validation script shipped
- [x] `docs/SCALPER_COCKPIT.md` + README 4.0
- [x] Tag **v4.0.0**
- [x] Version `4.0.0`
- [x] pytest green (130+)
- [x] Kill switch + risk gates with Profit stub

---

## 4.1 / 4.2 / 4.3 (follow-on — not GA)

- [ ] 4.1: WIN/WDO quotes + RSS/Twitter read-only
- [ ] 4.2: Trade archaeology + BTC/ETH/SOL watchlist
- [ ] 4.3: B3 CEI research import spike

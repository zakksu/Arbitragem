# Release 4.0.0 — Progress tracker

**Sprint:** 4.0-beta **complete** → next: 4.0-rc  
**Version:** `4.0.0-beta`  
**Last updated:** 2026-06-16

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

## 4.0-rc — in progress

| A4.14 | KPI history | [x] stub shipped early |
| A4.15 | Profit co-start | [ ] |
| A4.16 | Paper slippage on confirm | [ ] |
| A4.17 | Education pack | [ ] partial (`data/education/`) |

---

## 4.0.0 GA — not started

- [ ] Paper week #3 signed off
- [ ] Tag **v4.0.0**
- [ ] Full HelpTips sections 0–10

---

## 4.1+ follow-on

- [ ] WIN/WDO quotes + RSS read-only
- [ ] Trade archaeology + crypto watchlist
- [ ] B3 CEI research spike

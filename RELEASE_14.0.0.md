# Release 14.0.0 — Hybrid Cockpit UI + Journal Desk + Live PnL

**Version target:** `14.0.0`  
**Prerequisite:** [RELEASE_13.0.0.md](RELEASE_13.0.0.md) (Core5, Live Radar, journal API)  
**Design north star:** [RELEASE_11.0_SCOPE.md § Hybrid Cockpit](docs/RELEASE_11.0_SCOPE.md) (approved mockup merge)

---

## Problem (today)

| Issue | Evidence |
|-------|----------|
| Journal crushes the trading surface | 200-row blotter under Live Radar on main `/board` |
| Hybrid layout incomplete | 3-column desk exists; learning rail / strategy lab only in golden mode |
| PnL is numbers only | Status bar shows R$ day P&L; no intraday curve or projection |
| Cognitive split | Trading = “now”; journaling = “review” — should be separate tabs |

**Decision:** Keep **Desk** tab lean (Radar + watchlist + ideas + mind). Move **Journal** to its own tab with charts. Add **PnL** tab mirroring prop-desk dashboards (SMB / bank blotter).

---

## Information architecture (two surfaces)

```
┌─────────────────────────────────────────────────────────────────┐
│  [ DESK ]  [ JOURNAL ]  [ PnL ]     status bar (unchanged)      │
├─────────────────────────────────────────────────────────────────┤
│  DESK (default) — Hybrid Cockpit                                │
│  • Live Radar (always)                                          │
│  • 3-col: Watchlist | Symbol + Trade product | Idea stack       │
│  • Collapsible: Strategy Lab strip · Engine Mind footer           │
├─────────────────────────────────────────────────────────────────┤
│  JOURNAL — prop desk review                                     │
│  • Blotter + grades + motor log + WIN archaeology               │
│  • Filters: today / 5D / symbol / setup tag                     │
│  • Export CSV (existing API)                                    │
├─────────────────────────────────────────────────────────────────┤
│  PnL — real-time performance                                    │
│  • Intraday equity curve (SSE, 5s)                              │
│  • Day P&L vs stop-loss budget                                  │
│  • Projection cone (expectancy × time left in session)          │
│  • Lane split: CASH / WIN / OPT                                 │
└─────────────────────────────────────────────────────────────────┘
```

URL pattern (HTMX tabs, no SPA framework):

| Tab | Route | Partial |
|-----|-------|---------|
| Desk | `/board` | `board.html` (trimmed) |
| Journal | `/board?tab=journal` | `partials/journal_tab.html` |
| PnL | `/board?tab=pnl` | `partials/pnl_tab.html` |

Tab state in `sessionStorage` + query param for deep links.

---

## Visual direction (attractive remodel)

Borrow from approved hybrid + modern prop terminals:

| Element | Treatment |
|---------|-----------|
| **Tab bar** | Pill nav under status bar; active tab accent `#3dd68c` |
| **Cards** | `bb-glass` panels — subtle border, 8px radius, no heavy tables on Desk |
| **Charts** | Lightweight SVG sparklines on Desk status; full charts on PnL tab |
| **Typography** | Mono for prices/qty; tabular nums; larger hero PnL on PnL tab |
| **Density** | Desk = medium; Journal = high (tables OK); PnL = chart-first |
| **Motion** | PnL line animates on SSE tick; radar lamps unchanged |

CSS: new `blackboard_14_0.css` — do not bloat `blackboard.css`.

---

## Backend (minimal new surface)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/pnl/intraday` | Buckets: `{ts, cumulative_brl, fees_brl}` from `Trade` today |
| `GET /api/v1/pnl/projection` | `{expectancy_brl, session_remaining_min, projected_eod_low/high}` |
| `GET /board/stream/pnl` | SSE — push intraday series every 5s (mirror trader-desk SSE) |
| `GET /board/partials/journal-tab` | Full journal layout (move from inline slot) |
| `GET /board/partials/pnl-tab` | Charts + status cards |

Reuse: `trade_journal_desk.py`, `pnl_truth.py`, `kpi_history.py`, `risk_cockpit.py`.

**Projection math (simple, honest):**

```
expectancy = journal_desk.summary.expectancy_brl  # trailing 30d
remaining_trades_est = (session_minutes_left / avg_trade_cycle_min)
projected_eod = day_pnl + expectancy * remaining_trades_est
band_low/high = projected_eod ± (daily_volatility_est)
```

No ML — label as “model estimate” in UI.

---

## Phased ship plan

### 14.0-alpha — Tab shell + journal move (3–4 days)

| ID | Owner | Deliverable |
|----|-------|-------------|
| W14.1 | Worker | Tab bar component + `?tab=` routing in `board.html` |
| W14.2 | Worker | Remove `#trade-journal-slot` from Desk; load only on Journal tab |
| W14.3 | Worker | `journal_tab.html` — full-width blotter + archaeology hero |
| W14.4 | Worker | `blackboard_14_0.css` — tab + glass cards |
| A14.1 | Backend | `board_layout.py` — tab metadata for presets |

**Exit:** Desk screenshot fits in one viewport without scrolling past radar.

### 14.0-beta — Live PnL tab (4–5 days)

| ID | Owner | Deliverable |
|----|-------|-------------|
| A14.2 | Backend | `pnl_intraday.py` — aggregate today's fills into minute buckets |
| A14.3 | Backend | `GET /pnl/intraday` + `GET /pnl/projection` |
| A14.4 | Backend | `GET /board/stream/pnl` SSE |
| W14.5 | Worker | `pnl_tab.html` — hero day P&L + SVG/canvas intraday chart |
| W14.6 | Worker | Stop-loss budget line on chart (from risk profile) |
| W14.7 | Worker | Lane chips: CASH / WIN / OPT contribution bars |

**Exit:** PnL tab updates within 5s of paper fill without full page reload.

### 14.0-rc — Hybrid cockpit polish (3–4 days)

| ID | Owner | Deliverable |
|----|-------|-------------|
| W14.8 | Worker | Default hybrid: Strategy Lab collapsible strip (Core5 NTSL) |
| W14.9 | Worker | Learning rail thin strip (patches + briefing spark) — not golden-only |
| W14.10 | Worker | Engine Mind footer always on Desk (compact) |
| W14.11 | Worker | Layout presets: `default | archaeology | learn` (from 11.0 spec) |
| W14.12 | Worker | Desk status bar mini sparkline (today PnL trend) |

**Exit:** Matches hybrid ASCII diagram in RELEASE_11.0_SCOPE §125.

### 14.0-GA — Journal pro features + mobile (2–3 days)

| ID | Owner | Deliverable |
|----|-------|-------------|
| W14.13 | Worker | Journal filters + per-trade note edit (`PATCH /trades/{id}/note`) |
| W14.14 | Worker | Mobile: Journal tab readable; Desk stays 3-col scroll |
| W14.15 | Worker | PnL tab: 5D / 20D range toggle (uses `kpi_history`) |
| A14.5 | Backend | Version `14.0.0`, tests, tag `v14.0.0` |

---

## What we keep from 13.0 on Desk

| Stay on Desk | Move off Desk |
|--------------|---------------|
| Live Radar | Trade journal table |
| Watchlist / symbol / ideas | WIN archaeology wall |
| Trade product + confirm | Motor log details |
| Outbox copy hint | CSV export button → Journal tab |

---

## Tests

```powershell
pytest tests/test_14_0_ui.py -q   # tab routes, journal not on desk
pytest tests/test_pnl_intraday.py -q
```

---

## Timeline

```
Week 1   14.0-alpha   Tabs + journal move + CSS shell
Week 2   14.0-beta    PnL intraday SSE + chart tab
Week 3   14.0-rc      Hybrid polish (strategy lab, learning rail, mind)
Week 4   14.0-GA      Journal filters, mobile, tag v14.0.0
```

---

## Immediate UX win (before 14.0-alpha ships)

Temporary: hide journal on Desk via CSS or remove HTMX trigger — **optional hotfix** if Filipe wants cleaner board today.

---

## Related

- [RELEASE_11.0_SCOPE.md](docs/RELEASE_11.0_SCOPE.md) — Hybrid Cockpit ASCII + mockup merge
- [RELEASE_13.0.0.md](RELEASE_13.0.0.md) — `trade_journal_desk.py`, export API
- `src/services/kpi_history.py` — historical PnL buckets for 5D/20D charts

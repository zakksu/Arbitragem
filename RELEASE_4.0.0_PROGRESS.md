# Release 4.0.0 — Progress tracker

**Sprint:** 3.0.1 polish — **complete** → next: 4.0-alpha  
**Last updated:** 2026-06-16

---

## 3.0.1 — polish

| ID | Owner | Task | Status |
|----|-------|------|--------|
| A0.1 | Worker | DD display when `max_drawdown_pct` missing | **done** |
| A0.2 | Worker | Dedupe header KPIs (single status strip) | **done** |
| A0.3 | Worker | HelpTip skeleton + premium bubble CSS | **done** |
| A0.4 | Worker | Chart load — deferred LW Charts after HTMX swap | **done** |
| A0.5 | Worker | Builder button label/CSS (`Create Idea`, nowrap) | **done** |
| A0.6 | Supervisor | Version bump + tests | **done** |

### Definition of done (3.0.1)

- [x] DD shows `—` when `max_drawdown_pct` absent (not 100%)
- [x] Session chart renders after symbol click (LW Charts + `bbMountSymbolChart`)
- [x] Header: no duplicate Day P&L (`risk-cockpit-wrap` removed from board)
- [x] HelpTip partial on ≥3 controls (status, watchlist, ideas, chart, builder, toolbar)
- [x] Version `3.0.1-alpha`; tests green (Supervisor A0.6)

---

## 4.0-alpha — ready to start

3.0.1 DoD complete. Begin A4.x / W4.x per RELEASE_4.0.0.md §6.

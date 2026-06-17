# Scalper Cockpit — operator guide (4.0 GA)

## Daily flow

1. `python scripts/dev.py start --wait`
2. Open http://localhost:8000/board
3. Check world clocks (B3 / NY / LON / TOK / SHA) and Day P&L source (`profit` or `journal`)
4. Sort watchlist by **Score** — click symbol for Trade Product + chart E/S/T
5. Confirm ideas (paper default) — Risk drawer if limits change

## Risk profile (section 0.1)

- Default max daily loss: **R$ 500**
- Board toolbar → **Risk** → edit → Save
- API: `GET/PUT /api/v1/risk/profile`

## Trade Product (4.0-beta)

Tabs: **Thesis** | **Chart** | **Legs** | **Notes**  
**Arm NTSL** writes to `exports/ntsl/` for ProfitChart load.

## Pulse rail

Bottom row: news stub | economic calendar stub | rotating axioms from `data/education/axioms.json`.

## Replay lab (sandbox only)

```bash
python scripts/replay_lab_stub.py --symbol PETR4 --speed 10
```

Never routes to live broker — `mode: sandbox` only.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| S | Scan |
| K | Kill switch |
| 1-9 | Focus watchlist row |
| Enter | Confirm top idea |
| R | Refresh watchlist |

## KPI history chips

Status bar: Today · 5D · 20D · 3mo — `GET /api/v1/kpi/history?range=5d`

## Paper week gate (4.0 GA)

**CLI:**
```bash
python scripts/paper_validation.py
python scripts/paper_validation.py --export csv
```

**API (Worker W4.18):**
- `GET /api/v1/paper/validation` — checklist + `gate_pass`
- `GET /api/v1/paper/journal/export?format=json|csv|file`
- `POST /api/v1/paper/journal/export` — writes `exports/journal/paper_journal_*.csv`

Gate: **10+** structure confirms, **3+** Trade Products with rationale. Exit code `0` = pass, `2` = not ready for live.

## Mobile / GA polish

- Board is desktop-first; narrow view shows mobile banner (Worker W4.18)
- Empty states: watchlist with no scan, idea stack with no symbol selected

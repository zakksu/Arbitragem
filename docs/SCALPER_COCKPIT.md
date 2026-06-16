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

## Paper week gate

```bash
python scripts/paper_validation.py
```

Target: 10+ structure confirms, 3+ journaled Trade Products before live.

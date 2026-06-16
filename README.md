# Arbitragem Scalper — Structure Deck (4.0)

Profit-native B3 options scalping cockpit: ranked Core14 watchlist, Trade Product blackboard, Profit P&L truth, risk profile drawer, world clocks, and education pulse rail.

## Quick start

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/dev.py start --wait --open
```

| UI | URL |
|----|-----|
| **Blackboard (primary)** | http://localhost:8000/board |
| Streamlit admin | http://localhost:8501 |
| API | http://localhost:8000/api/v1/health |

## 4.0 highlights

- **Risk profile** — R$500/day default, editable via Risk drawer (`GET/PUT /api/v1/risk/profile`)
- **Profit P&L** — `GET /api/v1/profit/pnl` (journal > Profit bridge > paper stub)
- **Idea score** — 0–100 on watchlist and idea stack
- **Trade Product** — Thesis | Chart | Legs | Notes tabs per symbol
- **Pulse rail** — 33% news / calendar / lessons
- **Replay lab** — sandbox via `POST /api/v1/replay/run` or `scripts/replay_lab_stub.py`
- **Keyboard** — `S` scan, `K` kill, `1-9` watchlist, `R` refresh

## Paper validation (GA gate)

```bash
python scripts/paper_validation.py
```

## ProfitDLL detection

```bash
python scripts/detect_profit_dll.py
```

Optional `.env`: `PROFITCHART_EXE=C:\path\to\ProfitChart.exe` for co-start with `dev.py`.

## Docs

- [RELEASE_4.0.0.md](RELEASE_4.0.0.md) — scope
- [docs/SCALPER_COCKPIT.md](docs/SCALPER_COCKPIT.md) — operator guide

**Version:** 4.0.0 · Paper default · No Clear API

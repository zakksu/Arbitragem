# Release 11.0 — Archaeology Mastery & Core17 Options

**Prerequisite:** [RELEASE_10.0.0.md](RELEASE_10.0.0.md) (GA)  
**Codename:** Live Memory / Strategy Forge  
**Board mockups:** `assets/mockup_11_0_*.png` (5 concepts)

---

## Executive summary

Filipe’s **9,770-row B3 history** (Feb 2021 → Oct 2025) is mostly **index futures** (WIN/WDO ~86%) with meaningful **cash equities** (1,120 rows) and **273 option legs**. Release 11.0 turns that file into **actionable archaeology**, ships a **50-strategy NTSL options pack** for **Core17**, and proposes **five board redesigns** toward a post-golden-path cockpit.

---

## What we did immediately (this drop)

| Deliverable | Location |
|-------------|----------|
| B3 CEI Excel column mapping | `src/integrations/profit_parser.py` (`valor` → signed cash flow) |
| Import CLI | `scripts/import_filipe_b3_history.py` |
| History preview JSON | `data/.dev/b3_history_preview.json` |
| Core17 universe | `data/filipe_core17.csv` (+14 Core14 + BOVA11, RADL3, MGLU3) |
| Options templates per underlying | `data/core17_options.csv` |
| 50 NTSL option stubs | `strategies/ntsl/core14_options/` via `scripts/generate_core14_ntsl_pack.py` |
| Board redesign mockups (5) | `assets/mockup_11_0_*.png` |
| Tests | `tests/test_b3_history_import.py` |

### Your history — quick facts

| Metric | Value |
|--------|-------|
| Rows | 9,770 |
| Date range | 01/02/2021 – 31/10/2025 |
| Unique tickers | 214 |
| Futures (WIN/WDO) | ~8,371 rows |
| Cash à vista | 1,120 rows |
| Options | 273 rows |
| Top cash names | VALE3, JBSS3, MGLU3, WEGE3, ITUB4 |
| Core14 overlap | VALE3 (225), ITUB4 (60), PETR4 (38) |

**Import command:**

```powershell
python scripts/import_filipe_b3_history.py "c:\Users\godin\Downloads\historico b3 full.xlsx"
python scripts/generate_core14_ntsl_pack.py
python scripts/dev.py restart --wait
# Board → Strategy Store → Scan
```

Insights land in `data/.dev/b3_history_insights.json` (per-symbol archaeology + Core17 rollup).

---

## Five board redesign concepts

| # | Mockup | Idea |
|---|--------|------|
| 1 | `mockup_11_0_command_center.png` | **Command Center** — classic 3-column: watchlist / chart+legs / idea stack + engine mind |
| 2 | `mockup_11_0_learning_rail.png` | **Learning-first** — patches + briefing charts + archaeology timeline hero |
| 3 | `mockup_11_0_golden_mobile.png` | **Golden mobile** — PETR4-only confirm path, brief modal, progress ring |
| 4 | `mockup_11_0_archaeology.png` | **Archaeology wall** — 5-year timeline, futures vs cash vs options lanes |
| 5 | `mockup_11_0_strategy_lab.png` | **Strategy Lab grid** — 50 NTSL cards, sector filters, scan/index UX |

**Recommendation (updated):** Ship the **Hybrid Cockpit** below — one layout that keeps the best of all five mockups. Archaeology and Strategy Lab become **presets**, not separate products.

---

## Live trading — what you see where (today)

**Short answer:** You do **not** need ProfitChart open to know the scanner/motor/mind is running. Your **confirmation surface is the board** at http://127.0.0.1:8000/board. ProfitChart is a **data + execution terminal**, not a remote-controlled UI puppet.

### What ProfitChart is (and is not)

| | Today (pre–Phase C) | After Phase C (DLL orders wired) |
|---|---------------------|----------------------------------|
| **Quotes / chains** | Bridge reads via DLL or stub | Same — Profit must be running for live quotes |
| **Scanner / motor / mind** | Runs in Arbitragem API — **invisible in Profit** | Same — logic stays on the board |
| **Paper execute** | Sim auto-fill in bridge (`is_paper=true`) | N/A on sim account |
| **Live execute** | Ticket → `data/profit_outbox/next_order.json` + **Chart Trading hint** (`C Mercado · 100 · PETR4`) — **you click in Profit** | DLL may place orders; Profit still shows fills/positions natively |
| **NTSL strategies** | Export to `exports/profit/` → **manual import** in Profit Editor | Optional auto-arm (Phase C deliverable) |

ProfitChart will **not** visibly “be driven” like a macro recorder. You will see **your normal Profit UI** plus **our hints/outbox**. The agent’s brain (radar, scanner, engine mind) lives on the **blackboard**.

### “Is it on?” — 30-second checklist (board)

Look at the **status bar** (top of board):

| Signal | Green means |
|--------|-------------|
| **Paper** / **Live** pill | Mode matches intent (`PAPER_TRADING_MODE` in `.env`) |
| **Profit OK** | Bridge reachable at `:9100` |
| **Scanner** `(N)` | Universe loaded (14–17 symbols; `1` in golden path) |
| **MOTOR** pill | Orchestrator active — auto scan/execute when sleeves ON |
| **CASH / OPT / PAIR** sleeves | Green = sleeve open (paused = grey) |
| **GATE OK** | Risk cockpit not blocking confirms |

Then scroll to **Engine Mind** (footer):

| Signal | Meaning |
|--------|---------|
| Pulsing dot + phase (`SCAN`, `IDEATE`, …) | Motor cycle running |
| Sources list (max 5) | What the mind used this cycle (quotes, knowledge, …) |
| Recent cycles | Timestamped phase log |

**CLI equivalent:**

```powershell
python scripts/status_tick.py --json
# api.ok, motor.active, sleeves, degraded, knowledge, replay_training
```

### When you *do* need ProfitChart visible

1. **Live ticket execution** — pending order in outbox; companion shows hint; you confirm in Chart Trading.  
2. **NTSL arm/replay** — import strategy from `exports/profit/` or Strategy Store export.  
3. **P&L truth reconcile** — compare board Day P&L vs Profit account (Phase C gate #4).  
4. **Option chain sanity** — refresh strikes in `core17_options.csv` against real chain.

### ProfitChart Companion panel (board)

Already on board: **Bridge ON**, **ProfitChart ✓** (when `PROFITCHART_EXE` set), entry/stop/target levels to copy beside your chart. This is the “side-by-side” mirror — not remote control.

---

## Hybrid Cockpit — north-star layout (11.0 UI)

Merges the best of all five mockups into **one default desktop** + two presets.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STATUS: Paper/Live · Profit OK · Scanner(17) · MOTOR · Sleeves · GATE     │  ← #1 Command Center bar
│ [Learning rail: patches | briefing spark | degraded banner if any]          │  ← #2 top strip
├──────────┬──────────────────────────────────────────────┬───────────────────┤
│ WATCHLIST│  SYMBOL PANEL + ProfitChart Companion levels │  IDEA STACK        │  ← #1 center
│ Core17   │  Trade product + theory chips                │  Decision queue    │  ← #3 confirm/brief
│ grad badges│  Archaeology chip (your history)           │  Confirm → brief  │
├──────────┴──────────────────────────────────────────────┴───────────────────┤
│ STRATEGY LAB strip (collapsible): 50 NTSL cards · sector filter · Scan      │  ← #5
├─────────────────────────────────────────────────────────────────────────────┤
│ ENGINE MIND: phase · sources · cycle bars · recent log                      │  ← #1 footer
└─────────────────────────────────────────────────────────────────────────────┘

Presets (layout switcher):
  • default     — Hybrid above
  • archaeology — #4 timeline hero replaces Strategy Lab strip
  • golden      — #3 mobile: PETR4-only, hide watchlist extras, large confirm
  • learn       — #2 expanded: learning rail + patch drawer full width
```

### Elements kept from each mockup

| Mockup | Kept in hybrid |
|--------|----------------|
| #1 Command Center | 3-column grid, status KPIs, engine mind footer |
| #2 Learning rail | Top collapsible strip: patches + daily briefing mini-charts |
| #3 Golden mobile | `golden` preset: single-symbol, decision brief modal, progress ring |
| #4 Archaeology | Symbol “your history” chip + `archaeology` preset timeline |
| #5 Strategy Lab | Bottom collapsible NTSL grid linked to Strategy Store scan |

---

## Live Radar — new 11.0 feature (scoped)

A single **“systems green”** strip so you never guess.

| ID | Owner | Task |
|----|-------|------|
| W11.6 | Worker | **Live Radar** widget: 6 lamps (API, Bridge, Motor, Scanner, Mind, Sleeves) — all green = trading stack live |
| W11.7 | Worker | **Outbox ticker** — last ticket + Chart Trading hint + link to `next_order.json` |
| A11.13 | Backend | `GET /ops/live-radar` aggregates health + orchestrator + bridge mode + last_cycle_age_sec |
| W11.8 | Worker | Audible/ping optional when MOTOR transitions idle→active (off by default) |
| A11.14 | Backend | Bridge reports `dll_mode: stub|loaded|callbacks_wired` in `/health` |

**Rule for Filipe:** If **Live Radar** is all green and **MOTOR** pill shows, the stack is working — ProfitChart only needed when executing a live ticket or arming NTSL.

---

## Release 11.0 phases (proposed)

| Tier | Symbols | Role |
|------|---------|------|
| **Golden** | PETR4 | Mastery path — 5 green sessions before promote |
| **Core14** | `data/filipe_core14.csv` | Motor universe backbone |
| **+3 extension** | BOVA11, RADL3, MGLU3 | Index sleeve + Filipe-history names |
| **Shadow** | Next from factory | Clone PETR4 template → 3 shadow sessions |

### Options per underlying

`data/core17_options.csv` holds **sample weekly call/put tickers** (refresh strikes in Profit weekly). Structures per symbol:

1. Covered call  
2. Vertical spread  
3. Collar  
4. Cash scalp (VWAP reclaim)  
5. Protective put / BOVA hedge  

→ **17 × ~3 structures ≈ 50 NTSL files** in `strategies/ntsl/core14_options/`.

---

## Release 11.0 phases (proposed)

### 11.0-alpha — Archaeology spine (2 weeks)

| ID | Owner | Task |
|----|-------|------|
| A11.1 | Backend | FIFO round-trip P&L on archaeology rows (replace signed-valor proxy) |
| A11.2 | Backend | Futures lane (`WIN*`, `WDO*`) separate from equities in timeline API |
| A11.3 | Backend | `GET /archaeology/summary` — top symbols, win rate, net flow |
| A11.4 | Worker | Board layout presets: **default (hybrid)**, archaeology, golden, learn |
| A11.5 | Worker | Symbol panel “your history” chip when `has_live_history` |
| A11.6 | Both | Ingest insights into knowledge RAG (`ingest_knowledge.py --path insights`) |
| W11.6 | Worker | Live Radar widget + outbox ticker (see above) |

### 11.0-beta — Strategy Forge (2 weeks)

| ID | Owner | Task |
|----|-------|------|
| A11.7 | Backend | Replay top-10 archaeology symbols (VALE3, WIN roll) |
| A11.8 | Backend | NTSL pack version tag + `strategy_store` diff on regenerate |
| W11.1 | Worker | Strategy Lab strip in hybrid layout (mockup #5) |
| W11.2 | Worker | Per-structure filter + link to replay player |
| W11.3 | Worker | Trade product → pick NTSL from store by structure match |
| A11.9 | Backend | Options chain refresh job (Profit bridge → update `core17_options.csv`) |

### 11.0-rc — Core17 motor (2 weeks)

| ID | Owner | Task |
|----|-------|------|
| A11.10 | Backend | `filipe_core17` scanner mode in config |
| A11.11 | Backend | Motor universe max 5 auto + 12 shadow queue |
| W11.4 | Worker | Core17 sector strip + correlation map |
| W11.5 | Worker | Graduation badges use archaeology fill counts |
| A11.12 | Backend | Patch proposals weighted by archaeology win rate |

### 11.0-GA — Live memory gates (1 week)

| Gate | Target |
|------|--------|
| History imported | ≥9,000 archaeology rows, 0 duplicate ext_id |
| Strategy store | 50 NTSL indexed, scan <2s |
| Replay | VALE3 + PETR4 sessions green |
| Golden path | Still PETR4-first; Core17 unlock after 5 sessions |
| RAM | ≤1.5 GB with archaeology timeline cached |
| Manual | Filipe signs off archaeology P&L reconcile vs XP statement |

---

## Deferred / out of scope

- Public hosting, Cloudflare tunnel  
- Phase C live DLL (see `docs/PHASE_C_GATE.md`)  
- Auto-refresh option strikes from B3 official file (manual weekly OK)  
- YouTube ingest (`scripts/ingest_youtube.py`) — optional media RAG  
- GPU embed batch for full history text export  

---

## Suggested next actions (Filipe)

1. **Morning ritual:** open board only → check Live Radar (when shipped) or status bar MOTOR + Profit OK.  
2. Keep ProfitChart open **only when** placing live tickets or arming NTSL.  
3. `python scripts/status_tick.py --json` before session — motor.active should be true.  
4. Strategy Store → **Scan** → verify 50 strategies indexed.  
5. Pick hybrid default; use **golden** preset on phone/low-RAM days.

---

## Related docs

- [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md)  
- [docs/RELEASE_10.0_RUNBOOK.md](docs/RELEASE_10.0_RUNBOOK.md)  
- [docs/STRUCTURES.md](docs/STRUCTURES.md)  
- [docs/PHASE_C_GATE.md](docs/PHASE_C_GATE.md)

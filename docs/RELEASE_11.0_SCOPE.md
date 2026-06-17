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

**Recommendation:** Ship **#1** as default desktop; expose **#4** as `/board?layout=archaeology` preset when history imported; **#3** for `LOW_RAM_MODE` phone preview.

---

## Core17 symbol policy

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
| A11.4 | Worker | Board layout preset **archaeology** (mockup #4) |
| A11.5 | Worker | Symbol panel “your history” chip when `has_live_history` |
| A11.6 | Both | Ingest insights into knowledge RAG (`ingest_knowledge.py --path insights`) |

### 11.0-beta — Strategy Forge (2 weeks)

| ID | Owner | Task |
|----|-------|------|
| A11.7 | Backend | Replay top-10 archaeology symbols (VALE3, WIN roll) |
| A11.8 | Backend | NTSL pack version tag + `strategy_store` diff on regenerate |
| W11.1 | Worker | Strategy Lab grid UI (mockup #5) |
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

1. Run import CLI on your xlsx (already mapped).  
2. Board → Archaeology panel → confirm timeline populates.  
3. Strategy Store → **Scan** → verify 50 strategies.  
4. Pick favorite board mockup (#1–#5) for 11.0-alpha UI sprint.  
5. Refresh `core17_options.csv` strikes in Profit for one symbol (PETR4) as pilot.

---

## Related docs

- [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md)  
- [docs/RELEASE_10.0_RUNBOOK.md](docs/RELEASE_10.0_RUNBOOK.md)  
- [docs/STRUCTURES.md](docs/STRUCTURES.md)  
- [docs/PHASE_C_GATE.md](docs/PHASE_C_GATE.md)

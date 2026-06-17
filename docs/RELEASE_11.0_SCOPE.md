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

---

## Core17 symbol policy

| Tier | Symbols | Role |
|------|---------|------|
| **Golden** | PETR4 | Mastery path — 5 green sessions before promote |
| **Core14** | `data/filipe_core14.csv` | Motor universe backbone |
| **+3 extension** | BOVA11, RADL3, MGLU3 | Index sleeve + Filipe-history names |
| **Shadow** | Next from factory | Clone PETR4 template → 3 shadow sessions |

### Options per underlying

`data/core17_options.csv` — sample weekly call/put tickers (refresh in Profit weekly).

---

## Live Radar — full spec (11.0-alpha priority)

**Goal:** One glance answers *“Can I trade right now?”* — without opening ProfitChart.

### UI placement

Directly under the status bar in the **Hybrid Cockpit** (always visible, not a preset).

```
┌ LIVE RADAR ─────────────────────────────────────────────────────────────┐
│ ● API  ● Bridge  ● Motor  ● Scanner  ● Mind  ● Sleeves  │ OUTBOX: —   │
│   OK      OK      LIVE     17 sym    SCAN    CASH OPT    │ R$ day P&L  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Lamp | Green when | Yellow when | Red when |
|------|------------|-------------|----------|
| **API** | `/health/live` 200 | slow p95 | offline |
| **Bridge** | `:9100/health` OK | stub mode | unreachable |
| **Motor** | `orchestrator.active` + cycle &lt; 120s ago | idle but enabled | paused / circuit open |
| **Scanner** | universe loaded, last scan &lt; 15m | golden path 1-symbol OK | 0 symbols |
| **Mind** | engine mind phase not `ERROR` | stale &gt; 3 cycles | degraded |
| **Sleeves** | all open for intended mode | partial pause | kill switch / all closed |

**Outbox ticker (right side):** last ticket symbol, side, qty, `chart_trading_hint`, age seconds, link to copy hint.

### API contract

```http
GET /api/v1/ops/live-radar
```

```json
{
  "all_green": false,
  "ready_to_scan": true,
  "ready_to_execute": false,
  "lamps": {
    "api": {"state": "green", "detail": "10.0.0"},
    "bridge": {"state": "yellow", "detail": "stub", "dll_mode": "loaded"},
    "motor": {"state": "green", "last_cycle_age_sec": 42},
    "scanner": {"state": "green", "symbol_count": 1, "mode": "golden_path"},
    "mind": {"state": "green", "phase": "SCAN"},
    "sleeves": {"state": "green", "cash": true, "options": true, "pairs": true}
  },
  "outbox": {
    "pending": false,
    "last_ticket": null
  },
  "blockers": ["phase_c_gate", "paper_trading_mode"]
}
```

`ready_to_execute` is **false** until Phase C + live account profile — even if all lamps green.

### Implementation tasks

| ID | Owner | Task | Phase |
|----|-------|------|-------|
| A11.13 | Backend | `GET /ops/live-radar` aggregator | alpha |
| A11.14 | Backend | Bridge `/health` adds `dll_mode`, `account_profile`, `is_paper` | alpha |
| W11.6 | Worker | Live Radar partial + HTMX 10s poll | alpha |
| W11.7 | Worker | Outbox ticker + copy hint button | alpha |
| W11.8 | Worker | Optional sound on MOTOR idle→active (`.env`) | beta |
| A11.15 | Backend | `status_tick.py --json` includes `live_radar` mirror | alpha |
| W11.9 | Worker | Mobile: radar collapses to single dot + tap expands | rc |

### Filipe rule

**All six lamps green + MOTOR** = stack is alive. **ProfitChart** only when `outbox.pending` or arming NTSL.

---

## Strategy research — top sources (automated logic)

Synthesis from industry references (not endorsements — patterns to **encode in our stack**):

| Source | Focus | Takeaway for Arbitragem |
|--------|--------|-------------------------|
| [Bookmap — algo strategies](https://bookmap.com/blog/key-algorithmic-trading-strategies-from-trend-following-to-mean-reversion-and-beyond) | Regime → strategy fit | Volatile session → scalp/momentum; range → mean reversion |
| [QuantInsti — mean reversion](https://blog.quantinsti.com/mean-reversion-strategies-introduction-building-blocks/) | RSI, SMA cross, pairs | Pair with trend filter; hard stops mandatory |
| [3Commas — crypto mean reversion](https://3commas.io/mean-reversion-trading-bot) | Grid / DCA in sideways | BTC 1m grid only when ADX &lt; 25 |
| [GambiTick-AI](https://github.com/seady22/GambiTick-AI) / [MES bot](https://github.com/chang-pro/mes-futures-trading-bot) | Futures scalps: VWAP, volume profile, brackets | **Bracket SL/TP every tick**; session window filter |
| [NQ IFVG bot](https://github.com/prashanthaitha24/nq-strategy-b-bot) | Multi-TF FVG confluence | 5m retest inside 15m zone — portable to WIN 5m/15m |

**Common denominator:** bots automate **execution + risk**, not discretion. Edge = confluence + session filter + walk-forward proof.

---

## Strategy catalog — quick scalps (designed for this repo)

Priority order for **your history** (heavy WIN/WDO) and **R$500 capital**.

### B3 futures (WIN preferred series)

Roll rule: trade **front month** (`WINJ26`, `WINM26`, …) — roll 5 sessions before expiry.

| ID | Name | Logic | Entry | Stop | Target | Session |
|----|------|-------|-------|------|--------|---------|
| **F1** | Opening range breakout | First 15m high/low break with volume &gt; 1.2× 5m avg | Stop entry 1 tick beyond OR | Other side of range | 1.5× range width | 10:00–12:00 |
| **F2** | VWAP reclaim | Price below VWAP → reclaim + close above (long) | Market on close | 8 ticks (40 pts = R$8) | 12 ticks | 10:30–16:30 |
| **F3** | WIN–WDO divergence | WIN new HOD but WDO not confirming USD bid | Fade WIN short | 10 ticks | 15 ticks | 11:00–15:00 |
| **F4** | Prior POC magnet | Open away from prior day POC → revert | Limit at POC ±2 ticks | 12 ticks | POC touch | all day |
| **F5** | Archaeology bias | Your CSV: WIN &gt;80% history — only take F1/F2 **long** on green IBOV breadth days | same as F1/F2 | tighter 6 ticks | 10 ticks | paper first |

**Spinoff (in-box):** `structure_type: win_scalp_vwap` in idea generator — maps to NTSL stub + replay worker.

**Spinoff (out-of-box):** **“Pulse scalp”** — motor fires only when Live Radar all green + sleeve CASH open + first 3 engine mind sources green (no degraded).

### Crypto (paper sleeve first)

| ID | Name | Logic | Pair | Notes |
|----|------|-------|------|-------|
| **C1** | 1% mean reversion | Buy −1% from 20-bar mean, sell +1% | BTCUSDT | Binance paper only today |
| **C2** | Funding fade | Long spot when funding &lt; −0.01% and RSI &lt; 35 | BTC perp proxy | read-only funding if no perp |
| **C3** | Volatility halt | Sentinel: 5% 5m move → pause motor 15m | all | from mefai-engine pattern |

### Equities / options (NOT for R$500 live)

Core17 options NTSL pack is for **later** when capital &gt; R$5k and golden path graduated. At R$500, **do not** rely on 50× stock margin fantasies — Brazilian day-trade margin and lot sizes make PETR4 scalps impractical at this size.

---

## Are we ready to trade live next market open?

### Honest answer: **No — not fully automated live. Paper + manual tickets only.**

| Gate | Status | Blocker |
|------|--------|---------|
| Phase C ([PHASE_C_GATE.md](PHASE_C_GATE.md)) | **Open** | Need 5 paper B3 days, 20 fills, P&L reconcile |
| DLL order callbacks | **Stub** | `profit_dll_bridge.py` loads DLL; ctypes orders TODO |
| Live execute path | **Outbox** | You click Chart Trading in Profit |
| Golden path | **PETR4** | 5 green sessions not signed off |
| Futures sizing in motor | **Partial** | `capital_manager` sizes stock lots, not WIN contracts |
| WIN series roll | **Manual** | No auto-roll to front month in scanner yet |
| R$500 capital | **Tight** | See math below — **1 WIN max** recommended |

**What you CAN do next open (safe):**

1. Board + Live Radar (when shipped) — confirm MOTOR + Bridge green.  
2. **Paper** `PAPER_TRADING_MODE=true`, `PAPER_CAPITAL_BRL=500`.  
3. **One** WIN contract scalps F2 (VWAP reclaim) — manual confirm each ticket.  
4. Journal every fill; compare to Profit at EOD.

**What you should NOT do yet:**

- Auto-live motor with real money.  
- Multiple concurrent WIN+WDO on R$500.  
- Crypto live (paper only in app).  
- Core17 options structures on live account.

---

## Capital math — R$500 (~“500 bucks”)

Assume **BRL R$500** (if USD, convert — margins are in reais on B3).

### B3 day-trade margins (B3 circular Feb/2026 — verify with XP)

| Contract | B3 min margin (day) | Your estimate |
|----------|---------------------|---------------|
| **WIN** (mini índice) | **R$ 155** | you said ~R$100 — use **R$155** (new rule) |
| **WDO** (mini dólar) | **R$ 140** | you said ~R$150 — close |
| **BIT** (Bitcoin fut) | R$ 45 | optional |
| **MBR** (micro índice) | R$ 65 | **better for small account** — consider for phase 2 |

### Position budget (include ~R$100 buffer for swings)

| Plan | Allocation | Contracts |
|------|--------------|-----------|
| **Conservative** | 1× WIN only | R$155 + buffer → **1 contract** |
| **Balanced** | 1× MBR or 1× WDO | 1 contract, no stacking |
| **Aggressive (not recommended)** | 1 WIN + 1 WDO | R$295 margin — leaves R$205 — one bad tick wipes buffer |

**WIN tick economics:** R$0.20/point × 5 pt min = **R$1/tick**. A 50-point stop = **R$10** per contract. Daily loss limit should be **R$50** (10% of capital) = max 5 such stops.

**Stocks at 50× leverage:** Not modeled in app today. At R$500, even with leverage, one PETR4 lot (100 sh × ~R$38) dominates the account — **skip equities live** until R$3k+.

---

## Master phased plan

### Phase 0 — This week (before next open)

| Step | Action |
|------|--------|
| 0.1 | Set `.env`: `PAPER_TRADING_MODE=true`, `PAPER_CAPITAL_BRL=500`, `DEFAULT_DAILY_LOSS_LIMIT_BRL=50` |
| 0.2 | `python scripts/import_filipe_b3_history.py` (done) — review insights |
| 0.3 | Ship **Live Radar** (W11.6–A11.15) — alpha sprint |
| 0.4 | Add `futures_contract_sizer` — 1 contract max when capital &lt; R$2000 |
| 0.5 | Paper replay **F2 VWAP reclaim** on WIN front month |

### Phase 1 — Paper WIN only (2–3 B3 weeks)

- Universe: `WIN` front series only (+ optional WDO paper shadow).  
- Strategies: **F2**, then **F1** if win rate &gt; 45% paper.  
- Gates: 5 green sessions, &lt;5% motor errors, 20+ paper fills ([PHASE_C_GATE.md](PHASE_C_GATE.md)).  
- Live Radar must be all green every morning.

### Phase 2 — Manual live micro (after Phase 0 gates)

- `PAPER_TRADING_MODE=false` on **day account** only.  
- **1 WIN** or **1 MBR** contract max; outbox + Chart Trading confirm.  
- Daily stop R$50 hard; kill switch tested.  
- P&L reconcile board vs Profit within 2%.

### Phase 3 — Semi-auto live (11.0-rc)

- DLL `place_order` wired (Phase C deliverable).  
- Motor auto-fire **only** when Live Radar green + graduation badge on symbol.  
- Optional: 1 WDO hedge when WIN exposure &gt; 30 min.

### Phase 4 — Core17 + options (capital R$5k+)

- Promote PRIO3/RADL3 from shadow.  
- Strategy Lab NTSL arm for covered calls on held stock.  
- Not before golden path + futures paper proven.

### Phase 5 — Crypto live (optional, separate sleeve)

- C1 mean reversion on Binance with API keys in `.env`.  
- Max 5% of total capital; never cross-margin with B3.

---

## Release 11.0 phases (software)

### 11.0-alpha — Archaeology spine (2 weeks)

| ID | Owner | Task |
|----|-------|------|
| A11.1 | Backend | FIFO round-trip P&L on archaeology rows (replace signed-valor proxy) |
| A11.2 | Backend | Futures lane (`WIN*`, `WDO*`) separate from equities in timeline API |
| A11.3 | Backend | `GET /archaeology/summary` — top symbols, win rate, net flow |
| A11.4 | Worker | Board layout presets: **default (hybrid)**, archaeology, golden, learn |
| A11.5 | Worker | Symbol panel “your history” chip when `has_live_history` |
| A11.6 | Both | Ingest insights into knowledge RAG (`ingest_knowledge.py --path insights`) |
| A11.16 | Backend | `futures_contract_sizer` — margin-aware 1-lot cap for capital &lt; R$2k |
| A11.17 | Backend | WIN front-month resolver in scanner (`WINFUT` → active `WIN*`) |
| A11.18 | Backend | Strategy templates F1–F5 as `structure_type` + replay hooks |

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

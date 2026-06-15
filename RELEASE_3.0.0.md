# Release 3.0.0 — Scope (draft)

**Codename:** *Structure Deck*  
**Prerequisite:** Ship and **paper-validate 2.0.0** for at least one full trading week (Core14 scalps + at least one BOVA hedge idea executed in paper with journal review).  
**Focus:** Turn the 2.0 blackboard into an **options-aware intraday cockpit** — multi-leg structures, Greeks-aware sizing, and portfolio-level gates — still **only** Filipe Core14 cash + BOVA index options + per-stock options on those 14 names.

**Primary UI:** http://localhost:8000/board (HTMX blackboard, evolved)  
**Legacy UI:** http://localhost:8501 (Streamlit admin only)

---

## Frozen decisions (carry forward from 2.0)

| # | Decision |
|---|----------|
| 1 | **Universe:** Core14 cash + BOVA index options + stock options on Core14 only |
| 2 | **Execution:** NTSL via Profit (primary); Clear for leg fills when API supports multi-leg |
| 3 | **Backtest gate:** PF ≥ 1.3, max DD ≤ 8% (per idea); portfolio gate added in 3.0 |
| 4 | **Topology:** VPS dashboard + Windows PC Profit bridge (Tailscale) |
| 5 | **No Telegram confirm for live** — in-app 2-step confirm + screen watch |

**2.0 ships:** HTMX blackboard, idea stack, board notes, setup wizard, profit stub, paper mode, scanner scalp engine, SSE quotes, sector baskets stub.

---

## 1. Product vision — “structure deck” vs 2.0 blackboard

2.0 feels like a **scalper’s blackboard**: watchlist, single-symbol panel, ranked cash/BOVA ideas, confirm → NTSL export.

3.0 feels like a **structure trader’s deck**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ RISK COCKPIT  net Δ · Γ · Θ · margin · sector exposure · kill switch     │
├──────────┬─────────────────────────────┬─────────────────────────────────┤
│ WATCHLIST│  CHART + LEVELS + GREEKS    │ STRUCTURE BUILDER               │
│ Core14   │  cash or opt chain overlay  │ legs[] · hedge ratio · preview  │
│ + opts   │  IV rank · term structure   │ covered call · spread · collar  │
├──────────┴─────────────────────────────┴─────────────────────────────────┤
│ OPPORTUNITY RAIL  pairs · sector baskets · BOVA vs basket · IV events    │
├──────────────────────────────────────────────────────────────────────────┤
│ IDEA STACK (v3)  structure cards · walk-forward badge · portfolio impact │
└──────────────────────────────────────────────────────────────────────────┘
```

| Dimension | 2.0 Blackboard | 3.0 Structure Deck |
|-----------|----------------|-------------------|
| Unit of work | Single-symbol scalp idea | **Multi-leg structure** with hedge context |
| Options | BOVA chain stub + stock chain API | **Full chain panel**, IV rank, term structure |
| Risk view | Per-idea notional in confirm modal | **Portfolio cockpit** — net delta, sector, margin |
| Backtest | Per-pattern PF/DD badge | **Walk-forward auto-promotion** + portfolio backtest |
| Execution | 1-leg NTSL export | **Multi-leg NTSL** + delta-aware sizing |
| Research | Symbol report (Ollama) | Structure templates library + pair/stat arb signals |

**Emotional goal:** Filipe opens the board at 09:00, sees *“banks basket weak vs BOVA — collar on ITUB4 + short BBDC4 pair”* with legs pre-filled, backtest proof, and portfolio Greeks before one confirm.

---

## 2. Trading universe (unchanged scope, deeper options)

### 2.1 Cash equities (14) — same as 2.0

| Symbol | Sector | Pair / basket notes |
|--------|--------|---------------------|
| PETR4 | Energia | Anchor; pair with PRIO3 |
| VALE3 | Mineração | Commodity beta |
| PRIO3 | Energia | Pair with PETR4 |
| ITUB4 | Financeiro | Bank basket |
| BBAS3 | Financeiro | Bank basket |
| BBDC4 | Financeiro | Bank basket |
| BBSE3 | Financeiro | Bank basket |
| B3SA3 | Financeiro | Market infra |
| ABEV3 | Consumo | Defensive |
| GGBR4 | Siderurgia | Steel basket |
| CSNA3 | Siderurgia | Steel basket |
| USIM5 | Siderurgia | Steel basket |
| SUZB3 | Papel | Pulp |
| WEGE3 | Industrial | Quality growth |

**Config:** `SCANNER_MODE=filipe_core14` · `data/filipe_core14.csv` · `SECTOR_BASKETS` in `filipe_universe.py`

### 2.2 BOVA index options

- **Underlying:** BOVA11
- **Depth:** Near + next monthly series; calls + puts; auto-discovered from ProfitDLL
- **3.0 adds:** IV rank (52w proxy), term structure snapshot, skew flag, hedge ratio vs Core14 basket

### 2.3 Stock options (Core14 only)

- **Scope:** Listed options on each of the 14 underlyings (e.g. PETR4, VALE3 calls/puts)
- **Liquidity filter:** Bridge returns chain; scanner drops strikes with spread > N ticks or OI below threshold
- **3.0 structures:** Covered calls, vertical spreads, collars, protective puts — **not** exotic multi-underlying combos outside Core14+BOVA

### 2.4 Explicit OUT OF SCOPE for 3.0

| Out of scope | Rationale |
|--------------|-----------|
| Full B3 options universe | Liquidity + margin complexity |
| Small caps / illiquid names | Slippage + chain gaps |
| Overnight / swing multi-day primary UX | Intraday scalping + same-day structures remain default |
| Crypto, FX, US equities | B3 focus |
| Fully automated live (no confirm) | Safety — 2-step confirm retained |
| Telegram confirm for live orders | Frozen out in 2.0 |
| Custom exotic structures (iron condor on 8 names, dispersion on non-Core14) | Defer to 4.0+ |
| Replacement of Profit Tick-a-Tick backtest | Profit remains source of truth |
| Mobile-first full structure builder | Mobile = watchlist + confirm + risk banner only |

---

## 3. Major pillars (3.0)

| # | Pillar | One-liner |
|---|--------|-----------|
| **P1** | **Live Profit bridge** | Real ProfitDLL on Windows PC — quotes, chains, backtest run, order status |
| **P2** | **Multi-leg options structures** | Spreads, collars, covered calls, BOVA vs basket hedge — first-class `legs[]` |
| **P3** | **Pair & stat arb rail** | Sector pairs + z-score mean reversion on Core14 (PETR/PRIO, steel trio) |
| **P4** | **Intraday risk cockpit** | Net delta, sector concentration, margin estimate, kill switch at portfolio level |
| **P5** | **Walk-forward auto-promotion** | Nightly Profit exports → gates → Idea Stack without manual CSV upload |

---

## 4. Data & opportunity engine v3

Goal: surface **structure-ready** setups with options context, not only cash scalps.

### 4.1 Live data (extensions over 2.0)

| Data | Source | 3.0 use |
|------|--------|---------|
| Cash quotes + tape | ProfitDLL | Unchanged |
| BOVA option chain | ProfitDLL | IV, bid/ask, expiry ladder |
| Stock option chains (×14) | `GET /options/{underlying}` | Strike picker, covered call targets |
| Positions + day P&L | Clear + Profit fills | Cockpit + structure P&L attribution |
| Historical vol proxy | Session bars + 30d | IV rank (vs realized) |
| Correlation matrix | Rolling 30d returns | Pair signals, basket hedge sizing |

### 4.2 Opportunity signals (scanner v3)

| Signal | Structure bias |
|--------|----------------|
| Sector basket divergence | Short weak / long strong + BOVA put hedge |
| Pair z-score (PETR/PRIO, GGBR/CSNA/USIM) | Relative value legs in Idea Stack |
| IV rank high + uptrend | Covered call on held / intended long |
| IV rank low + event risk | Collar or protective put |
| BOVA term structure inversion | Calendar / diagonal ideas (template only if liquid) |
| Skew extreme (BOVA puts rich) | Index hedge vs long cash basket |
| Beta divergence (stock vs IBOV) | Delta-neutral pair + BOVA leg |

**Output:** `TradeIdea` v3 — `structure_type`, `legs[]` (each leg: asset, side, qty, strike, expiry, ratio), `hedge_ratio`, `target_delta`, `rationale_tags[]`, `backtest_proof`, `portfolio_impact` preview.

### 4.3 Structure template library

| Template | Example legs |
|----------|--------------|
| **Covered call** | Long PETR4 + short PETR call (OTM, nearest monthly) |
| **Vertical spread** | Bull call spread on VALE3 |
| **Collar** | Long ITUB4 + long put + short call |
| **Index hedge** | Long BOVA put vs weighted Core14 basket |
| **Sector pair** | Long PRIO3 / short PETR4 (cash) |
| **Steel basket short** | Short CSNA3 + USIM5 vs long GGBR4 |
| **BOVA vs basket** | BOVA call/put vs sector ETF proxy weights |

Templates stored in `data/structure_templates/` + NTSL stubs in `strategies/ntsl/structures/`.

---

## 5. Execution v3 — multi-leg NTSL, hedge ratios, delta-aware sizing

### 5.1 Flow

```
Structure Builder or Idea Stack
    → [Review] modal: legs, Greeks preview, margin, portfolio impact
    → [Confirm] pre-trade risk (daily loss, max contracts, sector cap, net Δ)
    → NTSL bundle export OR Clear multi-order batch
    → Journal: structure_id links all legs
    → Profit: arm strategies / manual chart watch
```

### 5.2 Execution capabilities

| Capability | Detail |
|------------|--------|
| **Multi-leg NTSL** | One export file or ordered strategy set per structure template |
| **Hedge ratios** | BOVA contracts sized from basket beta vs BOVA11 |
| **Delta-aware sizing** | Target portfolio net Δ band (e.g. −0.2 to +0.2 per structure) |
| **Leg sequencing** | Cash leg first, then options (configurable); paper sim models partial fill |
| **Rollback** | Kill switch cancels open orders + pauses NTSL strategies |

### 5.3 Safety gates (extends 2.0)

| Gate | 3.0 rule |
|------|----------|
| Paper default | Until `PAPER_TRADING_MODE=false` + wizard green |
| Structure confirm | All legs shown; no hidden hedge |
| Max net delta | Config: `MAX_PORTFOLIO_NET_DELTA` |
| Options margin | Estimate from bridge or Clear summary before send |
| Same-structure dedup | Block duplicate structure_id within session |
| Backtest proof | Required for auto-promoted ideas; manual ideas warn if missing |

### 5.4 Backends

| Backend | When |
|---------|------|
| **Profit NTSL** | Primary — multi-strategy export per structure |
| **Clear Smart Trader** | Live leg fills when multi-leg API confirmed |
| **Paper simulator** | Full structure fill model with spread + 1 tick slippage per leg |

---

## 6. UI v3 — charts, chain panel, structure builder

### 6.1 Blackboard upgrades

| Feature | Description |
|---------|-------------|
| **Chart on board** | Lightweight Charts (or themed Plotly) in symbol panel — cash + overlay strikes |
| **Options chain panel** | Tab per symbol: strikes, IV, bid/ask, OI proxy, click → add leg |
| **Structure builder** | Right column: drag legs, edit ratios, live Greeks preview |
| **Risk cockpit strip** | Top bar: net Δ, day P&L, margin %, sector chips, kill switch |
| **Opportunity rail** | Footer: pair z-scores, sector heat, BOVA regime banner |
| **Layout presets** | “Scalp”, “Options hedge”, “Pairs” — persisted like 2.0 S10 |

### 6.2 Idea Stack v3

- Structure cards with leg summary + mini payoff sketch
- Walk-forward badge (fold stability, not only single PF)
- Portfolio impact chip (“+0.15 net Δ, banks +12% notional”)
- Filter: cash only / options only / hedged

### 6.3 Streamlit

- Admin: portfolio backtest report, structure template editor, walk-forward job monitor
- No new primary UX in Streamlit

---

## 7. Backtest & research v3

### 7.1 Walk-forward auto-promotion

```
NTSL template × symbol (or structure)
    → Profit bridge POST /backtest/run
    → CSV export watcher (2.0 A2.4b)
    → Walk-forward folds (Python layer + Profit metrics)
    → Gates: PF ≥ 1.3, DD ≤ 8%, min trades, fold consistency
    → Auto-promote to Idea Stack with badge
    → Ollama structure summary on blackboard
```

| Task | Detail |
|------|--------|
| **R3.1** | Nightly queue: top templates × Core14 + 3 structure types |
| **R3.2** | Fold consistency score (e.g. ≥ 3/4 folds pass) |
| **R3.3** | Demote ideas when live paper slippage breaches threshold |

### 7.2 Portfolio-level backtest

- Simulate **combined** Core14 book: cash scalps + 1–2 concurrent structures
- Metrics: portfolio PF, max DD, correlation of P&L streams, margin peaks
- Output: `GET /research/portfolio-backtest` + PDF/CSV for weekly review
- **Not** a replacement for Profit tick backtests — aggregates exported results

### 7.3 Research artifacts

| Artifact | Purpose |
|----------|---------|
| Per-structure NTSL folder | `strategies/ntsl/structures/{template}/` |
| Promotion log | SQLite: why idea promoted / rejected |
| Weekly research digest | Ollama summary of promoted + rejected structures |

---

## 8. Infrastructure v3

| Area | 3.0 target |
|------|------------|
| **VPS production** | Docker Compose on Hetzner/DO; Caddy HTTPS; Postgres optional |
| **Tailscale** | VPS ↔ Windows PC bridge on private IP; no public :9100 |
| **Observability** | Structured logs, health dashboard, bridge heartbeat in status bar |
| **Secrets** | `.env` on VPS; bridge credentials on PC only |
| **Backups** | Daily SQLite/Postgres + journal export |
| **Auth** | `DASHBOARD_AUTH_ENABLED=true` on prod; board session cookie |

### 8.1 Bridge hardening

- Real `ctypes` ProfitDLL wrapper (replace stub)
- Reconnect + quote staleness alerts
- Chain cache TTL + manual refresh button
- Version probe in setup wizard

---

## 9. Phased delivery inside 3.0

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| **3.0-alpha** | Live Profit bridge + stock/BOVA chains in UI + structure `legs[]` model | 2.0 paper week |
| **3.0-beta** | Structure builder + 3 templates (covered call, vertical, BOVA hedge) + risk cockpit v1 | alpha |
| **3.0-rc** | Walk-forward auto-promotion + pair rail + multi-leg NTSL export | beta |
| **3.0.0** | Portfolio backtest + live path (Clear or Profit) + prod VPS cutover | rc + Filipe sign-off |

**Estimated calendar:** **12–16 weeks** after 2.0 paper validation (see §13).

---

## 10. Definition of done (3.0.0)

### 3.0-alpha

- [ ] Real ProfitDLL bridge on Windows PC (quotes + chains, not stub)
- [ ] BOVA + stock option chains in blackboard chain panel (all 14 underlyings)
- [ ] `TradeIdea` supports multi-leg `legs[]` + `structure_type` in API + DB
- [ ] IV rank + term structure flags on BOVA (scanner tags)
- [ ] Setup wizard shows bridge version + chain sample for PETR4 + BOVA

### 3.0-beta

- [ ] Structure builder UI — add/remove legs, preview notional
- [ ] Templates: covered call, vertical spread, BOVA vs basket hedge
- [ ] Risk cockpit strip: day P&L, net delta estimate, sector exposure
- [ ] Pair signals (PETR/PRIO, steel basket) in opportunity rail
- [ ] 2-step confirm shows all legs + margin warning

### 3.0.0 (GA)

- [ ] Multi-leg NTSL export per structure template
- [ ] Walk-forward auto-promotion to Idea Stack (nightly job)
- [ ] Portfolio-level backtest report across Core14
- [ ] Delta-aware sizing + hedge ratio for BOVA legs
- [ ] Paper week **#2** — at least 5 structure trades journaled with slippage review
- [ ] VPS prod: HTTPS, auth, Tailscale to bridge, observability green 5 days
- [ ] Kill switch stops structures + cancels pending legs
- [ ] Docs: `docs/STRUCTURES.md`, updated `agent_integration.md`

---

## 11. Task split (Supervisor + Worker)

**Rule:** Unchanged from 2.0 — Supervisor owns `src/`, `scripts/`, `tests/`; Worker owns `src/web/`, blackboard HTMX.

### Supervisor (Alpha) — 3.0 backlog sketch

| ID | Task | Deliverable |
|----|------|-------------|
| A3.1 | ProfitDLL live bridge | `scripts/profit_bridge.py`, ctypes callbacks |
| A3.2 | Structure model + API | `TradeIdea` legs, `POST /structures/preview` Greeks |
| A3.3 | Scanner v3 signals | IV rank, pair z-score, sector basket |
| A3.4 | Walk-forward promotion job | Nightly cron + Idea Stack insert |
| A3.5 | Multi-leg NTSL exporter | `strategies/ntsl/structures/` |
| A3.6 | Portfolio backtest service | Aggregate Profit exports |
| A3.7 | Risk cockpit API | `GET /risk/cockpit` net delta, sectors |
| A3.8 | Clear multi-leg router | When API allows; else sequential legs |

### Worker — 3.0 backlog sketch

| ID | Task | Deliverable |
|----|------|-------------|
| W3.1 | Chart in symbol panel | Lightweight Charts + levels |
| W3.2 | Options chain panel | HTMX partial, strike click → leg |
| W3.3 | Structure builder column | Leg editor + template picker |
| W3.4 | Risk cockpit strip | Top bar from `/risk/cockpit` |
| W3.5 | Idea Stack structure cards | Leg summary + walk-forward badge |
| W3.6 | Opportunity rail | Pairs + sector heat footer |
| W3.7 | Layout presets | Save/load “options hedge” layout |

---

## 12. Dependency map

```
A3.1 live bridge ──► A3.2 structure API ──► W3.2 chain panel ──► W3.3 builder
A3.3 scanner v3 ──────────────────────────► W3.6 opportunity rail
A3.4 walk-forward ──► A3.6 portfolio BT ────► W3.5 idea cards
A3.5 NTSL export ───────────────────────────► 3.0.0 live path
A3.7 risk API ──────────────────────────────► W3.4 cockpit strip
```

---

## 13. Timeline estimate

| Milestone | Duration (weeks) | Cumulative |
|-----------|------------------|------------|
| 2.0 paper validation week | 1 | 1 |
| **3.0-alpha** (live bridge + chains + legs model) | 4–5 | 5–6 |
| **3.0-beta** (builder + 3 templates + cockpit) | 4–5 | 9–11 |
| **3.0-rc** (walk-forward + pairs + NTSL multi-leg) | 3–4 | 12–15 |
| **3.0.0** (portfolio BT + prod + paper week #2) | 1–2 | **13–17** |

**Realistic target:** **14 weeks** from start of 3.0 work (assuming 2.0 paper week already done).  
**Aggressive:** 12 weeks with full-time agent splits.  
**Conservative:** 17 weeks if ProfitDLL integration or Clear multi-leg blocks.

---

## 14. Open questions for Filipe

1. **Structure priority:** Which 3 templates first — covered calls on PETR4/VALE3, bank collars, or BOVA vs basket hedge?
2. **Holdings assumption:** Structure builder assumes flat book, or sync actual Clear/Profit positions for covered calls?
3. **Net delta band:** Target intraday net delta (e.g. always near 0 vs allow +0.5 directional)?
4. **Pair trading:** Cash pairs only in 3.0, or options legs on both sides (e.g. PETR put vs PRIO call)?
5. **Walk-forward bar:** Keep PF ≥ 1.3 / DD ≤ 8%, or tighten for options (e.g. PF ≥ 1.5)?
6. **Live cutover:** First live structure via Profit NTSL only, or Clear API for option legs?
7. **VPS host:** Existing Hetzner/DO box, or new provision in 3.0-alpha?
8. **Paper week #2 success:** Minimum number of structure types traded before live (suggest: 3 types × 2 paper days each)?

---

## 15. Release strategy — after 2.0

| Release | When | Purpose |
|---------|------|---------|
| **2.0.x** | Now → paper week | Validate blackboard workflow, NTSL confirm, scanner habits |
| **3.0-alpha** | +1 week after paper | Live bridge + chains visible on board |
| **3.0-beta** | +5 weeks | Structure builder + first hedges in paper |
| **3.0.0** | +14 weeks | Portfolio gates + prod VPS + optional live structures |

**Recommendation:** Complete 2.0 paper week with **journal notes on which symbols and sectors you actually trade**. Use that to order structure templates (e.g. if energy > banks, prioritize PETR covered calls + BOVA hedge over bank collars).

---

*Last updated: 2026-06-15 — scope draft for Filipe review. No implementation until 2.0 paper week signed off.*

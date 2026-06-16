# Release 4.0.0 — Scope (draft)

**Brand:** **Arbitragem Scalper** (subtitle: *Structure Deck*)  
**Codename:** *Scalper Cockpit*  
**Prerequisite:** Ship **3.0.0** and complete **3.0.1 polish**; paper-validate with **10+ structure confirms** and journal review before 4.0-beta live features.  
**Focus:** Evolve the 3.0 Structure Deck into a **Profit-native scalper cockpit** — ranked watchlist, Trade Product blackboard, Profit P&L truth, world clocks, education rail, and sandbox replay lab — still **Core14 + BOVA + stock options** at 4.0 GA, with phased universe expansion in 4.1–4.2.

**Primary UI:** http://localhost:8000/board (HTMX blackboard)  
**Legacy UI:** http://localhost:8501 (Streamlit admin only)

---

## Frozen decisions (4.0)

| # | Decision |
|---|----------|
| 1 | **Brand:** **Arbitragem Scalper** — subtitle *Structure Deck* on board header |
| 2 | **Base universe:** Core14 cash + BOVA index options + stock options on Core14 only (unchanged from 3.0) |
| 3 | **Universe expansion (phased):** WINFUT + WDOFUT quotes in **4.1**; BTC/ETH/SOL **watch-only or paper stubs** in **4.2** — no Clear API |
| 4 | **Crypto execution:** TBD — Profit if Nelogica exposes; else paper stub + Binance **public API quotes only** in 4.2 |
| 5 | **Execution:** Profit NTSL primary; **NO Clear API / scrapers** |
| 6 | **P&L / positions / fills:** Profit bridge only (DLL, exports, journal reconcile) |
| 7 | **Risk defaults:** max daily loss **R$ 500**; editable in Risk Profile drawer |
| 8 | **KPI history:** minimum **3 months** fast path; target **2+ years** where Profit exports + journal allow |
| 9 | **Language:** English UI; principal trading terms with **PT-BR explanation in tooltips** (e.g. *Drawdown (rebaixamento)*) |
| 10 | **Bottom rail:** **33% news / 33% economic calendar / 33% lessons** (axioms, theory, tips) |
| 11 | **Max hold:** trades ≤ **10 trading days** or **2 calendar weeks** — swing-intraday hybrid OK, not multi-month |
| 12 | **Twitter / social:** **read-only signals** from **4.1+**; **no auto-trade from social** |
| 13 | **Replay auto-trade:** allowed **only in ProfitChart replay sandbox** at configurable speed (e.g. 10×) — never real money without confirm |
| 14 | **ProfitDLL discovery:** setup wizard + `dev.py` auto-detect on Windows; user may not know install path — we own detection |
| 15 | **Topology:** VPS dashboard + Windows PC Profit bridge (Tailscale) — unchanged |

**3.0 ships:** multi-leg structures, risk cockpit, walk-forward, portfolio backtest, opportunity rail, layout presets, kill switch.

**3.0.1 ships (immediate):** DD display fix, chart load fix, header KPI dedupe, HelpTip skeleton, version `3.0.1-alpha`.

---

## 1. Product vision — Scalper Cockpit vs 3.0 Structure Deck

3.0 feels like a **structure trader’s deck**: builder, Greeks strip, WF badges, pair rail.

4.0 feels like a **scalper’s cockpit** — one screen to decide *take it or skip it* in seconds, with theory and odds when you want depth:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ARBITRAGEM SCALPER · Structure Deck                                          │
│ KPI STRIP  day/wk P&L · win% · slippage · open risk · PF₂₀ · margin · gates  │
│ WORLD CLOCKS  B3 · NY · LON · TYO · SHA  (open / closed / holiday)           │
├──────────┬───────────────────────────────────────────┬───────────────────────┤
│ WATCHLIST│  TRADE PRODUCT (per symbol)               │ IDEA STACK            │
│ sortable │  thesis · economics · odds · chart+levels │ ranked for symbol     │
│ cols     │  legs · catalysts · AI why · notes        │ score · mini board    │
├──────────┴───────────────────────────────────────────┴───────────────────────┤
│ BOTTOM PULSE RAIL  33% news │ 33% calendar │ 33% lessons (axioms/theory)   │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Dimension | 3.0 Structure Deck | 4.0 Scalper Cockpit |
|-----------|-------------------|---------------------|
| Header | Arbitragem + duplicate P&L rows | **Scalper** brand + single KPI strip |
| Watchlist | Symbol + last/bid/ask | **Color, vol, cost, idea score**, column sort/filter |
| Blackboard | Chart stub + builder tabs | **Trade Product** — one narrative card blending cash/options/pairs |
| Idea stack | Global ranked list | **Per-symbol ranked** mini blackboards |
| P&L source | Clear mock + stub | **Profit bridge** truth |
| Bottom | Sector + opportunity rail | **Pulse rail** news + calendar + education |
| Research | Walk-forward + portfolio BT | **+ Replay lab** (sandbox), trade archaeology (4.2) |
| Education | STRUCTURES.md links | Inline **why / odds / alternatives** on every product |

**Emotional goal:** Filipe opens at 09:00, clocks show B3 open + NY pre-market, watchlist sorted by best edge, clicks PETR4 — blackboard shows a **Trade Product** with thesis, chart levels, PF/DD, and one-click NTSL arm — bottom rail explains today’s CPI and a one-line axiom on mean reversion.

---

## 2. Trading universe

### 2.1 Base — Core14 cash (4.0 GA)

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

### 2.2 BOVA index options (4.0 GA)

- **Underlying:** BOVA11
- **Depth:** Near + next monthly; calls + puts from ProfitDLL
- **4.0 adds:** Trade Product templates surface IV context + hedge ratio in narrative, not separate “options mode”

### 2.3 Stock options — Core14 only (4.0 GA)

- Listed options on each of the 14 underlyings
- Liquidity filter unchanged from 3.0
- Structures: covered calls, verticals, collars, BOVA hedge, pairs — max hold ≤ 10 sessions

### 2.4 Phased universe expansion

| Phase | Asset class | Scope | Data source | Execution |
|-------|-------------|-------|-------------|-----------|
| **4.0 GA** | Core14 + BOVA + stock opts | Full cockpit | ProfitDLL | NTSL |
| **4.1** | WINFUT, WDOFUT | Quotes + scanner tags; paper legs | ProfitDLL (preferred) or stub | NTSL if Profit supports; else paper |
| **4.2** | BTC, ETH, SOL | **Watch-only default**; optional paper stub | Binance public REST (quotes); no Clear | **TBD** — Profit if available, else paper only |
| **4.3** | B3 CEI imports | Historical trade notes (research) | Manual export / parser spike | N/A |

**Honest note on Clear:** Clear has **no stable public API**. We explicitly **excluded Clear scrapers** (fragile, ToS risk). Crypto during B3 hours is **not** “trade via Clear in app” — it is **watchlist + paper** until Profit or a dedicated feed path is proven.

---

## 3. Product pillars (4.0)

| # | Pillar | One-liner |
|---|--------|-----------|
| **P1** | **Profit-native cockpit** | P&L, positions, fills, DLL discovery, optional Profit co-start |
| **P2** | **Trade Product blackboard** | One blended view: thesis, economics, odds, legs, chart — not siloed modes |
| **P3** | **Ranked opportunity surface** | Idea score drives watchlist + per-symbol stack sort |
| **P4** | **Risk profile drawer** | Editable limits (R$ 500/day default), position caps, cost/trade, kill rules |
| **P5** | **Market pulse + education** | 33/33/33 bottom rail — news, calendar, lessons with PT tooltips |
| **P6** | **Replay lab (sandbox)** | ProfitChart replay at speed — observe fills, accumulation, gather edges — **not live auto** |

---

## 4. UI map — user sections 0–10 (+ 0.1–0.3)

| Ref | User ask | 4.0 behavior | Phase |
|-----|----------|--------------|-------|
| **0** | `?` tooltips everywhere | `HelpTip` component on KPIs, columns, buttons; `docs/tooltips/` EN + PT hint | 3.0.1 skeleton → 4.0-rc full |
| **0.1** | Risk management panel | `/board/risk` drawer — `RiskProfile` SQLite model | 4.0-alpha |
| **0.2** | P&L without Clear | `GET /api/v1/profit/pnl` + sync; status shows **Profit** not Clear mock | 4.0-alpha |
| **0.3** | B3 / years of history | **4.2** trade archaeology; **4.3** CEI research import | 4.2–4.3 |
| **1** | Watchlist++ | Color by bias; cols: ATR%, est. cost, idea rel %; sort/filter; reset; default = best score | 4.0-alpha |
| **2** | Expand KPIs | Week P&L, win rate, slippage, open risk R$, PF₂₀, margin — in unified strip | 4.0-alpha → 4.0-rc filters |
| **3** | Header rebrand + history | **Arbitragem Scalper**; filterable KPI strip; ranges today/5d/20d/YTD/custom | 4.0-alpha + 4.0-rc |
| **4** | World clocks + smart board | SP, NY, LON, TYO, SHA + open/closed/holiday; Trade Product education fields | 4.0-alpha + 4.0-beta |
| **5** | Toolbar clarity | Rename Scan / Pause all / Integrations + HelpTips; optional first-run tour | 3.0.1 + 4.0-rc |
| **6** | Per-symbol idea stack | Filter by active symbol; card = mini Trade Product + score | 4.0-alpha |
| **7** | One-click structures | Pre-built NTSL packs; chart with entry/stop/target; **Open in Profit** hint | 4.0-beta |
| **8** | Structure → Profit | Builder → blackboard preview → **Arm in Profit** single confirm | 4.0-beta |
| **9** | Notes in board | Merge notes + AI into Trade Product tabs (Thesis \| Chart \| Legs \| Notes) | 4.0-beta |
| **10** | Bottom pulse rail | 33% news snippets, 33% calendar, 33% lessons/axioms | 4.0-beta |

### Assistant suggestions A–J → phases

| ID | Feature | Phase | Notes |
|----|---------|-------|-------|
| **A** | 3.0.1 bugfix sprint | **3.0.1** | DD 100%, chart load, header dedupe, button label |
| **B** | Idea score 0–100 | **4.0-alpha** | `reliability × gate × WF × vol_fit` |
| **C** | Symbol focus mode | **4.0-alpha** | Click watchlist → expand board, filter stack, pre-fill builder |
| **D** | Profit co-start | **4.0-rc** | `dev.py start` optional ProfitChart launch from `.env` path |
| **E** | Catalyst feed | **4.0-beta** stub → **4.1** Twitter/RSS read-only | Never auto-trade from social |
| **F** | Education layer | **4.0-beta** + **4.0-rc** copy | Links STRUCTURES.md + “why vs alternatives” |
| **G** | Paper realism | **4.0-rc** | Expected vs ideal fill on confirm modal |
| **H** | Keyboard shortcuts | **4.0-rc** | `S` scan, `K` kill, `1-9` watchlist, `Enter` top idea |
| **I** | Layout presets v2 | **4.0-rc** | Scalp / Structure / Learn — panel visibility |
| **J** | Odds panel | **4.0-beta** | Historical win rate for pattern × symbol (journal + BT) |

---

## 5. Phased delivery

| Phase | Calendar | Deliverable |
|-------|----------|-------------|
| **3.0.1** | 1 week | Bugfix + HelpTip skeleton + header dedupe → `3.0.1-alpha` |
| **4.0-alpha** | 3 weeks | Risk panel, watchlist cols/sort, Profit P&L stub, clocks, per-symbol stack, idea score |
| **4.0-beta** | 3 weeks | Trade Product blackboard, charts w/ levels, one-click NTSL, bottom pulse rail, replay lab start, odds panel |
| **4.0-rc** | 2 weeks | KPI history filters, education copy, keyboard shortcuts, layout presets v2, Profit co-start, paper realism |
| **4.0.0** | 1 week | Paper week gate, docs, tag **v4.0.0** |
| **4.1** | +2–3 weeks | Twitter/RSS read-only signals + WIN/WDO futures quotes |
| **4.2** | +2–3 weeks | Trade archaeology + crypto watchlist (BTC/ETH/SOL quotes) |
| **4.3** | research | B3 CEI import if stable export path exists |

**Estimated calendar:** **10 weeks** from 3.0.1 start to 4.0.0 GA (aggressive with agent splits). **+4–6 weeks** for 4.1–4.2.

---

## 6. Phase task tables (Supervisor + Worker)

### 3.0.1 — polish

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| A0.1 | Worker | Fix DD display when `max_drawdown_pct` missing | Templates show `—` not 100% |
| A0.2 | Worker | Dedupe header KPIs | Status bar vs risk cockpit — single P&L row |
| A0.3 | Worker | HelpTip skeleton | `partials/help_tip.html` + CSS |
| A0.4 | Worker | Chart load fix | Deferred LW Charts init after HTMX swap |
| A0.5 | Worker | Builder button label/CSS | “New idea” + nowrap in builder row |
| A0.6 | Supervisor | Version bump | `3.0.1-alpha` + test |

### 4.0-alpha — cockpit foundation

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| A4.1 | Supervisor | `RiskProfile` model + API | `GET/PUT /api/v1/risk/profile` |
| A4.2 | Supervisor | Profit P&L sync stub | `GET /api/v1/profit/pnl`, scheduler job |
| A4.3 | Supervisor | Idea score service | `score_idea()` → 0–100 |
| A4.4 | Supervisor | Watchlist enrich API | ATR%, est. cost, top idea score per symbol |
| A4.5 | Supervisor | Per-symbol ideas endpoint | `GET /api/v1/ideas?symbol=PETR4` |
| A4.6 | Supervisor | World clocks API | `GET /api/v1/market/clocks` |
| A4.7 | Supervisor | ProfitDLL detect script | `scripts/detect_profit_dll.py` |
| W4.1 | Worker | Risk drawer UI | HTMX panel from `/board/partials/risk-profile` |
| W4.2 | Worker | Header rebrand + KPI strip v1 | Scalper title, merged metrics |
| W4.3 | Worker | Watchlist columns + sort | Color, vol, cost, score; reset sort |
| W4.4 | Worker | World clocks row | Green/red/yellow market dots |
| W4.5 | Worker | Per-symbol idea stack | Filter on focus symbol |
| W4.6 | Worker | HelpTips on watchlist + cockpit | Wire `docs/tooltips/` keys |

### 4.0-beta — Trade Product + pulse

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| A4.8 | Supervisor | Trade Product schema | `trade_product` fields on idea/board API |
| A4.9 | Supervisor | Chart levels API | Entry/stop/target + max pain overlay data |
| A4.10 | Supervisor | NTSL one-click arm | Export + folder watcher + status |
| A4.11 | Supervisor | Pulse rail feeds | RSS + BCB/B3 calendar stubs |
| A4.12 | Supervisor | Replay lab API v0 | `POST /api/v1/replay/run` → Profit replay job id |
| A4.13 | Supervisor | Odds panel data | Pattern win rate from journal + BT |
| W4.7 | Worker | Trade Product blackboard template | Thesis / economics / odds / legs |
| W4.8 | Worker | Chart overlays | LW Charts price lines for E/S/T |
| W4.9 | Worker | Bottom pulse rail 33/33/33 | Three-column rotating partial |
| W4.10 | Worker | Builder → Arm flow | Single confirm modal |
| W4.11 | Worker | Replay lab UI | Start replay, speed slider, log panel |
| W4.12 | Worker | Odds panel widget | On Trade Product card |

### 4.0-rc — history + habits

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| A4.14 | Supervisor | KPI history service | 3mo min, 2yr target; SQLite rollups |
| A4.15 | Supervisor | Profit co-start | `dev.py` + `.env` `PROFITCHART_EXE` |
| A4.16 | Supervisor | Paper slippage model | Expected fill on confirm payload |
| A4.17 | Supervisor | Education content pack | `data/education/` axioms + structure blurbs |
| W4.13 | Worker | KPI date-range filters | today / 5d / 20d / YTD |
| W4.14 | Worker | Keyboard shortcuts | Document + `board.html` handlers |
| W4.15 | Worker | Layout presets v2 | Learn mode hides idea stack, etc. |
| W4.16 | Worker | First-run tour (optional) | 5-step overlay |
| W4.17 | Worker | Full HelpTip coverage | All sections 0–10 |

### 4.0.0 — GA

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| A4.18 | Supervisor | Paper week gate | Checklist API + journal export |
| A4.19 | Supervisor | Docs | `docs/SCALPER_COCKPIT.md`, update README |
| W4.18 | Worker | GA polish | Performance, empty states, mobile banner |
| Both | Both | Tag v4.0.0 | Release notes + version bump |

### 4.1 — futures + social read-only

| A4.20 | WIN/WDO universe + quotes in watchlist |
| A4.21 | Twitter/RSS ingest → `Signal` read-only cards (no auto-trade) |
| W4.19 | Futures row styling + session badges |
| W4.20 | Social signal chips on pulse rail (news third) |

### 4.2 — archaeology + crypto watch

| A4.22 | Profit CSV history import pipeline |
| A4.23 | Binance quote adapter (BTC/ETH/SOL) |
| A4.24 | Crypto paper stub executor |
| W4.21 | History timeline UI |
| W4.22 | Crypto watchlist section (read-only default) |

### 4.3 — B3 CEI research

| A4.25 | CEI export parser spike |
| W4.23 | Import wizard step “Historical trades” |

---

## 7. Replay lab spec (sandbox)

**Purpose:** Use ProfitChart’s **replay module** to run NTSL against historical sessions at **configurable speed (default 10×)**, observe fills, position buildup, and institutional-style accumulation patterns — **gather edges without risking capital**.

### 7.1 Safety boundaries

| Rule | Detail |
|------|--------|
| **Sandbox only** | Replay jobs never route to live Clear/broker |
| **No silent live auto** | Real-money auto-trade remains **OUT** — 2-step confirm retained |
| **Speed cap** | Config `REPLAY_MAX_SPEED=20` default; user slider 1×–20× |
| **Audit log** | Every replay run → SQLite `replay_runs` with strategy, symbol, period, metrics |
| **Promotion path** | Replay metrics may **suggest** Idea Stack entries; still need backtest gates |

### 7.2 Flow

```
Select NTSL template + symbol + replay file/date range
    → POST /api/v1/replay/run {strategy, symbol, speed, mode: "sandbox"}
    → Profit bridge triggers ProfitChart replay (or manual arm instruction if UI-only)
    → Bridge streams progress % + fill events (SSE)
    → On complete: CSV metrics → parse → replay summary card
    → Optional: "Promote to idea" → walk-forward queue
```

### 7.3 UI (4.0-beta)

- **Replay** tab on symbol panel or Setup drawer
- Speed slider, start/stop, fill log tail
- Highlight: time-of-day fill clusters, net position curve
- Label: **SANDBOX — not live**

### 7.4 Dependencies

- ProfitDLL / ProfitChart replay API availability (document honestly if stub-only in beta)
- Windows PC bridge required
- Falls back to **instruction card** (“Open replay in Profit, load strategy X”) when DLL cannot auto-start replay

---

## 8. Risk profile defaults

Persisted model: `RiskProfile` (SQLite, one row per user/env).

| Field | Default | Tooltip (EN / PT) |
|-------|---------|-------------------|
| `max_daily_loss_brl` | **500** | Max loss per session before kill / block confirm — *Perda máxima diária* |
| `max_open_positions` | 5 | Concurrent structures + scalps — *Posições abertas* |
| `max_cost_per_trade_brl` | 50 | Commission + slippage budget — *Custo por trade* |
| `max_portfolio_net_delta` | 0.5 | From 3.0 — *Delta líquido* |
| `max_sector_pct` | 40 | Single sector notional cap — *Concentração setorial* |
| `max_hold_sessions` | 10 | Aligns with frozen max hold — *Prazo máximo* |
| `kill_on_daily_loss` | true | Auto kill-switch when daily loss breached — *Stop automático* |
| `paper_trading_mode` | true | Until wizard green + explicit live — *Modo simulado* |

**UI:** Risk button (section **0.1**) opens drawer; edits `PUT /api/v1/risk/profile`; cockpit strip shows breach warnings.

---

## 9. KPI catalog

| KPI | Source | History range | Phase |
|-----|--------|---------------|-------|
| Day P&L (R$) | Profit bridge | Today | 4.0-alpha |
| Week P&L | Profit + journal rollup | 5d / 20d | 4.0-rc |
| Win rate (%) | Journal | 3mo → 2yr | 4.0-rc |
| Avg slippage (ticks) | Paper + live fills | 3mo | 4.0-rc |
| Open risk (R$) | Positions × stop distance | Live | 4.0-alpha |
| Net Δ | Risk cockpit | Live | 3.0 (retained) |
| Margin estimate | Bridge stub | Live | 3.0 (retained) |
| PF₂₀ | Last 20 closed trades | 3mo min | 4.0-rc |
| Idea score (top) | Scanner | Live | 4.0-alpha |
| Sector concentration % | Cockpit | Live | 3.0 (retained) |
| Replay edge count | Replay lab | Per run | 4.0-beta |
| Bridge latency ms | Health | 24h | 4.0-alpha |

**Filter UX (4.0-rc):** chip row — Today · 5D · 20D · YTD · Custom (date picker); applies to P&L, win%, PF₂₀ simultaneously.

**Fast path:** ingest whatever Profit exports first (often 3–6 months); backfill 2+ years via CSV archaeology in 4.2.

---

## 10. World clocks spec

| Market | TZ | Display | Status colors |
|--------|-----|---------|---------------|
| B3 (São Paulo) | America/Sao_Paulo | HH:MM | Green open · Red closed · Yellow holiday |
| New York | America/New_York | HH:MM | Pre-market dim green |
| London | Europe/London | HH:MM | |
| Tokyo | Asia/Tokyo | HH:MM | |
| Shanghai | Asia/Shanghai | HH:MM | |

**API:** `GET /api/v1/market/clocks` → `{markets: [{id, label, local_time, status, next_event, minutes_to_open}]}`

**UI:** Compact row under header; `HelpTip` on each clock; mobile = scroll horizontal.

**Data:** `exchange_calendars` or static B3 holiday JSON + US/JP/CN holiday stubs; upgrade to library in rc.

---

## 11. Trade Product blackboard — template fields

Single **Trade Product** card per active symbol (replaces siloed chart / builder / report tabs over time).

| Section | Field | Source |
|---------|-------|--------|
| **Header** | Symbol, side, structure_type, score /100 | Idea + scanner |
| **Thesis** | 2–3 sentence trade thesis | Ollama + template |
| **Economics** | Principle tags (mean reversion, hedge, vol sale) | `rationale_tags[]` |
| **Why not alternatives** | 3 bullets vs other structures | Education pack + Ollama |
| **Odds** | Win rate, PF, DD, sample size | Backtest + journal (J) |
| **Expected gain** | R$ and % at target; max loss at stop | Legs + sizing |
| **Catalysts** | Earnings, macro, sector | Catalyst feed (E) |
| **Chart** | Session LW chart + E/S/T + max pain | W4.8 |
| **Legs** | `legs[]` summary + margin chip | Structure API |
| **AI why** | Short paragraph | Ollama cached 24h |
| **Actions** | Preview · Arm NTSL · Add to journal | 4.0-beta |

**Tabs (progressive):** Thesis | Chart | Legs | Notes — merged per user **§9**.

---

## 12. Bottom pulse rail — 33 / 33 / 33

Replace footer-only sector strip as **primary pulse** (sector heat may compress into watchlist or secondary chip row).

| Third | Content | Source | Refresh |
|-------|---------|--------|---------|
| **33% News** | 2-line headline + “market effect” AI summary | RSS (Valor, InfoMoney stub), BCB | 5–15 min |
| **33% Calendar** | Next 48h events — CPI, FOMC, BCB Copom, earnings Core14 | `data/calendar/` + manual seed | 1h |
| **33% Lessons** | Axiom / theory / tip — rotatable | `data/education/axioms.json` | Daily |

**Layout:** Three equal columns; click expands drawer; `HelpTip` on each column header.

**4.1 addition:** social **read-only** chips appear inside News third — never trigger orders.

---

## 13. ProfitDLL onboarding

User may not know if DLL is installed. **We own discovery.**

### 13.1 Detection (`scripts/detect_profit_dll.py`)

| Step | Action |
|------|--------|
| 1 | Search common paths: `C:\Nelogica\Profit\`, `Program Files\Nelogica\`, registry hint |
| 2 | Find `ProfitDLL.dll` or documented equivalent |
| 3 | Print `PROFIT_DLL_PATH=` line for `.env` |
| 4 | Exit 0 if found, 2 if not (wizard shows manual path picker) |

### 13.2 `dev.py` integration

- On Windows `setup` / `start`: run detector if `PROFIT_DLL_PATH` unset
- Auto-write `.env` when single unambiguous hit
- Log which bridge script selected (`profit_dll_bridge.py` vs stub)

### 13.3 Setup wizard steps

| Step | Check |
|------|-------|
| ProfitChart install | Path exists (optional `PROFITCHART_EXE`) |
| DLL loaded | Bridge `/health` → `mode: dll` |
| Quote sample | PETR4 last not null |
| NTSL export folder | Writable `exports/ntsl/` |
| Replay (beta) | Replay module detected or “manual only” badge |

### 13.4 Docs

- Update `docs/profit_bridge.md` with detection flow
- Screenshot-friendly troubleshooting for “bridge offline”

---

## 14. Explicitly OUT of 4.0.0 GA

| Out of scope | Rationale |
|--------------|-----------|
| **Clear API / scrapers** | No stable API; fragile automation |
| **Live auto-trade without confirm** | Safety — 2-step confirm; **replay sandbox excepted** |
| **Auto-trade from Twitter / social** | Deferred to 4.1 **read-only** signals |
| **Full B3 cash/options universe** | Liquidity + complexity — Core14 only at GA |
| **Crypto live execution** | Path TBD; 4.2 watch/paper only |
| **Multi-month swing primary UX** | Max hold 10 sessions / 2 weeks |
| **Mobile-first Trade Product builder** | Mobile = watchlist + confirm + risk banner |
| **B3 CEI automated login** | Research spike only in 4.3 |
| **Replacement of Profit Tick-a-Tick** | Profit remains backtest source of truth |

**In scope (user clarification):** replay auto-trade at 10× in **sandbox**; phased WIN/WDO + crypto **quotes**; swing **up to** 2 weeks.

---

## 15. Open questions

### Resolved ✅

| Question | Answer |
|----------|--------|
| Max daily loss | **R$ 500** default |
| KPI history depth | **3 months** minimum fast path; **2+ years** ideal |
| ProfitDLL on PC | **Unknown** — detection in scope |
| Bottom rail mix | **33% news / 33% calendar / 33% lessons** |
| Language | **English UI** + PT terms in tooltips |
| Clear for crypto | **No** — Binance public quotes + paper stub |
| Twitter auto-trade | **OUT** until 4.1 read-only |

### Remaining

| # | Question | Default if no answer |
|---|----------|----------------------|
| 1 | ProfitChart install path on Filipe PC | Detector + manual picker |
| 2 | First NTSL templates for replay lab | Top 3 scalp templates from 3.0 journal |
| 3 | VPS cutover for 4.0 or stay local-first? | Local-first; VPS optional rc |
| 4 | Binance geo / rate limits for 4.2 | Public endpoints only; cache 5s |
| 5 | Paper week #3 success criteria | 10 confirms + 3 Trade Products journaled |

---

## 16. Definition of done

### 3.0.1

- [ ] DD shows `—` when `max_drawdown_pct` absent (not 100%)
- [ ] Session chart renders after symbol click (LW Charts visible)
- [ ] Header: no duplicate Day P&L (status vs cockpit merged)
- [ ] HelpTip partial used on ≥3 controls
- [ ] Version `3.0.1-alpha`; tests green

### 4.0-alpha

- [ ] Risk Profile drawer persists defaults (R$ 500/day)
- [ ] Watchlist: vol, cost, score columns + sort + reset
- [ ] Profit P&L in header (stub or live DLL)
- [ ] World clocks row with open/closed state
- [ ] Idea stack filters by active symbol
- [ ] Idea score on cards and watchlist
- [ ] ProfitDLL detect script + wizard step

### 4.0-beta

- [ ] Trade Product blackboard template live for Core14
- [ ] Chart entry/stop/target overlays
- [ ] One-click NTSL arm flow
- [ ] Bottom pulse rail 33/33/33
- [ ] Replay lab v0 (sandbox) — start + log + metrics
- [ ] Odds panel on Trade Product

### 4.0-rc

- [ ] KPI history filters (today / 5d / 20d / YTD)
- [ ] Education copy on structures
- [ ] Keyboard shortcuts documented + working
- [ ] Layout presets v2 (Scalp / Structure / Learn)
- [ ] Profit co-start optional
- [ ] Paper realism on confirm modal

### 4.0.0 (GA)

- [ ] Paper week #3 signed off
- [ ] `docs/SCALPER_COCKPIT.md` + README updated
- [ ] Tag **v4.0.0**
- [ ] All HelpTips on sections 0–10
- [ ] Kill switch + risk gates verified with Profit stub + DLL path

### 4.1 / 4.2 / 4.3 (follow-on)

- [ ] 4.1: WIN/WDO quotes + RSS/Twitter read-only signals
- [ ] 4.2: Trade archaeology import + BTC/ETH/SOL watchlist
- [ ] 4.3: B3 CEI research import spike doc

---

## 17. Paste-into-agent prompts

### Supervisor (Alpha) — start 4.0-alpha

```
Sprint: 4.0-alpha — Scalper Cockpit foundation.
Read RELEASE_4.0.0.md §6 (4.0-alpha table).

Priority order:
A4.7 ProfitDLL detect script + dev.py hook
A4.1 RiskProfile model + GET/PUT /api/v1/risk/profile
A4.2 GET /api/v1/profit/pnl + sync job
A4.3 idea score service
A4.4 watchlist enrich endpoint
A4.5 per-symbol ideas filter
A4.6 GET /api/v1/market/clocks

Tests for each endpoint. After API: python scripts/dev.py restart --wait
Do not touch src/web/ except API contracts in docs/agent_integration.md
```

### Worker — start 4.0-alpha (after A4.1–A4.6 stubs)

```
Sprint: 4.0-alpha — Scalper Cockpit UI.
Read RELEASE_4.0.0.md §4 UI map + §10 clocks.

Priority:
W4.2 header rebrand "Arbitragem Scalper" + merged KPI strip
W4.1 risk drawer HTMX
W4.3 watchlist columns/sort
W4.4 world clocks row
W4.5 per-symbol idea stack on focus
W4.6 HelpTips from docs/tooltips/

Test at http://localhost:8000/board after python scripts/dev.py start --wait
```

### Both — 3.0.1 hotfix (now)

```
Sprint: 3.0.1 polish per RELEASE_4.0.0.md §16 (3.0.1).
Fix DD default, chart init, header dedupe, HelpTip skeleton, builder button.
Bump __version__ to 3.0.1-alpha. pytest tests/ -q. Commit + push.
```

---

## 18. Dependency map

```
A4.7 DLL detect ──► A4.2 Profit P&L ──► W4.2 header KPI strip
A4.1 RiskProfile ──► W4.1 risk drawer ──► cockpit gate warnings
A4.3 idea score ──► A4.4 watchlist enrich ──► W4.3 watchlist UI
A4.5 symbol ideas ──► W4.5 stack filter (focus mode C)
A4.8 Trade Product API ──► W4.7 blackboard template ──► W4.8 chart levels
A4.12 replay API ──► W4.11 replay UI (sandbox only)
A4.14 KPI history ──► W4.13 date filters
A4.11 pulse feeds ──► W4.9 bottom rail 33/33/33
```

---

## 19. Timeline estimate

| Milestone | Duration (weeks) | Cumulative |
|-----------|------------------|------------|
| **3.0.1** polish | 1 | 1 |
| **4.0-alpha** | 3 | 4 |
| **4.0-beta** | 3 | 7 |
| **4.0-rc** | 2 | 9 |
| **4.0.0** GA | 1 | **10** |
| **4.1** futures + social | 2–3 | 12–13 |
| **4.2** archaeology + crypto | 2–3 | 14–16 |
| **4.3** CEI research | spike | — |

**Realistic target:** **10 weeks** 3.0.1 → 4.0.0 GA.  
**Conservative:** 13 weeks if ProfitDLL replay API is stub-only through beta.

---

## 20. Release strategy — after 3.0

| Release | When | Purpose |
|---------|------|---------|
| **3.0.1** | Now | Screenshot bugs, tooltips skeleton, header dedupe |
| **4.0-alpha** | +1 week | Risk drawer, watchlist++, clocks, Profit P&L |
| **4.0-beta** | +4 weeks | Trade Product, pulse rail, replay lab start |
| **4.0-rc** | +7 weeks | KPI history, shortcuts, education |
| **4.0.0** | +10 weeks | Paper week #3 + tag GA |
| **4.1+** | +12 weeks | Futures, social read-only, archaeology, crypto watch |

**Recommendation:** Complete 3.0.1 before alpha so Filipe’s daily board use isn’t blocked by DD/chart/header noise. Use journal from 3.0 paper week to order Trade Product templates (energy vs banks vs steel).

---

*Last updated: 2026-06-16 — frozen scope for Filipe review. Implementation starts with 3.0.1-alpha.*

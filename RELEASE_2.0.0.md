# Release 2.0.0 — Scope **FROZEN** ✅

**Frozen:** 2026-06-13 · Filipe decisions applied · **Released 2.0.0**

| # | Decision |
|---|----------|
| 1 | **Stock options + BOVA index options** (chain from Profit) |
| 2 | **Execution: NTSL via Profit**, confirmed in app → export + arm in ProfitChart |
| 3 | **Backtest gate:** PF ≥ 1.3, max DD ≤ 8% |
| 4 | **Topology:** VPS dashboard + Windows PC Profit bridge (Tailscale) |
| 5 | **No Telegram confirm** — screen watch during live |

**Prerequisite:** Tag **v1.0.0** and use paper; **v2.0.0** ships blackboard + NTSL confirm flow.

**Primary UI:** http://localhost:8000/board (HTMX blackboard)  
**Legacy UI:** http://localhost:8501 (Streamlit, maintenance mode)

---

# Release 2.0.0 — Scope (draft)

**Codename:** *Blackboard*  
**Prerequisite:** Ship and use **1.0.0** in paper mode first.  
**Focus:** Filipe’s liquid IBOV watchlist — **cash + BOVA index options** — with ProfitChart-native workflow, opportunity detection, and confirmed 1-click execution.

---

## 1. Trading universe (frozen for 2.0)

### 1.1 Cash equities (14)

| Symbol | Sector | Notes |
|--------|--------|--------|
| PETR4 | Energia | Anchor tape, high liquidity |
| VALE3 | Mineração | Commodity beta |
| PRIO3 | Energia | Pair / corr with PETR4 |
| ITUB4 | Financeiro | Bank basket |
| BBAS3 | Financeiro | Bank basket |
| BBDC4 | Financeiro | Bank basket |
| BBSE3 | Financeiro | Insurance / fin |
| B3SA3 | Financeiro | Market infra |
| ABEV3 | Consumo | Defensive |
| GGBR4 | Siderurgia | Steel basket |
| CSNA3 | Siderurgia | Steel basket |
| USIM5 | Siderurgia | Steel basket |
| SUZB3 | Papel | Pulp |
| WEGE3 | Industrial | Quality growth |

**Config:** `SCANNER_MODE=filipe_core14` · `data/filipe_core14.csv`

### 1.2 BOVA index options

- **Underlying:** BOVA11 (IBOV ETF)
- **Scope:** Near-term monthly series (calls + puts), auto-discovered from Profit bridge option chain — not a static hardcoded list.
- **Use cases:** Index hedge, directional IBOV scalps, covered structures vs cash basket.
- **Config:** `SCANNER_INCLUDE_BOVA_OPTIONS=true` · chain refresh from ProfitDLL.

### 1.3 Out of scope for 2.0

- Full B3 options universe
- Small caps / illiquid names
- Overnight / swing multi-day (primary UX remains **intraday scalping**)

---

## 2. Product vision — “editable blackboard”

Replace the current “dashboard of pages” with a **single workspace** that feels like ProfitChart: dark, dense, panels you arrange.

### 2.1 Layout (target)

```
┌─────────────────────────────────────────────────────────────────┐
│ STATUS BAR  PAPER/LIVE · P&L · margin · connectors · clock    │
├──────────┬──────────────────────────────────────┬───────────────┤
│ WATCHLIST│  MAIN BLACKBOARD (per symbol)        │ IDEA STACK    │
│ 14+BOVA  │  chart · tape · levels · notes       │ ranked ideas  │
│ drag pin │  [user + AI annotations]             │ confirm → send│
├──────────┴──────────────────────────────────────┴───────────────┤
│ SCANNER STRIP · sector heat · corr mini-map · alerts            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Blackboard behaviors

| Feature | Description |
|---------|-------------|
| **Pinned symbols** | Click watchlist → expands blackboard for that symbol |
| **Editable notes** | Text sticks on board (user + AI); saved per symbol/day |
| **Draw levels** | Horizontal lines: entry, stop, target (stored, sent with order) |
| **Panel layout** | Resizable columns; layout persisted in SQLite / browser |
| **ProfitChart parity** | Near-black `#0c0c0c`, amber actions, mono prices, compact tables |

### 2.3 Tech direction

| Layer | 1.0 | 2.0 |
|-------|-----|-----|
| UI | Streamlit | **HTMX + Jinja** on FastAPI *or* lightweight React shell |
| Charts | Plotly | **Lightweight Charts** or Plotly with Profit-like theme |
| Real-time | Poll | **SSE/WebSocket** from bridge for quotes |

Streamlit **retired** for primary workspace (keep optional admin view if needed).

---

## 3. Data & opportunity engine

Goal: surface **actionable** setups, not just raw quotes.

### 3.1 Live data (per symbol)

| Data | Source (priority) |
|------|-------------------|
| Last, bid/ask, spread | ProfitDLL bridge |
| Volume, session VWAP | Profit bridge / derived |
| Option chain (BOVA) | ProfitDLL |
| Positions, day P&L | Clear API + Profit fills |
| Time & sales (tape) | ProfitDLL (if exposed) |

### 3.2 Opportunity signals (scanner v2)

| Signal | Use |
|--------|-----|
| Relative volume vs 30d | Spike detection |
| VWAP reclaim / loss | Scalp bias |
| Sector correlation break | Pairs (PETR/PRIO, GGBR/CSNA/USIM) |
| IBOV beta divergence | Stock vs index |
| Spread compression | Entry quality |
| Option IV skew (BOVA) | Hedge / directional options ideas |

**Output:** `TradeIdea` object — symbol, structure type, side, legs, entry/stop/target, reliability, expiry (options), rationale tags.

### 3.3 Structure types (ideas)

| Type | Example |
|------|---------|
| **Scalp long/short** | Cash equity, ticks stop/target |
| **Pair / relative** | Long PRIO3 / short PETR4 (mean reversion) |
| **Index hedge** | Long BOVA put vs long cash basket |
| **Covered / collar** | BOVA call vs BOVA11 shares (if held) |
| **Sector basket** | Banks weak → short ITUB4 + BBDC4 hedge with BOVA call |

Each idea = **structured legs[]** ready for Clear API or Profit automation.

---

## 4. ProfitChart integration (deep)

This is the main differentiator for 2.0.

### 4.1 Automated backtest loop

```
NTSL template per pattern
    → Profit bridge runs backtest (tick or 1min)
    → CSV / JSON results
    → Arbitragem scores (win%, PF, max DD)
    → If passes thresholds → promote to "Idea Stack"
    → Ollama writes human summary on blackboard
```

| Task | Detail |
|------|--------|
| **P4.1** | Profit bridge: `POST /backtest/run` {strategy, symbol, period} |
| **P4.2** | Watch folder: Profit exports CSV → auto-ingest (no manual upload) |
| **P4.3** | Per-symbol NTSL library in `strategies/ntsl/{symbol}/` |
| **P4.4** | Nightly job: backtest top 3 patterns × 14 symbols (queue, rate-limited) |
| **P4.5** | Dashboard: “Backtest proof” badge on each idea (PF, trades, DD) |

### 4.2 Idea generation from backtests

- Rank parameter sets from walk-forward on Profit exports
- Map winning NTSL params → live scanner thresholds
- **Reject** ideas that fail min trades / max DD / paper slippage rules

### 4.3 What we cannot fully automate (honest)

- ProfitChart UI itself is not embeddable — **side-by-side** or **bridge API** only
- Full tick backtest speed depends on your PC + Profit license
- Some ProfitDLL callbacks require Nelogica docs / support

---

## 5. AI layer (per symbol)

### 5.1 Symbol report card (on blackboard)

Generated on demand + cached 24h:

| Section | Content |
|---------|---------|
| **Tape read** | Today’s behavior vs 30d |
| **Strengths / weaknesses** | Liquidity, spread, trend, sector |
| **Catalysts** | Earnings, dividends, macro (PETR/VALE oil-iron) |
| **Projection** | Short horizon bias (not financial advice — labeled) |
| **Backtest summary** | Best NTSL pattern last 90d from Profit |
| **Suggested structures** | 1–3 ideas with legs, linked to Idea Stack |

**Prompt context:** scanner tags + latest backtest + open position + sector peers.

### 5.2 Ollama vs batch

- **On-demand:** “Analyze PETR4” button on blackboard
- **Scheduled:** Morning brief for all 14 + BOVA (Telegram/Discord optional)

---

## 6. Execution — 1-click on confirmation

### 6.1 Flow

```
Idea Stack → [Review] → modal shows legs, risk, notional
         → [Confirm] → pre-trade risk check
         → Clear API order(s) OR Profit automation
         → Journal auto-entry + screenshot of board state
```

### 6.2 Safety gates (required before live)

| Gate | Rule |
|------|------|
| Paper default | `PAPER_TRADING_MODE=true` until explicit opt-in |
| Confirm modal | No one-click without second click + PIN optional |
| Risk manager | Daily loss, max contracts, sector concentration |
| BOVA options | Extra margin check vs Clear summary |
| Kill switch | Sidebar “STOP ALL” → pause strategies + block orders |

### 6.3 Execution backends

| Backend | When |
|---------|------|
| **Clear Smart Trader API** | Live cash + listed options |
| **Profit automation** | NTSL strategies already in ProfitChart |
| **Paper simulator** | Log intent, mark P&L from quotes |

---

## 7. Credentials & integration wizard

In-app **Settings → Connect accounts** (step-by-step). Agents auto-detect what they can.

### 7.1 Auto-detect (no Filipe action)

| Check | How |
|-------|-----|
| Profit bridge up | `GET localhost:9100/health` |
| ProfitDLL path exists | `PROFIT_DLL_PATH` file check |
| Clear mock vs live | Keys present in `.env` |
| Ollama | `/api/tags` |

### 7.2 Filipe must provide (wizard explains where)

#### Clear Corretora — Smart Trader API

| Field | Where to find |
|-------|----------------|
| `CLEAR_API_KEY` | Clear → Área do cliente → **Smart Trader** / API → Gerar chave *(or ask assessor)* |
| `CLEAR_API_SECRET` | Same portal, shown once at creation |
| `CLEAR_ACCOUNT_ID` | Conta Clear (número da conta) or API account list endpoint |

**If API not enabled:** wizard shows email template to assessor + link to Clear support.  
**Doc:** `docs/CLEAR_API_SETUP.md` (expand with screenshots in 2.0).

#### ProfitChart / Nelogica

| Field | Where to find |
|-------|----------------|
| `PROFIT_DLL_PATH` | Usually `C:\Nelogica\Profit\ProfitDLL.dll` after Profit install |
| Activation | Profit aberto + logado na mesma máquina do bridge |
| Módulo automação | Required for backtest + order routing |
| NTSL export path | Profit → Editor de Estratégias → export folder |

**Wizard action:** “Test bridge” → quotes for PETR4 + BOVA chain sample.

**Doc:** `docs/profit_bridge.md` + new `docs/PROFIT_SETUP_WIZARD.md`

### 7.3 Agent self-service limits

- Cannot log into Clear/Profit for you (credentials + 2FA)
- **Can:** probe ports, validate DLL, run stub, parse exports, patch `.env.example`, open browser to docs URLs

---

## 8. Suggested additions (Supervisor recommendations)

Items not in your list that strongly support 2.0 goals:

| # | Feature | Why |
|---|---------|-----|
| S1 | **Sector baskets** | Banks / steel / energy group signals + hedges |
| S2 | **IBOV regime banner** | “Risk-on/off” from BOVA11 trend affects all ideas |
| S3 | **Idea lifecycle** | `detected → backtested → confirmed → executed → reviewed` |
| S4 | **Morning playbook** | 08:55 auto-scan + AI brief before open |
| S5 | **Slippage model** | Paper fills use spread + 1 tick — realistic before live |
| S6 | **Correlation mini-map** | 14×14 heatmap on blackboard footer |
| S7 | **Event flags** | Dividend ex-date, earnings (manual CSV or B3 calendar API later) |
| S8 | **Telegram confirm** | Optional: confirm trade from phone before Clear send |
| S9 | **Board snapshots** | Export PNG/PDF of blackboard + idea for journal |
| S10 | **Versioned layouts** | Save “scalp layout” vs “options hedge layout” |

---

## 9. Phased delivery inside 2.0

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **2.0-alpha** | Core14 universe + blackboard shell (HTMX) + watchlist + Idea Stack API | **Done** |
| **2.0-beta** | Profit backtest run + CSV watcher + sector pairs | **Done** |
| **2.0-rc** | Backtest badges + confirm modal + setup wizard + sector strip | **Done** |
| **2.0** | Clear live execution + SSE quotes + AI reports + kill switch | **In progress** (GA: lifecycle, Clear live, mobile) |

**Try alpha now:** `http://localhost:8000/board` (API must be running)

---

## 10. Definition of done (2.0.0)

- [x] 14 symbols universe (`filipe_core14.csv`, `SCANNER_MODE=filipe_core14`)
- [x] Blackboard workspace at `/board` (HTMX partials)
- [x] Per-symbol panel: quote, notes placeholder
- [x] `TradeIdea` model + `/api/v1/ideas` + confirm (paper)
- [x] BOVA option chain stub (`GET /options/bova` on bridge)
- [x] Integration wizard (`/setup/status`, `/setup/test`)
- [x] Profit auto-backtest → idea promotion pipeline (export watcher + `attach_backtest_proof`)
- [x] Scanner emits ideas with backtest proof badge (sector pairs + CSV promote)
- [x] Idea Stack 2-step confirm UI (modal on `/board`)
- [x] SSE quote stream on blackboard watchlist (A2.8 / W2.1)
- [x] AI symbol report panel (A2.9 / W2.5)
- [x] Paper execute + kill switch wired (A2.6a/c / W2.4)
- [ ] Clear live execution with journal sync (A2.6b)
- [ ] Idea lifecycle gates enforced end-to-end (A2.10)
- [ ] Load time &lt; 1s perceived (SSE tuning)
- [ ] Mobile: watchlist + confirm only (W2.9)

---

## 11. Task split (Supervisor + Worker)

**Rule:** Supervisor owns `src/`, `scripts/`, `tests/`, `dashboard/api_cache.py`. Worker owns `dashboard/views/`, `dashboard/scanner_ui.py`, `dashboard/components/` (except `api_cache`), `src/web/` (HTMX blackboard).

**Coordination:** When Supervisor ships an API, update `docs/agent_integration.md` and ping Worker with endpoint + sample JSON. Worker never imports `src/` in Streamlit — HTTP only.

**Parallel rule (mandatory):** Supervisor picking **A2.x** → Worker starts mapped **W2.x** same sprint. See [AGENTS.md § Parallel release protocol](AGENTS.md#parallel-release-protocol-mandatory).

---

### 11.1 Parallel kickoff matrix

Status as of **2.0-rc complete → GA sprint**. ✅ = shipped · 🔲 = remaining.

| Supervisor | Worker | Before API? | Sup | Worker |
|------------|--------|-------------|-----|--------|
| A2.4a `POST /backtest/run` | W2.8 backtest proof badge | yes | ✅ | ✅ |
| A2.4b CSV export watcher | W2.8 badge from `backtest_proof` | no | ✅ | ✅ |
| A2.5a sector correlation pairs | W2.7 sector strip + corr mini-map | yes | ✅ | ✅ |
| A2.5b VWAP reclaim signal | W2.2 symbol panel VWAP | yes | 🔲 | 🔲 |
| A2.8 SSE `/stream/quotes` | W2.1 watchlist SSE | yes | ✅ | ✅ |
| A2.9 `GET /symbols/{sym}/report` | W2.5 report panel tab | no | ✅ | ✅ |
| A2.10 idea lifecycle gates | W2.4 modal states + gate UX | yes | 🔲 | 🔲 |
| A2.6a paper `POST /ideas/{id}/execute` | W2.4 execute after confirm | no | ✅ | ✅ |
| A2.6b Clear order router | W2.4 live confirm + risk copy | no | 🔲 | 🔲 |
| A2.6c `POST /risk/kill-switch` | W2.4 sidebar STOP ALL | yes | ✅ | ✅ |
| A2.7 `/setup/status` *(alpha)* | W2.6 setup wizard UI | yes | ✅ | ✅ |
| — | W2.3 board notes persist | yes | — | 🔲 |
| — | W2.9 mobile watchlist + confirm | yes | — | 🔲 |
| — | W2.10 Streamlit ↔ board link | yes | — | 🔲 |

**GA remaining (both agents):** A2.5b, A2.10, A2.6b · W2.3, W2.9, W2.10 · W2.4 live path after A2.6b.

---

### ✅ Done (2.0-alpha)

| ID | Owner | Task | Artifact |
|----|-------|------|----------|
| A2.1 | Supervisor | Core14 universe | `data/filipe_core14.csv`, `SCANNER_MODE=filipe_core14` |
| A2.2 | Supervisor | BOVA chain stub | `GET /options/bova`, `get_bova_option_chain()` |
| A2.3 | Supervisor | TradeIdea API | `/ideas`, `/ideas/generate`, `/ideas/{id}/confirm` |
| A2.7 | Supervisor | Setup wizard API | `/setup/status`, `/setup/test` |
| W2.1 | Worker | Blackboard shell | `/board`, `src/web/templates/`, `blackboard.css` |
| W2.2 | Worker | Watchlist + symbol panel | HTMX partials, click → quote panel |

---

### 🔵 Now — GA sprint (2.0-rc done → 2.0.0)

#### Supervisor (Alpha) — start here

| P | ID | Task | Deliverable | Blocks |
|---|-----|------|-------------|--------|
| P0 | **A2.4a** | Profit bridge `POST /backtest/run` | `scripts/profit_bridge_stub.py` + client method; returns job id + metrics JSON | W2.4 badges |
| P0 | **A2.4b** | Export folder watcher | Watch `exports/profit/*.csv` → auto-ingest + link to `TradeIdea.backtest_proof` | Idea promotion |
| P1 | **A2.5a** | Scanner v2 — sector correlation | Pair signals (PETR/PRIO, GGBR/CSNA/USIM) in `TradeIdea` | W2.7 heatmap data |
| P1 | **A2.5b** | Scanner v2 — VWAP reclaim | Use quote history or session VWAP from bridge | Symbol panel |
| P1 | **A2.8** | SSE quote stream | `GET /stream/quotes` for Core14; blackboard watchlist subscribes | W2.1 perf |
| P2 | **A2.9** | AI symbol report API | `GET /symbols/{sym}/report` (Ollama + scan + backtest context) | W2.5 |
| P2 | **A2.10** | Idea lifecycle states | `detected → backtested → confirmed → executed`; gate on `backtest_min_profit_factor` | W2.4 modal |
| P3 | **A2.6a** | Paper execution service | `POST /ideas/{id}/execute` → journal entry + slippage model (S5) | W2.4 |
| P3 | **A2.6b** | Clear order router | `place_order()` for live when `PAPER_TRADING_MODE=false` | 2.0 GA |
| P3 | **A2.6c** | Kill switch API | `POST /risk/kill-switch` blocks all confirms | Sidebar + board |

**Supervisor test bar:** `pytest tests/ -q` after each task. Restart: `python scripts/dev.py restart --wait`.

#### Worker — start here (no backend blockers)

| P | ID | Task | Deliverable | Needs from Supervisor |
|---|-----|------|-------------|----------------------|
| P0 | **W2.3** | Board notes persist | `localStorage` or `POST /board/notes/{sym}` if A adds route | Optional API |
| P0 | **W2.4** | Idea Stack confirm modal | 2-step HTMX modal → `POST /ideas/{id}/confirm` | ✅ API exists |
| P1 | **W2.6** | Setup wizard UI | Settings page or `/board/setup` using `/setup/status` | ✅ API exists |
| P1 | **W2.5** | AI report panel | Symbol panel tab “Report” → `/symbols/{sym}/report` | A2.9 |
| P2 | **W2.7** | Sector strip + corr mini-map | Footer on `/board`; data from `/universe/filipe-core14` + future corr API | A2.5a |
| P2 | **W2.8** | Backtest proof badge | Idea card shows PF/DD when `backtest_proof` set | A2.4b |
| P3 | **W2.9** | Mobile board | Watchlist + confirm only; hide center panel &lt;768px | W2.4 |
| P3 | **W2.10** | Streamlit ↔ board link | Home status bar links to `/board`; deprecate duplicate watchlist slowly | — |

**Worker test bar:** refresh `http://localhost:8000/board` and `http://localhost:8501`.

---

### Dependency map (who waits on whom)

```
A2.4 backtest run ──► A2.4b watcher ──► A2.10 lifecycle ──► W2.8 badges
A2.9 symbol report ────────────────────────────────────────► W2.5 panel
A2.5 sector corr ──────────────────────────────────────────► W2.7 heatmap
A2.8 SSE quotes ───────────────────────────────────────────► W2.1 faster watchlist
A2.6 paper execute ────────────────────────────────────────► W2.4 live path
```

**No wait:** W2.3, W2.4 (paper confirm), W2.6 can ship today.

---

### Paste into Supervisor chat

```
You are Supervisor (Alpha). Read AGENTS.md + RELEASE_2.0.0.md §11–§11.1.
2.0-rc is done (SSE, reports, execute, kill switch). GA sprint: A2.5b → A2.10 → A2.6b.
When you pick A2.x, Worker MUST start mapped W2.x in parallel (§11.1 matrix).
Do NOT touch src/web/ or dashboard/views/. Update docs/agent_integration.md per endpoint.
Run pytest after each task. python scripts/dev.py restart --wait after API changes.
```

### Paste into Worker chat

```
You are Worker (Beta). Read AGENTS.md + RELEASE_2.0.0.md §11–§11.1.
When Supervisor starts A2.x, start mapped W2.x immediately unless §11.1 "Before API?" = no.
GA sprint: W2.3 notes → W2.10 board link → W2.9 mobile; W2.4 live path when A2.6b ships.
Own src/web/ and dashboard/views/. Do NOT edit src/api/ or api_cache.py.
Wire endpoints via HTMX or cached_get() only. Test http://localhost:8000/board.
```

---

## 12. Release strategy — 1.0 now, 2.0 next

| Release | When | Purpose |
|---------|------|---------|
| **1.0.0** | **Now** | Paper lab, scan, journal, learn the 14 names daily |
| **1.1** | Optional | HTMX prototype of watchlist only |
| **2.0.0** | 6–10 weeks | Blackboard + Profit backtests + live-ready execution |

**Recommendation:** Tag **v1.0.0** this week. Use it to validate which of the 14 you actually trade. Feed that into 2.0 prioritization (e.g. steel basket vs banks first).

---

## 13. Open questions for Filipe

1. **Options:** BOVA only, or also stock options (PETR4 calls) in 2.0?
2. **Execution default:** Clear API vs Profit NTSL automation — which is primary?
3. **Backtest bar:** Min profit factor / max DD to promote an idea?
4. **VPS vs local:** Dashboard on VPS with bridge on Windows PC — confirm topology?
5. **Telegram confirm** for live orders — wanted?

---

*Last updated: scope draft for Filipe review. No implementation until 1.0.0 tagged.*

# Release 1.0.0 — IBOV Top 20 Scalping Focus

**Goal:** Working dashboard that scans the **top 20 IBOV stocks by 30-day average volume**, pulls live data from **ProfitPro/ProfitChart**, generates **scalping insights** (short trades, seconds-to-minutes), and is ready for Filipe to test.

**Current version:** `1.0.0`

---

## Task split (paste into each agent chat)

### Agent A — Backend & Profit Integration

| # | Task | Priority | Details |
|---|------|----------|---------|
| A1 | **IBOV Top 20 universe** | P0 | `src/services/ibov_universe.py` — static/curated list of top 20 IBOV by 30d avg volume (PETR4, VALE3, ITUB4, BBDC4, BOVA11, etc.). Export via `GET /universe/ibov-top20`. Refresh weekly via config or CSV in `data/ibov_top20.csv`. |
| A2 | **ProfitPro bridge live** | P0 | Start `scripts/profit_bridge_stub.py` (or real DLL) on port 9100. Set `PROFIT_BRIDGE_ENABLED=true` in `.env`. Verify `GET /health` shows Profit ✅. Extend stub with per-symbol quotes for all 20 tickers. |
| A3 | **Scanner → Top 20** | P0 | Change `PatternScanner` to scan full IBOV top 20 (not only BOVA). Config: `SCANNER_MODE=ibov_top20`. Rank by volume + spike score. |
| A4 | **Scalping pattern engine** | P0 | Detect short-term patterns: volume spike, spread compression, momentum burst, VWAP reclaim. Tag `scalp_long` / `scalp_short`. Score `reliability` 0–100. |
| A5 | **Insights API** | P0 | `GET /scanner/insights` — top 5 scalp candidates today with symbol, side bias, pattern, reliability, suggested stop/target ticks. `POST /scanner/run` triggers Ollama summary per candidate. |
| A6 | **Ollama scalping prompts** | P1 | Update `ollama_client.py` system prompt: IBOV cash equities, seconds-to-minutes holds, tight stops, no overnight. |
| A7 | **dev.py auto-start Profit bridge** | P1 | `scripts/dev.py start` also launches profit bridge if `PROFIT_BRIDGE_ENABLED=true`. |
| A8 | **Tests + version bump** | P1 | Tests for universe + scanner. Bump `src/__init__.py` to `1.0.0` when A1–A5 done. |

**Agent A — start command:**
```bash
python scripts/dev.py start --wait
python scripts/profit_bridge_stub.py   # separate terminal until A7
python scripts/run_scanner.py
```

---

### Agent B — Frontend & UX (this agent)

| # | Task | Priority | Details |
|---|------|----------|---------|
| B1 | **Fix blank dashboard** | P0 | ✅ Done — renamed `dashboard/pages/` → `dashboard/views/`. Restart: `python scripts/dev.py restart --wait` |
| B2 | **IBOV Top 20 Scanner UI** | P0 | Scanner page: ranked table of 20 symbols, reliability bar, long/short bias chips, volume heatmap. |
| B3 | **Insights page / panel** | P0 | New **Scalp Insights** section on Home + Scanner: top 5 picks, one-click "Ask Ollama" per symbol. |
| B4 | **Home dashboard** | P0 | Replace BOVA-only copy with IBOV top 20 summary cards + link to scanner. |
| B5 | **Profit status widget** | P1 | Settings: test Profit bridge connection, show green/red, auto-enable instructions. |
| B6 | **Mobile + dark polish** | P1 | Ensure top 20 table scrolls on phone; chart heights responsive. |
| B7 | **1.0.0 release notes** | P1 | README section "What's new in 1.0.0" + ask Filipe to test checklist. |

**Agent B — depends on Agent A:**
- B2/B3 need `GET /universe/ibov-top20` and `GET /scanner/insights` (can mock until A ships).

**Agent B — start command:**
```bash
python scripts/dev.py start --wait --open
```

---

# Release 1.0.0 — IBOV Top 20 Scalping ✅

**Status: READY FOR FILIPE TO TEST** (version `1.0.0`)

## What 1.0.0 can do

For Filipe — here's what the dashboard does today, in plain language:

- **See your account at a glance** — balance, today's profit/loss, and margin on the Home page (paper mode until you add Clear API keys).
- **Scan the 20 busiest IBOV stocks** — one click runs volume + momentum analysis on PETR4, VALE3, ITUB4, BOVA11, and the rest of the top-20 list.
- **Get scalp trade ideas** — ranked picks with long/short/neutral bias, reliability score, and suggested stop/target in ticks.
- **Read pattern alerts** — volume spikes, momentum bursts, VWAP reclaim, and similar tags on the Daily Scanner charts and table.
- **Ask Ollama for a quick plan** — 30-second scalp entry/stop/target suggestions for any top symbol.
- **Sync your journal** — import trades from Clear and Profit into one place.
- **Backtest and optimize** — upload Profit CSV exports or run Python grid search to compare strategies.
- **Run strategies on a schedule** — the API can scan daily; Profit bridge connects to ProfitChart for live quotes.
- **Start everything with one command** — `python scripts/dev.py start --wait --open` boots API, dashboard, and Profit bridge stub.

---

## Shared definition of done (1.0.0)

- [x] Profit bridge auto-starts via `dev.py` (stub on :9100)
- [x] Scanner runs on **20 IBOV symbols** (`SCANNER_MODE=ibov_top20`)
- [x] Dashboard shows **ranked scalp candidates** with reliability score
- [x] Ollama generates **scalping insights** for top picks
- [x] Home + Scanner pages wired
- [x] `python scripts/dev.py start --wait` works
- [x] Journal syncs **Clear + Profit** trades
- [x] BOVA options on watchlist (`SCANNER_INCLUDE_BOVA_OPTIONS`)
- [ ] **Filipe manual test** — see checklist below

---

## Filipe test checklist (after 1.0.0)

1. Run `python scripts/dev.py start --wait --open`
2. Confirm sidebar: **Profit 🟢** (ProfitPro open + bridge running)
3. Open **Daily Scanner** → click **Run Scan Now**
4. See **20 symbols** ranked with patterns
5. Open **Home** → see top scalp alerts
6. Open **Ollama Insights** → quick prompt on a top symbol
7. Report: does the insight feel useful for scalping?

---

## Paste this into Agent A's chat

```
You are Agent A. Read RELEASE_1.0.0.md in the repo. Implement tasks A1–A8 in order.
Focus: IBOV top 20 by 30d volume, ProfitPro bridge on port 9100, scalping pattern detection,
GET /scanner/insights API. Coordinate with Agent B who owns UI. Bump to 1.0.0 when done.
Start by running: python scripts/dev.py start --wait
```

## Paste this into Agent B's chat (or continue here)

```
You are Agent B. Read RELEASE_1.0.0.md. Implement B1–B7. Wire UI to Agent A's endpoints.
Focus: IBOV top 20 scanner charts, scalp insights panel, fix blank pages.
When Agent A ships /scanner/insights, integrate immediately. Ask Filipe to test at 1.0.0.
```

---

## Known issue (fixed by B1)

Streamlit was loading `dashboard/pages/*.py` as separate routes (blank screen on "home").
Views live in `dashboard/views/` now — only `app.py` is the entry point.

# Release 7.0 — Golden Path Perfection (local-first)

## Vision

**One symbol (PETR4) flawless end-to-end on Filipe's PC — then replicate, never the reverse.**

---

## Prerequisites (5.x / 6.x must be green)

| Release | Must ship | Why 7.0 depends on it |
|---------|-----------|------------------------|
| **5.0** | Trader Desk, motor journal, launcher, Phase A/B paper | Journal is the truth layer for golden-path gates |
| **5.1** | Fast shell, staged HTMX, kill-desk SSE full HTML, shared cache | First paint & desk refresh must not block motor RAM |
| **5.2** | Snapshot worker, trust scorecard | Scorecard feeds golden-path checklist + symbol factory lock |
| **6.0** | Profit DLL read-only quotes + positions | PETR4 tape and blotter must match Profit without stub drift |
| **6.1** | Profit DLL write orders on Sim **3368** only | Paper fill → journal FILL row must round-trip on real DLL path |
| **Phase C gate** | [docs/PHASE_C_GATE.md](docs/PHASE_C_GATE.md) criteria met on paper | Live is out of 7.0 scope; paper truth must be signed off first |

**Hard rule:** No second symbol in the active motor universe until PETR4 golden path is **green for 5 consecutive B3 sessions**.

---

## 7.0 pillars

| Pillar | What | Why |
|--------|------|-----|
| **Golden path dashboard** | Single-screen PETR4 health: scan → idea → backtest proof → paper fill → journal match | Filipe sees one truth, not 14 partial greens |
| **Symbol replication factory** | Wizard to clone PETR4 pipeline config to Core14 siblings — **disabled** until golden path green | Prevents scaling broken behavior across symbols |
| **RAM budget enforcement** | Per-process MB caps + ops panel; fail CI/agent loop if budget exceeded | RAM is the bottleneck for build speed and local stability |
| **Background test loop** | pytest runs on save/schedule in agent loop — never blocks launch or board paint | Dev velocity without sacrificing gate quality |
| **Paper journal reconciliation** | Automated day P&L vs Profit export / DLL position diff for PETR4 | "Working perfectly" means numbers match, not just UI green |
| **Staged SSE & cache discipline** | One quote stream, one desk stream, bounded HTML payloads | Duplicate EventSources + full HTML SSE are top RAM offenders today |
| **Motor cycle observability** | Cycle ms, phase breakdown, error rate in ops panel + `status_tick.py --json` | Slow cycles correlate with SQLite lock contention and quote batch size |
| **Local-first forever** | No hosting, tunnel, or remote execution in 7.0 | Perfect one machine before any network surface |

---

## Symbol replication factory (after PETR4 golden path)

**Golden path checklist (all required, 5 sessions):**

1. Scanner emits ≥1 ranked PETR4 idea per session when sleeves ON  
2. Idea carries valid `backtest_proof` (PF ≥ gate, DD ≤ gate)  
3. Paper execute → motor journal `FILL` + `JOURNAL` rows within one cycle  
4. Blotter position qty matches Profit Sim read-only position  
5. Day P&L within 2% of Profit truth (Phase C gate #4)  
6. Motor error rate < 5% of cycles (Phase C gate #2)  
7. Trust scorecard ≥ 85% (5.2) with no red gates  

**Factory behavior (enabled only when checklist green):**

- UI: "Add symbol to universe" → pick from Core14 template list (PRIO3, VALE3, …)  
- Clone from PETR4: scanner thresholds, idea gates, sleeve sizing, backtest window — **not** live DLL credentials  
- New symbol enters **shadow mode** (scan + ideas + backtest, no auto-execute) for 3 sessions  
- Promote to motor universe only after shadow checklist passes (subset of golden path)  
- Max **+1 symbol per week** — prevents RAM and attention explosion  

Mockup: [assets/mockup_7_0_symbol_factory.png](assets/mockup_7_0_symbol_factory.png)

---

## Quality gates

### Performance

| Gate | Target | Measure |
|------|--------|---------|
| Board first paint | < 800 ms (PETR4-only universe) | `dev.py start --wait` → `/board` TTFB |
| HTMX partial swap | < 200 ms p95 | symbol panel, idea stack |
| Motor cycle | < 3 s p95 (PETR4 only) | ops panel `motor_cycle_ms` |
| SSE reconnect | < 1 s perceived | watchlist price update after tab focus |

### RAM (local dev — Filipe's PC)

| Gate | Target | Measure |
|------|--------|---------|
| **Total stack** | ≤ 1.2 GB RSS (API + Streamlit + bridge + motor) | ops panel snapshot |
| API (uvicorn) | ≤ 350 MB | `/api/v1/ops/memory` |
| Streamlit | ≤ 400 MB | same |
| Profit bridge | ≤ 150 MB | same |
| SQLite `arbitragem.db` | ≤ 80 MB on disk; WAL checkpoint nightly | `dev.py` maintenance hook |

### Tests

| Gate | Target |
|------|--------|
| Golden path integration | 1 pytest module: PETR4 scan → idea → paper → journal (mock DLL) |
| Regression suite | `pytest tests/ -q` green in background loop within 10 min |
| No blocking on user | Launch and board usable while tests run |

### Paper truth

| Gate | Target |
|------|--------|
| Journal FILL rows | ≥ 20 on PETR4 (Phase C gate #3) |
| P&L reconciliation | Within 2% for 5 days |
| Manual sign-off | Filipe blotter review (Phase C gate #5) |

---

## RAM optimization playbook (this codebase)

Specific levers — ordered by impact:

### SQLite (`data/arbitragem.db`)

- **Why heavy:** Every motor cycle opens a session; journal append + idea queries + KPI history accumulate rows.  
- **Actions:**  
  - Cap `motor_journal` retention (e.g. 30 days hot, archive JSONL)  
  - Index `(symbol, created_at)` on journal and ideas  
  - `PRAGMA journal_mode=WAL; synchronous=NORMAL` at init  
  - Single session per motor cycle (already in `_orchestrator_loop`) — never nest sessions  
  - Batch commits in scanner (one commit per cycle, not per idea)

### httpx / urllib (API clients)

- **Why heavy:** Dashboard `api_get` + Streamlit reruns create duplicate connections; Ollama probes hold long timeouts.  
- **Actions:**  
  - Reuse one `httpx.Client` per process in `dashboard/utils.py`  
  - Extend `cached_get()` TTL for stable endpoints (`/bootstrap`, `/health`) to 90s  
  - Disable Ollama probe on board first paint (`ollama_probe_timeout_seconds=0.5`, lazy load reports)  
  - Profit bridge: connection pool size 2, no per-quote client spin-up

### SSE (`/api/v1/stream/quotes`, `/board/stream/trader-desk`)

- **Why heavy:** Two EventSources per board tab; trader-desk pushes **full HTML** every 10s.  
- **Actions:**  
  - **5.1 carry-forward:** desk SSE sends JSON deltas or phase-scoped partials, not full `trader_desk.html`  
  - Quote stream: subscribe **PETR4 only** in golden-path mode (`?symbols=PETR4`)  
  - Heartbeat 30s (not 15s) when single symbol  
  - Client-side: disconnect SSE when tab hidden (`document.visibilityState`)  
  - Server-side: one asyncio task per stream type, not per connection fan-out to full Core14 batch

### pytest workers

- **Why heavy:** Full suite loads FastAPI app, SQLite, autonomous engine — parallel xdist duplicates DB.  
- **Actions:**  
  - Golden-path tests: in-memory SQLite (`DATABASE_URL=sqlite:///:memory:`)  
  - Split fast unit (`tests/test_*.py` minus integration) vs slow integration  
  - Background loop: `pytest tests/ -q --ignore=tests/autonomous -x` first (< 3 min), full suite nightly  
  - No xdist on Windows agent loop unless RAM headroom > 2 GB free

### uvicorn workers

- **Why heavy:** Multiple workers duplicate motor loop and SQLite writers.  
- **Actions:**  
  - **Always `--workers 1`** on local dev (`scripts/dev.py`)  
  - Motor loop only in lifespan of worker 0 (guard with env `ARBITRAGEM_MOTOR=1`)  
  - Reload mode off during paper sessions (`--reload` doubles import RAM)

### Streamlit

- **Why heavy:** Full rerun on widget interaction; session_state cache grows unbounded.  
- **Actions:**  
  - `@st.cache_data` on heavy views (performance, backtest tables)  
  - `invalidate_cache()` surgical prefix only — not full clear every rerun  
  - Prefer blackboard HTMX for live desk; Streamlit for analytics only  
  - `streamlit run` with `--server.maxUploadSize 5` and disable unused pages in 7.0 slim mode

### Motor loop (`src/main.py` `_orchestrator_loop`)

- **Why heavy:** Runs every 15–45s; triggers scan, orchestrator, journal, risk summary.  
- **Actions:**  
  - Golden-path mode: skip full Core14 scan — PETR4-only scan path  
  - `paper_motor_auto_seed_ideas`: off after golden path stable (ideas from real scan only)  
  - Log cycle timing to ops endpoint; alert if p95 > 5s  
  - `asyncio.to_thread` for DB work (keep) — never block event loop with sync Profit DLL calls

### Quote cache

- **Why heavy:** `get_quotes_batch` over 14 symbols every 2s in SSE generator.  
- **Actions:**  
  - Process-level LRU cache keyed by symbol, TTL 1s (SSE tick still 2s but batch hits cache)  
  - Synthetic quotes for paper first paint (`_fast_quote`) — DLL only on SSE enrich  
  - Disable futures/crypto watchlist fetches when `GOLDEN_PATH_MODE=true`

### Snapshot worker (5.2)

- **Why heavy:** Periodic full desk snapshot to disk.  
- **Actions:**  
  - Snapshot JSON only (not HTML); max 24 snapshots rolling  
  - Run interval 60s in golden-path mode (not 10s)

---

## Background test architecture

**Goal:** Agents and CI validate continuously; Filipe never waits on pytest to open the board.

```
┌─────────────────┐     file watch / git diff      ┌──────────────────┐
│  dev.py start   │ ─────────────────────────────► │ test_worker.py   │
│  (non-blocking) │                                │ (subprocess)     │
└────────┬────────┘                                └────────┬─────────┘
         │                                                  │
         │ health OK                                        │ pytest -q
         ▼                                                  ▼
┌─────────────────┐                                ┌──────────────────┐
│ Board + Desk    │ ◄── status: green/yellow/red ──│ data/.dev/       │
│ (user trades)   │     via ops panel + status_tick│ test_status.json │
└─────────────────┘                                └──────────────────┘
```

| Component | Behavior |
|-----------|----------|
| **`scripts/test_worker.py`** (new) | Spawned by `dev.py start` when `ARBITRAGEM_BG_TESTS=1`; runs fast suite every 5 min or on `tests/` mtime change |
| **`data/.dev/test_status.json`** | `{ "state": "green\|yellow\|red", "last_run", "failures": [], "duration_sec", "ram_mb_peak" }` |
| **Ops panel** | Shows test badge — green = safe to promote symbol; red = golden path frozen |
| **Agent loop** | Read `status_tick.py --json` + test_status before declaring sprint done |
| **CI (optional)** | Same fast suite on push; full suite on tag only |
| **Golden-path test** | `tests/test_golden_path_petr4.py` — mandatory green for factory unlock |

**Failure policy:** Red tests block symbol factory and ops "promote" button — **do not** block board or motor (Filipe keeps paper session).

---

## Out of scope (7.0)

- Hosting, Cloudflare tunnel production, remote desk execution  
- Core14 full motor universe (only PETR4 + factory-shadow symbols)  
- Phase C live money / non-Sim DLL write  
- Crypto, futures, social RSS on golden-path board (lazy/off)  
- Ollama strategy generation in hot path  
- Multi-user auth / VPS hardening  
- Pair trades (PRIO3/PETR4) until both symbols pass shadow mode individually  

---

## Milestones

### 7.0-alpha — Golden path visible

- [ ] `GOLDEN_PATH_MODE` env + PETR4-only quote SSE  
- [ ] Golden path dashboard partial (checklist UI)  
- [ ] Ops panel v0: RSS per process + motor_cycle_ms  
- [ ] `test_worker.py` + `test_status.json`  
- [ ] RAM playbook items: SQLite WAL, quote LRU, desk SSE JSON delta (spike)  
- **Exit:** Board loads < 1 GB total RSS with desk + motor running  

Mockup: [assets/mockup_7_0_golden_path.png](assets/mockup_7_0_golden_path.png)

### 7.0-beta — Paper truth automated

- [ ] PETR4 P&L reconciliation job (export + DLL vs journal)  
- [ ] Trust scorecard wired to golden path checklist (5.2)  
- [ ] `tests/test_golden_path_petr4.py` green in background loop  
- [ ] Motor cycle timing + journal retention policy  
- [ ] Streamlit slim mode + cache discipline  
- **Exit:** 5 consecutive B3 sessions green on checklist (automated + manual sign-off)  

### 7.0-rc — Symbol factory

- [ ] Symbol factory UI (locked/unlocked states)  
- [ ] Shadow mode for 2nd symbol (PRIO3 recommended)  
- [ ] Factory blocked when test_status red or RAM > budget  
- [ ] Docs + `status_tick.py --json` includes golden_path + test + ram  
- **Exit:** PRIO3 completes shadow checklist; Filipe promotes manually; total RSS still ≤ 1.2 GB  

Mockups:
- [assets/mockup_7_0_symbol_factory.png](assets/mockup_7_0_symbol_factory.png)
- [assets/mockup_7_0_ops_panel.png](assets/mockup_7_0_ops_panel.png)

### 7.0 GA

- Golden path green 5 sessions · factory proven with one shadow symbol · background tests green 7 days · RAM budget met · Phase C gate paper criteria signed  

---

## Quick launch (unchanged)

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/launch.py
python scripts/status_tick.py
# Agent loop:
python scripts/dev.py status --json
```

---

*Local-first. Perfect PETR4. Then replicate.*

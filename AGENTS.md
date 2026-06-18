# Agent instructions — Arbitragem Dashboard

**Current sprint:** [RELEASE_14.1_EXECUTION.md](RELEASE_14.1_EXECUTION.md) **14.1.1** (desk command strip + weekly sim report). Version: `14.1.1`.

## Two-agent workflow (always on)

Work **together** on the `Arbitragem` folder. Split by layer, not by “who’s free.”

| Agent | Role | Owns |
|-------|------|------|
| **Supervisor (Alpha)** | Backend, API, integrations, performance, `scripts/dev.py`, tests | `src/`, `scripts/`, `tests/`, `dashboard/api_cache.py` |
| **Worker** | Streamlit + HTMX blackboard UX | `dashboard/views/`, `dashboard/scanner_ui.py`, `dashboard/components/` (except `api_cache`), `src/web/` |

**Rules**
1. Start each response with **Joint plan** — who does what this turn.
2. Do **not** duplicate work (e.g. Worker does not rewrite `api_cache.py`).
3. After mutations, call `invalidate_cache()` from dashboard or `python scripts/dev.py restart --wait`.
4. Both agents run `python scripts/dev.py start --wait` before asking Filipe to test.

## Parallel release protocol (mandatory)

**Rule:** When Supervisor picks an **A2.x** task, Worker **MUST** start the mapped **W2.x** in the **same sprint turn** — no waiting for backend unless the API contract is missing (see table). Split by layer; ship both sides every session.

### 4.0.0 GA kickoff matrix (complete)

| Supervisor | Worker (same sprint) | Status |
|------------|----------------------|--------|
| A4.18 paper validation API | W4.18 mobile banner + empty states | **DONE** |
| A4.19 SCALPER_COCKPIT docs | W4.18 paper gate banner on status | **DONE** |

### 12.0-beta kickoff matrix (active)

| Supervisor | Worker (start same sprint) | Before API? | Status |
|------------|----------------------------|-------------|--------|
| A12.7 paper fills `fees_brl` from `clear_cost_model` | W12.3 trade product margin + fees row (100 lot) | no — extend `estimate_paper_fills` | **DONE** |
| A11.3 `GET /archaeology/summary` | W11.4 layout preset **archaeology** (timeline hero) | no — partial exists | **DONE** |
| A12.8 Clear API trade sync (optional, `CLEAR_API_KEY`) | W12.3 journal row shows synced Clear fill | no | **DONE** |
| A11.1 FIFO P&L on archaeology rows | A11.5 symbol panel “your history” chip | no | **DONE** |
| A11.6 ingest insights → knowledge RAG | W11.1 Strategy Lab strip in hybrid layout | yes (static cards) | **DONE** |
| A11.14 bridge `/health` `dll_mode` + `is_paper` | W11.7 outbox ticker polish (copy hint) | no | **DONE** |
| A11.10 `filipe_core17` scanner mode | W11.4 Core17 sector strip | no | **DONE** |

Full 11.0 tables: [docs/RELEASE_11.0_SCOPE.md](docs/RELEASE_11.0_SCOPE.md).

### 4.1 kickoff matrix (backlog)

| Supervisor | Worker (start same sprint) | Before API? |
|------------|----------------------------|-------------|
| A4.20 WIN/WDO quotes API | W4.19 futures row styling + session badges | yes (stub rows) |
| A4.21 RSS/Twitter signals API | W4.20 social chips on pulse rail | yes (placeholder chips) |

Full phase tables: [RELEASE_4.0.0.md §6](RELEASE_4.0.0.md) · [RELEASE_4.0.0_PROGRESS.md](RELEASE_4.0.0_PROGRESS.md).

### Supervisor → Worker kickoff matrix (2.0 legacy)

| Supervisor | Worker (start same sprint) | Can start before API? | Status |
|------------|----------------------------|------------------------|--------|
| A2.4a backtest run | W2.8 backtest proof badge | yes (placeholder PF/DD) | **DONE** |
| A2.4b CSV watcher | W2.8 badge from `backtest_proof` | no | **DONE** |
| A2.5a sector pairs | W2.7 sector strip + corr map | yes (mock/static grid) | **DONE** |
| A2.5b VWAP reclaim | W2.2 symbol panel VWAP line | yes | **DONE** |
| A2.8 SSE `/stream/quotes` | W2.1 watchlist SSE subscribe | yes (HTMX `sse-connect`) | **DONE** |
| A2.9 `/symbols/{sym}/report` | W2.5 AI report panel tab | no — use `docs/agent_integration.md` | **DONE** |
| A2.10 idea lifecycle gates | W2.4 modal state badges + disabled confirm | yes (UI states first) | **DONE** |
| A2.6a paper execute | W2.4 execute path after confirm | no | **DONE** |
| A2.6b Clear live router | W2.4 live-mode confirm + risk copy | no | **DONE** |
| A2.6c kill switch API | W2.4 sidebar STOP ALL button | yes (wire button first) | **DONE** |
| A2.7 setup API *(alpha)* | W2.6 setup wizard UI | yes — API shipped | **DONE** |
| — *(no backend blocker)* | W2.3 board notes persist | yes | **DONE** |
| — | W2.9 mobile watchlist + confirm | yes | **DONE** |
| — | W2.10 Streamlit ↔ board link | yes | **DONE** |

Full matrix with checkmarks: [RELEASE_2.0.0.md §11.1](RELEASE_2.0.0.md).

### 2.0 GA — DONE vs REMAINING

| Phase | Supervisor | Worker |
|-------|------------|--------|
| **DONE** (alpha) | A2.1–A2.3, A2.7 | W2.1, W2.2 |
| **DONE** (beta) | A2.4a, A2.4b, A2.5a | W2.8, W2.7 (data wired) |
| **DONE** (rc) | A2.8, A2.9, A2.6a, A2.6c | W2.5, W2.4 confirm/execute/kill, W2.6 |
| **REMAINING** (GA) | — | — (2.0 GA Worker lane **DONE**) |

**GA bar:** Clear live OR paper+journal sync verified · SSE perceived load &lt; 1s · mobile confirm path · all lifecycle gates enforced.

### Sprint kickoff prompts

**Supervisor (Alpha):**

```
You are Supervisor (Alpha). Read AGENTS.md + RELEASE_12.0.0.md + docs/RELEASE_11.0_SCOPE.md.
Active: A12.7 (paper fees_brl) + A11.3/A11.1 (archaeology API). Worker starts mapped W12.3 / W11.4 in parallel.
Own src/, scripts/, tests/. Do NOT touch src/web/ or dashboard/views/.
Update docs/agent_integration.md per endpoint. pytest after each task. dev.py restart --wait after API changes.
Use .venv\Scripts\python.exe scripts\dev.py (orphan port recycle is in dev.py).
```

**Worker (Agent 2):**

```
You are Worker (Agent 2). Read AGENTS.md kickoff matrices (12.0-beta + 11.0-alpha).
When Supervisor picks A12.7, start W12.3 same turn. When A11.3 lands, wire archaeology preset + history chip.
Own src/web/, dashboard/views/, dashboard/components/ (not api_cache.py).
HTMX + cached_get() only. Test http://localhost:8000/board after each change.
```

### Release cadence

| Tag | When | Version bump | Gate |
|-----|------|--------------|------|
| `2.0.0-alpha` | Blackboard shell + Core14 API | minor pre-release | W2.1–W2.2 + A2.1–A2.3 |
| `2.0.0-beta` | Backtest pipeline + sector pairs | beta bump | A2.4a/b + A2.5a + W2.8 |
| `2.0.0-rc` | SSE + reports + confirm/execute/kill | rc bump | A2.8, A2.9, A2.6a/c + W2.4–W2.6 |
| `2.0.0` | Clear live + lifecycle + mobile | **GA** | A2.6b, A2.10, W2.9 + DoD §10 |

Bump `pyproject.toml` / dashboard version string on each phase tag. Both agents note phase in first response **Joint plan**.

## Full developer autonomy

Agents must **run the stack themselves** using `scripts/dev.py`. Do not delegate setup to Filipe unless automation fails.

### Start everything (use this first)

```bash
python scripts/dev.py start --wait --json
```

Exit `0` = API + Streamlit healthy at http://localhost:8501  
**Blackboard (2.0):** http://localhost:8000/board

### Supervisor (backend) — **12.0-beta + 11.0-alpha**

**Done (11.0-alpha pack):** A11.1 FIFO archaeology P&L · A11.3 archaeology summary · A11.6 knowledge insights ingest · A11.10 `filipe_core17` scanner + `GET /universe/filipe-core17` · A12.7 paper `fees_brl`.

**Done (11.0-rc pack):** W11.4 sector strip on Desk · A11.8 NTSL pack version + store diff · A11.9 options refresh API · A11.11 motor queue 12 + core17 universe.

**Next / backlog (code-complete — manual gates only):**

```
Blocked on Filipe / external: Phase C gate (`docs/PHASE_C_GATE.md`), ≥9k archaeology rows, 50 NTSL indexed, DLL ctypes live orders (12.0-rc), live crypto.
```

**Shipped (11.0 GA software — `8f5fecc`):** A11.7 replay · A12.8 Clear sync · A4.20 futures · A11.12 patch weighting · A11.14 bridge health · A4.21 social signals · A11.16 sizer · A11.17 WIN roll · A11.18 F1–F5 · profit execution ladder · session prep.

### Worker (Agent 2) — **parallel with every A12.x / A11.x pick**

```
W12.3  Trade product margin + fees (100 lot) — when A12.7 lands
W11.4  Archaeology layout preset + sector strip
W11.5  Symbol panel “your history” chip
W11.1  Strategy Lab strip (can stub before A11.8)
```

Always pair via [Parallel release protocol](#parallel-release-protocol-mandatory) · full split: [RELEASE_2.0.0.md §11](RELEASE_2.0.0.md)

- After API changes: `python scripts/dev.py restart --wait`
- Tests: `pytest tests/ -q`
- Logs: `logs/api.log`

### Worker (frontend)

- After UI changes: refresh http://localhost:8501 (Streamlit hot-reloads)
- If sidebar shows "API offline": `python scripts/dev.py restart --wait`
- Use `cached_get()` from `dashboard/api_cache.py` — never raw `api_get` on every rerun
- Blackboard: edit `src/web/templates/` + `blackboard.css`; test at http://localhost:8000/board
- Logs: `logs/dashboard.log`

### Filipe (beginner)

One command only:

```powershell
python scripts/dev.py start --wait --open
```

Then use the dashboard in the browser. Stop with `python scripts/dev.py stop`.

## Agent handoff

See [docs/agent_integration.md](docs/agent_integration.md) for the API contract between backend and frontend.

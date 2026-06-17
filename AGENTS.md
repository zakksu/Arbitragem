# Agent instructions — Arbitragem Dashboard

**Current sprint:** [RELEASE_4.0.0.md](RELEASE_4.0.0.md) — **4.0.0 GA** shipped. Tracker: [RELEASE_4.0.0_PROGRESS.md](RELEASE_4.0.0_PROGRESS.md).

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

### 4.1 kickoff matrix (active)

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
You are Supervisor (Alpha). Read AGENTS.md + RELEASE_2.0.0.md §11–§11.1.
2.0-rc core is done (SSE, reports, execute, kill switch). Remaining: A2.5b → A2.10 → A2.6b.
When you pick an A2.x task, Worker MUST start the mapped W2.x in parallel (see kickoff matrix).
Do NOT touch src/web/ or dashboard/views/. Update docs/agent_integration.md per endpoint.
Run pytest after each task. python scripts/dev.py restart --wait after API changes.
```

**Worker (Beta):**

```
You are Worker (Beta). Read AGENTS.md + RELEASE_2.0.0.md §11–§11.1.
When Supervisor starts A2.x, start mapped W2.x immediately — do not wait unless "Can start before API?" = no.
Remaining: ~~W2.3 notes → W2.10 board link → W2.9 mobile~~ **DONE** · W2.4 live path when A2.6b lands **DONE**
Own src/web/ and dashboard/views/. Do NOT edit src/api/ or api_cache.py.
Wire endpoints via HTMX or cached_get() only. Test http://localhost:8000/board after each change.
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

### Supervisor (backend) — **idle at 4.3.0-alpha**

Backend complete through 4.3 (autonomous engine, CEI, 2.0 GA debt). Resume when:

- Worker ships W4.21–W4.22b (4.2-beta) and files API bugs
- New phase scoped (4.4+) in `RELEASE_4.0.0.md`
- Integration work: ProfitDLL ctypes, Clear live hardening, tick walk-forward

### Worker (frontend) — **parallel with every A2.x pick**

```
W2.3   Board notes persist — **DONE**
W2.9   Mobile watchlist + confirm — **DONE**
W2.10  Streamlit ↔ board link — **DONE**
W2.4   Live confirm path — **DONE**
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

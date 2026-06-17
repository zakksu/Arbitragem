# Release 7.0.0 — Golden Path Perfection (GA)

**Version:** `7.0.0` · **Scope:** [RELEASE_7.0_LOCAL.md](RELEASE_7.0_LOCAL.md)

Local-first release: one symbol (**PETR4**) flawless end-to-end on Filipe's PC, then replicate via the symbol factory — never the reverse.

---

## What's in 7.0 GA

| Phase | Shipped |
|-------|---------|
| **7.0-alpha** | `GOLDEN_PATH_MODE`, PETR4-only universe, golden path checklist UI, ops strip, background test worker, staged HTMX first paint |
| **7.0-beta** | P&L reconciliation, trust scorecard → checklist #7, journal retention, Streamlit slim mode, `/api/v1/ops/memory` |
| **7.0-rc** | Symbol factory backend + UI (locked/unlocked), shadow/promote APIs, PRIO3 shadow workflow |
| **7.0 GA** | Release docs, RAM snapshot tooling, session recording script, full test suite green |
| **7.0 low-RAM** | `LOW_RAM_MODE`, hardware rules, `benchmark_ram.py`, resource profile toggles |

Mockups: [golden path](assets/mockup_7_0_golden_path.png) · [symbol factory](assets/mockup_7_0_symbol_factory.png) · [ops panel](assets/mockup_7_0_ops_panel.png)

---

## How to run

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/launch.py
# or full dev stack:
python scripts/dev.py start --wait --open
```

**Board (golden path mode):** http://127.0.0.1:8000/board  
**Streamlit:** http://127.0.0.1:8501

Enable golden path in `.env`:

```env
GOLDEN_PATH_MODE=true
LOW_RAM_MODE=true
ARBITRAGEM_BG_TESTS=1
```

**Low-RAM on <16 GB hosts:** `LOW_RAM_MODE=true` (or rely on `GOLDEN_PATH_MODE` auto-enable). Disables Ollama/RSS/social, slim Streamlit, 60s desk SSE, +50% motor interval, 15-row desk journal. See `.cursor/rules/low-ram-hardware.mdc`.

**Agent / ops loop:**

```powershell
python scripts/status_tick.py --json
python scripts/ram_snapshot.py
python scripts/benchmark_ram.py --json
python scripts/golden_path_record_session.py --dry-run --json
```

---

## Quality gates

### Automated (CI / background test worker)

- `pytest tests/ -q` green
- `tests/test_golden_path_petr4.py` + `tests/test_symbol_factory.py` in fast background loop
- Symbol factory **locked** when: golden path &lt; 5 green sessions, checklist not all green, `test_status` red, or stack RSS &gt; 1.2 GB budget
- P&L reconcile job every 5 min when `GOLDEN_PATH_MODE=true`

### Manual (Filipe sign-off)

| Gate | Target | How |
|------|--------|-----|
| Golden path green **5 B3 sessions** | Checklist all green on paper | Run paper sessions; `golden_path_record_session.py` records when green |
| Factory shadow symbol | PRIO3 completes 3 shadow sessions | Factory UI → clone → shadow checklist → promote |
| Background tests green **7 days** | `data/.dev/test_status.json` stays green | Operational — leave stack running |
| RAM budget ≤ **1.2 GB** | Ops strip + `ram_snapshot.py` | Manual verify with desk + motor running |
| Phase C paper criteria | [docs/PHASE_C_GATE.md](docs/PHASE_C_GATE.md) | Manual blotter review + sign-off |
| Board first paint &lt; 800 ms | PETR4-only staged load | Manual browser timing |

---

## Symbol factory

1. Open board footer → **Symbol factory**
2. When **locked**: overlay shows — needs 5 green golden-path sessions + all-green checklist + green tests + RAM under budget
3. When **unlocked**: pick Core14 symbol (PRIO3 recommended) → **Clone from PETR4 template**
4. Shadow mode runs 3 sessions (scan + ideas + backtest, no auto-execute)
5. **Promote to motor** after shadow checklist passes (+1 symbol/week max)

APIs: `GET /api/v1/symbol-factory/status` · `POST .../shadow` · `POST .../promote`

---

## Dev tooling (not for production fake data)

| Script | Purpose |
|--------|---------|
| `scripts/golden_path_record_session.py` | Record today's session if checklist all green |
| `scripts/golden_path_record_session.py --dev-fill-sessions 5` | **Dev only** — seed 5 session dates to test factory unlock locally |
| `scripts/ram_snapshot.py` | Write stack RSS to `data/.dev/ram_snapshot.json` (ops panel reads this) |
| `scripts/benchmark_ram.py` | Peak RSS for imports + golden path evaluate → `data/.dev/ram_benchmark.json` |
| `scripts/test_worker.py` | Background pytest → `data/.dev/test_status.json` |
| `scripts/status_tick.py --json` | Single JSON health snapshot for agents |

---

## What's manual vs automated

| Item | Automated | Manual |
|------|-----------|--------|
| Golden path checklist evaluation | Yes (every 30s on board) | — |
| Session green counter | Yes when all green today | 5 distinct B3 trading days |
| P&L reconcile | Yes (scheduler) | Profit export truth source |
| Trust scorecard | Yes | — |
| Symbol factory lock/unlock | Yes | Promote decision |
| Shadow session progress | Yes (`record_shadow_session`) | Run 3 real shadow sessions |
| RAM budget | Measured (ops + snapshot) | Verify under load |
| Phase C live | Out of scope | Paper sign-off only |

---

## Upgrade from 7.0-beta

1. Pull / checkout `v7.0.0`
2. `pip install -r requirements.txt` (adds `psutil`)
3. `python scripts/dev.py restart --wait`
4. Confirm `python scripts/status_tick.py --json` shows `golden_path`, `symbol_factory`, `ram_mb`

---

*Local-first. Perfect PETR4. Then replicate.*

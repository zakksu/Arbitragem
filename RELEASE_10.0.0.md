# Release 10.0.0 — Eternal Golden Path (GA)

**Version:** `10.0.0` · **Prerequisite:** [RELEASE_7.0.0.md](RELEASE_7.0.0.md)  
**Vision:** [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md) · **Runbook:** [docs/RELEASE_10.0_RUNBOOK.md](docs/RELEASE_10.0_RUNBOOK.md)

Local-first mastery on **1–5 symbols** (PETR4 first). Replay-driven learning, engine observability, knowledge RAG spine, theory deck on confirm, learning rail patches, paper graduation — no universe expansion until golden path is rock solid.

---

## 10.0 GA shipped

| Pillar | Status |
|--------|--------|
| Replay Training Engine | `replay_engine.py`, scheduler + `replay_training_worker.py`, visual replay player |
| Engine Mind | Phases, sources (max 5), cycle breakdown, motor log |
| Strategy Store | NTSL scan from Profit export dirs |
| Golden Path + Symbol Factory | PETR4-only when `GOLDEN_PATH_MODE=true` |
| Knowledge spine (FTS) | `data/knowledge.db`, ingest CLI, search API + library panel |
| Daily briefing | Transparent session summary on board |
| Theory deck (beta) | Theory card chips + decision brief modal on confirm |
| Learning rail (rc) | Patch propose / approve / reject drawer |
| Paper graduation | Per-symbol gates + watchlist badges |
| Self-healing | Health registry, circuit breakers, degraded banner |
| Motor universe | Max 1–5 concurrent auto symbols policy |
| Resource profile | RAM/GPU fractions, low-RAM coexistence |

---

## How to run

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/launch.py
```

**.env (recommended):**

```env
GOLDEN_PATH_MODE=true
LOW_RAM_MODE=true
REPLAY_TRAINING_ENABLED=true
ARBITRAGEM_BG_REPLAY=1
KNOWLEDGE_ENABLED=true
ENGINE_MIND_ENABLED=true
RESOURCE_RAM_FRACTION=0.8
RESOURCE_GPU_FRACTION=0.4
```

**URLs:**
- Board: http://127.0.0.1:8000/board
- Engine mind API: http://127.0.0.1:8000/api/v1/engine/mind
- Knowledge search: http://127.0.0.1:8000/api/v1/knowledge/search?q=VWAP
- Daily briefing: http://127.0.0.1:8000/api/v1/daily-briefing

**Ingest corpus (offline — never on motor hot path):**

```powershell
python scripts/ingest_knowledge.py --path docs/STRUCTURES.md --symbol PETR4
python scripts/ingest_knowledge.py --path exports/ntsl --symbol PETR4
```

**Background workers (spawned by `dev.py start`):**
- `scripts/test_worker.py` → `data/.dev/test_status.json`
- `scripts/replay_training_worker.py` → `data/.dev/replay_training_status.json`

```powershell
python scripts/status_tick.py --json
python scripts/replay_training_worker.py --once
```

---

## API reference (10.0 GA)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/replay/run` | Start replay session |
| `POST /api/v1/replay/training/run` | Run training cycle (PETR4) |
| `GET /api/v1/replay/sessions` | Recent replays |
| `GET /api/v1/engine/mind` | Engine mind snapshot |
| `POST /api/v1/strategy-store/scan` | Index NTSL strategies |
| `GET /api/v1/knowledge/status` | Corpus stats |
| `GET /api/v1/knowledge/search` | FTS search |
| `GET /api/v1/knowledge/distill` | Rule axioms distill |
| `GET /api/v1/daily-briefing` | Session briefing JSON |
| `POST /api/v1/ideas/{id}/brief` | Decision brief (max 5 bullets) |
| `GET /api/v1/ideas/{id}/theory-cards` | Theory cards for idea |
| `GET /api/v1/autonomous/patches` | Pending patch proposals |
| `POST /api/v1/autonomous/patches/generate` | Generate from journal |
| `GET /api/v1/symbols/{sym}/graduation` | Paper graduation gates |
| `GET /api/v1/motor/universe` | Motor symbol policy |
| `GET /api/v1/self-healing/health` | Health + circuit breakers |

---

## Deferred (hardware / integration)

- ProfitDLL live tick stream (stub bridge fills today)
- GPU embedding batch (`KNOWLEDGE_GPU_EMBED`)
- Live graduation to non-paper account (requires explicit unlock per [PHASE_C_GATE.md](docs/PHASE_C_GATE.md))

---

## Quality gates

| Gate | Target |
|------|--------|
| Stack RSS | ≤ 1.5 GB with knowledge + motor (16 GB host, 80% policy) |
| Knowledge search | < 500 ms p95 |
| Replay worker | Non-blocking; status JSON green |
| Golden path | 5 B3 sessions before symbol #2 |
| Tests | `pytest tests/test_10_0_ga.py tests/test_knowledge_store.py tests/test_replay_engine_10.py -q` |

See [RELEASE_10.0.0_PROGRESS.md](RELEASE_10.0.0_PROGRESS.md).

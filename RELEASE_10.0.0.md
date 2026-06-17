# Release 10.0.0 — Eternal Golden Path (GA)

**Version:** `10.0.0` · **Prerequisite:** [RELEASE_7.0.0.md](RELEASE_7.0.0.md)  
**Vision:** [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md) · **Runbook:** [docs/RELEASE_10.0_RUNBOOK.md](docs/RELEASE_10.0_RUNBOOK.md)

Local-first mastery on **1–5 symbols** (PETR4 first). Grounded decisions, replay training, engine observability, knowledge RAG, self-learning patches — paper default on cold start.

---

## 10.0.0 GA shipped

| Pillar | Status |
|--------|--------|
| Replay Training Engine | Tick sim + bridge hook, visual player, background worker |
| Engine Mind | Real-time phases, sources, cycle breakdown, 3s poll |
| Strategy Store | NTSL scan + board panel |
| Knowledge spine | FTS corpus, search, library panel |
| Decision briefs | RAG + Ollama on demand, confirm modal, conflict block |
| Theory cards | Chips on idea stack + brief |
| Learning loop | Outcome rank, patch propose/approve/reject UI |
| Paper graduation | Per-symbol gates + watchlist badges |
| ProfitChart Companion | Level overlays + copy |
| Daily briefing | Charts + narrative |
| Self-healing | Health registry, degraded banner, ops corpus row |
| Theory Deck layout | Scalp / Structure / Learn presets |

---

## How to run

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/launch.py
```

**Board:** http://127.0.0.1:8000/board · **API:** http://127.0.0.1:8000/docs

```powershell
python scripts/status_tick.py --json
pytest tests/test_10_0_ga.py tests/test_10_0_ui_ga.py tests/test_knowledge_store.py -q
```

---

## Quality gates (GA)

| Gate | Target |
|------|--------|
| Version | `10.0.0` in `src/__init__.py` |
| Tests | `test_10_0_ga` + `test_10_0_ui_ga` + knowledge green |
| Stack RSS | ≤ 1.5 GB with knowledge + motor |
| Kill switch | Stops all symbols < 1 s |
| Paper default | Cold start paper mode |

Manual: Filipe sign-off on decision simplicity · 5 green B3 golden-path sessions before symbol #2.

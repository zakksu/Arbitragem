# Release 10.0.0 — Progress (Eternal Golden Path)



**Version:** `10.0.0-alpha`  

**Agent 1 (Backend):** Replay + Strategy Store + Knowledge + Self-healing — **COMPLETE**



---



## Shipped



| ID | Component | Status |

|----|-----------|--------|

| A10.R1 | `ReplaySession` / `ReplayFill` models | ✅ |

| A10.R2 | `replay_engine.py` — tick sim + **bridge fill import** | ✅ |

| A10.R3 | Parallel `ThreadPoolExecutor` training cycle | ✅ |

| A10.R4 | Scheduler `replay_training` job | ✅ |

| A10.S1 | `strategy_store.py` + `ntsl_parser.py` | ✅ |

| A10.K1 | `knowledge/replay_ingest.py` — replay + NTSL → FTS | ✅ |

| A10.K2 | Knowledge API ingest endpoints | ✅ |

| A10.M1 | `engine_mind.py` + circuit breaker snapshot | ✅ |

| A10.H1 | `self_healing/circuit_breaker.py` | ✅ |

| A10.J1 | `b3_history_import.py` + `POST /archaeology/import/excel` | ✅ |

| A10.API | Full API surface (see below) | ✅ |

| A10.T1 | `tests/test_replay_engine_10.py` (13+ tests) | ✅ |



## API



```http

POST /api/v1/replay/run

GET  /api/v1/replay/sessions

GET  /api/v1/replay/{job_id}

POST /api/v1/replay/training/run

POST /api/v1/strategy-store/scan

GET  /api/v1/strategy-store

GET  /api/v1/engine/mind

POST /api/v1/knowledge/ingest/replays

POST /api/v1/knowledge/ingest/strategies

GET  /api/v1/knowledge/search?q=

POST /api/v1/archaeology/import/excel

GET  /api/v1/self-healing/breakers

```



## Config



```env

REPLAY_TRAINING_ENABLED=true

REPLAY_PARALLEL_WORKERS=2

PROFITCHART_STRATEGIES_DIR=C:/Nelogica/Profit/Estrategias

KNOWLEDGE_ENABLED=true

RESOURCE_RAM_FRACTION=0.8

RESOURCE_GPU_FRACTION=0.4

```



## Agent 2 (UI) — **COMPLETE** (10.0-alpha cockpit)

| ID | Component | Status |
|----|-----------|--------|
| W10.EM | Engine Mind footer — sources, cycle breakdown, API merge, 3s poll | ✅ |
| W10.RP | Visual Replay Player — run replay, fill markers, sessions list | ✅ |
| W10.PC | ProfitChart Companion — level overlays + copy | ✅ |
| W10.SS | Strategy Store panel — scan NTSL + detail drawer | ✅ |
| W10.DB | Daily briefing — golden path bar, P&L spark, replay bars | ✅ |
| W10.KL | Knowledge library search panel (golden path) | ✅ |
| W10.T2 | `tests/test_engine_mind_10_0.py` (11 tests) | ✅ |

## Agent 1 backlog — cleared



All items from the first 10.0 increment are done. Next phase (Worker / integration):



- Worker W10.x knowledge library UI

- Real ProfitDLL tick stream (replace stub bridge fills)

- GPU embedding batch during knowledge ingest (`KNOWLEDGE_GPU_EMBED`)



See [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md).


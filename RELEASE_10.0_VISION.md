# Release 10.0 — Grounded Autonomous Trader (vision)

**Codename:** *Theory Deck*  
**Prerequisite:** [RELEASE_7.0_LOCAL.md](RELEASE_7.0_LOCAL.md) GA (PETR4 golden path + symbol factory proven) · 8.x multi-symbol scale · 9.x observability + engine hardening  
**Primary UI:** http://localhost:8000/board (HTMX) · **Analytics:** http://localhost:8501 (Streamlit slim)  
**Stack (unchanged core):** FastAPI · SQLite WAL · Profit bridge · HTMX blackboard · optional Binance quotes · Ollama (local)

---

## 1. North star — what 10.0 means vs 7.0

| Dimension | **7.0** (today) | **10.0** (target) |
|-----------|-----------------|-------------------|
| **Scope** | One symbol flawless (PETR4) → replicate via symbol factory | **Core14 motor universe** with per-symbol golden-path clones, shadow → promote discipline |
| **Decision quality** | Rules + gates (PF, DD, lifecycle) + optional Ollama commentary | **Grounded decisions**: every high-stakes suggestion cites retrieved theory + journal evidence |
| **Autonomy** | Motor scans, WFO promote, rankings sync — human confirms executes | **Graduated autonomy**: paper auto-execute within gates → live only after symbol graduation + human approve |
| **Knowledge** | Static lessons rail, `STRUCTURES.md`, symbol report cache | **Living corpus**: books, papers, video transcripts → RAG → theory cards linked to ideas & outcomes |
| **Learning** | Journal analyzer + Ollama post-trade notes | **Closed loop**: outcome → rank patterns → retrieve theory → propose rule patch → human approve |
| **Robustness** | RAM budget, test worker, golden path checklist | **Self-healing stack**: circuit breakers, degraded modes, auto-restart, health loops — trading pauses, stack recovers |
| **Simplification** | Many panels, gates, scores | **Decision briefs**: one screen answers *take / skip / wait* with ≤5 bullets + citations |

**One sentence:** 7.0 proves the machine can trade **one** symbol truthfully on Filipe's PC; 10.0 proves it can trade **many** symbols **autonomously** with **explainable, corpus-grounded** decisions that **get simpler** over time—not noisier.

**Emotional goal:** Filipe drops a PDF of Marcos Kozlowski or a YouTube transcript on market structure; next session the board shows a PETR4 idea with a *theory card* quoting the exact passage that supports the entry—and when the trade loses, the system proposes a gate tweak backed by journal stats, not a vague LLM rant.

---

## 2. Phased milestones (10.0-alpha → 10.0-GA)

Intermediate releases **8.x** (multi-symbol factory at scale) and **9.x** (self-healing + engine 2.0 foundations) are assumed complete before 10.0-alpha. This section is the 10.0 slice only.

### Dependency graph (high level)

```
7.0 GA ──► 8.x multi-symbol ──► 9.x heal + engine 2.0 ──► 10.0-alpha (RAG spine)
                                                                    │
                    10.0-beta (theory cards + decision briefs) ◄────┘
                                    │
                    10.0-rc (self-learning loop + graduation)
                                    │
                    10.0-GA (full Core14 autonomous paper + optional live per symbol)
```

---

### 10.0-alpha — Knowledge spine (ingest + retrieve, no hot-path LLM)

**Theme:** Build the library; do not let Ollama read PDFs on every motor cycle.

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| **A10.1** | Supervisor | Corpus schema + sqlite-vec store | `data/knowledge.db` (or `knowledge_vec` table in `arbitragem.db`); migrations |
| **A10.2** | Supervisor | Ingestion CLI: PDF/epub/txt → chunk → embed | `scripts/ingest_knowledge.py` (batch, offline) |
| **A10.3** | Supervisor | YouTube transcript path | `scripts/ingest_youtube.py` (yt-dlp + whisper optional, or paste transcript) |
| **A10.4** | Supervisor | `GET /api/v1/knowledge/search?q=&symbol=&tags=` | Hybrid keyword + vector; capped `limit=8` |
| **A10.5** | Supervisor | Embedding worker profile | CPU default; CUDA batch when `detect_compute_device().gpu_available` |
| **A10.6** | Supervisor | Resource profile: `knowledge_enabled`, RAM caps | Extend `resource_profile.py`; off in `LOW_RAM_MODE` hot path |
| **W10.1** | Worker | Knowledge library panel on board | `/board/partials/knowledge-library` — upload dropzone, ingest status |
| **W10.2** | Worker | Search UI + snippet preview | HTMX search rail; no full-page Streamlit |
| **W10.3** | Worker | Ops: corpus stats (chunks, MB, last ingest) | Ops panel row |

**Definition of done (alpha exit):**

- [ ] Ingest 3 sample docs (1 PDF, 1 pasted transcript, 1 `STRUCTURES.md` chapter) without crashing stack
- [ ] Search returns relevant chunks in < 500 ms p95 on Filipe's PC (CPU embed OK)
- [ ] Total stack RSS ≤ **1.5 GB** with knowledge DB + motor (stretch from 7.0's 1.2 GB — knowledge is lazy-loaded)
- [ ] `pytest tests/test_knowledge_*.py` green; ingest never runs inside motor cycle
- [ ] `docs/agent_integration.md` updated with knowledge endpoints

**Dependencies:** 7.0 GA · `sentence-transformers` or `fastembed` (lightweight) · **sqlite-vec** extension (see §6)

---

### 10.0-beta — Theory cards + decision briefs (grounded UX)

**Theme:** Link corpus to live trading objects; simplify the decision surface.

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| **A10.7** | Supervisor | Theory card model | `TheoryCard`: `id`, `title`, `source_uri`, `chunk_ids[]`, `tags[]`, `symbols[]` |
| **A10.8** | Supervisor | Auto-link cards to ideas | On idea generate: retrieve top-k chunks → attach card IDs to `TradeIdea.meta` |
| **A10.9** | Supervisor | Decision brief generator | `POST /api/v1/ideas/{id}/brief` — Ollama **only** on retrieved context (RAG), max 5 bullets |
| **A10.10** | Supervisor | Rule distillation job (offline) | Weekly: cluster corpus chunks → candidate axioms JSON (no auto-apply) |
| **A10.11** | Supervisor | Conflict detector | Compare brief claims vs `backtest_proof` + risk gates → `conflicts[]` |
| **W10.4** | Worker | Theory card chips on Trade Product | Idea stack + symbol panel |
| **W10.5** | Worker | Decision brief modal | Replace wall-of-text AI report for confirm path |
| **W10.6** | Worker | Conflict badges (red/yellow) | Block confirm when hard conflict |
| **W10.7** | Worker | Scanner pattern ↔ card tags | `vwap_reclaim` shows linked cards in education rail |

**Definition of done (beta exit):**

- [ ] Every confirmed idea in paper mode shows ≥1 theory card OR explicit "no corpus match"
- [ ] Decision brief generated in < 8 s p95 (Ollama + small context window)
- [ ] Conflict detector blocks confirm on hard mismatch (e.g. brief says "add to loser", gate forbids)
- [ ] Filipe manual sign-off: briefs feel **simpler** than 4.0 symbol report (qualitative)

**Dependencies:** 10.0-alpha · existing `TradeIdea` lifecycle · `OllamaClient` with RAG context builder

---

### 10.0-rc — Self-learning loop + paper graduation

**Theme:** Close the loop from outcomes to proposals; still human-in-the-loop for patches.

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| **A10.12** | Supervisor | Outcome ranker | Journal + backtest → pattern × symbol win rate, PF, slippage |
| **A10.13** | Supervisor | Strategy patch proposal | `PATCH_PROPOSAL` row: diff on thresholds, cite evidence + theory card IDs |
| **A10.14** | Supervisor | Approve/reject API | `POST /api/v1/autonomous/patches/{id}/approve` → applies to symbol factory clone config |
| **A10.15** | Supervisor | Paper graduation gates | Per-symbol: N fills, reconcile green, trust ≥ 85%, WFO stable 4 folds |
| **A10.16** | Supervisor | Autonomous engine 2.0 scheduler | Per-symbol routines; not one global Core14 scan in golden-path style |
| **A10.17** | Supervisor | Self-healing hooks | See §3 — wire into motor pause/resume |
| **W10.8** | Worker | Learning rail on board | "What we learned this week" + pending patches |
| **W10.9** | Worker | Graduation badge per symbol | Watchlist + factory UI |
| **W10.10** | Worker | Patch review drawer | Diff view, approve/reject, link to journal trades |

**Definition of done (rc exit):**

- [ ] ≥1 patch proposal generated from real journal data (paper) with citations
- [ ] Approve path updates symbol config; reject leaves audit trail
- [ ] 2 symbols (e.g. PETR4 + PRIO3) at **paper graduated** — auto-execute within gates, no live
- [ ] Self-healing: simulated bridge failure → degraded mode → recovery without manual `dev.py` (see §3)

**Dependencies:** 10.0-beta · `symbol_factory.py` · `journal_analyzer.py` · `AutonomousEngine`

---

### 10.0-GA — Multi-symbol grounded autonomous trader

**Theme:** Production bar on Filipe's machine — ambitious, still local-first.

| ID | Owner | Task | Deliverable |
|----|-------|------|-------------|
| **A10.18** | Supervisor | Core14 motor universe policy | Max concurrent auto symbols = f(RAM); queue rest in shadow |
| **A10.19** | Supervisor | Live graduation (optional per symbol) | Explicit unlock; Profit Sim 3368 → live only with second confirm |
| **A10.20** | Supervisor | Crypto context (read-only default) | Binance quotes enrich briefs; no auto crypto execute unless flag |
| **A10.21** | Supervisor | Knowledge poisoning guards | See §8 |
| **A10.22** | Supervisor | Full regression + RAM snapshot CI | `ram_snapshot.py` ≤ 1.5 GB with 3 symbols + knowledge |
| **W10.11** | Worker | Unified "Theory Deck" layout preset | Scalp / Structure / **Learn** v3 |
| **W10.12** | Worker | Multi-symbol decision queue | One ranked queue across symbols, brief on click |
| **W10.13** | Worker | GA runbook + onboarding | `docs/RELEASE_10.0_RUNBOOK.md` |

**Definition of done (GA):**

- [ ] ≥5 Core14 symbols in motor universe (not all auto-live; mix shadow/graduated/paper)
- [ ] Golden-path-style checklist **per symbol** automated (factory 7.0 pattern reused)
- [ ] Knowledge corpus ≥50 ingested chunks with provenance; every auto-execute cites retrieval
- [ ] Self-learning: 30 days paper, ≥3 approved patches, 0 unapproved auto-applied patches
- [ ] Kill switch stops all symbols < 1 s; paper default on cold start
- [ ] Filipe sign-off on decision simplicity (primary GA gate)

---

## 3. Performance & robustness

### Low-RAM evolution (7.0 → 10.0)

| Area | 7.0 | 10.0 target |
|------|-----|-------------|
| Stack budget | 1.2 GB | **1.5 GB** with knowledge lazy-loaded; **2.0 GB** only when `KNOWLEDGE_GPU_EMBED=1` batch job running |
| Ollama | Off in low-RAM / golden path | **On demand only**: briefs, patch proposals — never per-quote SSE |
| Vector index | N/A | sqlite-vec; max **10k chunks** hot; archive cold corpus to second file |
| SSE | PETR4-only option | Per-symbol subscribe; disconnect on hidden tab (carry forward) |
| Embeddings | N/A | `fastembed` CPU ~50 MB; CUDA batch in subprocess, exit after job |

**New env flags (proposed):**

```env
KNOWLEDGE_ENABLED=true
KNOWLEDGE_MAX_CHUNKS=10000
KNOWLEDGE_EMBED_MODEL=BAAI/bge-small-en-v1.5   # or multilingual for PT books
KNOWLEDGE_GPU_EMBED=false                     # true only during ingest job
AUTONOMOUS_DEGRADED_MODE=auto                 # see self-healing
```

### Self-healing architecture

```
┌──────────────┐     every 30s      ┌─────────────────┐
│ Health loop  │ ─────────────────► │ HealthRegistry   │
│ (async task) │                    │ api|bridge|ollama│
└──────────────┘                    │ motor|knowledge  │
        │                           └────────┬─────────┘
        │ degraded                         │
        ▼                                    ▼
┌──────────────┐                    ┌─────────────────┐
│ Circuit      │                    │ Motor: pause     │
│ breakers     │ ◄── trip on N errs │ auto-execute     │
└──────────────┘                    │ SSE: stub quotes │
        │                           │ UI: yellow banner│
        │ half-open probe            └─────────────────┘
        ▼
┌──────────────┐
│ Auto-restart │  subprocess watchdog in dev.py (bridge, ollama optional)
│ (bounded)    │  max 3 restarts / 15 min — then stay degraded + alert
└──────────────┘
```

| Component | Trip condition | Degraded behavior | Recovery |
|-----------|----------------|-------------------|----------|
| Profit bridge | 5 failures / 60 s | Stub quotes + block live execute | Half-open probe every 60 s |
| Ollama | Timeout or 503 | Skip brief; show retrieval-only cards | Lazy probe on next brief request |
| SQLite | `database is locked` ×3 | Motor skip write cycle; queue journal | Backoff + WAL checkpoint |
| RAM | > `effective_ram_budget_mb` | Drop knowledge search cache; extend motor interval | Ops alert; no auto kill |
| Ingest job | RSS > cap | Pause chunking; resume checkpoint | Manual or scheduled retry |

**Supervisor tasks (9.x prep, required for 10.0-rc):** `A9.x` health registry, circuit breakers in `profit_bridge` + motor orchestrator, `GET /api/v1/ops/health/deep`.

### Observability

- **Structured events:** `MotorJournal` + new `SystemEvent` types: `circuit_open`, `degraded_enter`, `patch_proposed`
- **Traces:** motor phase breakdown (already in 7.0) + `brief_ms`, `retrieve_ms`, `embed_job_ms`
- **Dashboards:** ops panel v2 — health matrix, degraded mode indicator, corpus size
- **Scripts:** extend `status_tick.py --json` with `knowledge`, `degraded`, `circuits`
- **No Prometheus requirement** — local JSON files under `data/.dev/` match existing test_worker pattern

---

## 4. Autonomous engine 2.0

Evolution of `src/autonomous/engine.py` — from daily global routine to **per-symbol state machines**.

### Principles

1. **Symbol-scoped routines** — each motor universe symbol has `SymbolAutonomyState`: `shadow | scanning | paper_auto | graduated | live_unlocked`
2. **Walk-forward as promote gate** — keep `run_walk_forward_promotion`; add **per-symbol** fold history in rankings
3. **Promote gates (stacked)** — all must pass for `paper_auto`:

   | Gate | Source |
   |------|--------|
   | `backtest_proof` | PF ≥ 1.3, DD ≤ 8% |
   | WFO | ≥4 folds, no fold PF < 1.0 |
   | Golden path subset | Reconcile ±2%, error rate < 5% |
   | Trust scorecard | ≥ 85% |
   | Theory grounding | Brief generated without hard conflict |
   | Human | Approve graduation UI click |

4. **Paper → live graduation** — separate track; requires Phase C sign-off per symbol; kill switch resets to `paper_auto`

### Engine loop (conceptual)

```
for symbol in motor_universe:
    if circuit_breaker.open: continue
    state = factory.get_state(symbol)
    if state == shadow: scan + ideas only
    if state >= paper_auto: scan → rank → auto-confirm if gates → auto-execute paper
    on fill: journal → outcome_ranker → maybe patch_proposal (async, offline)
    nightly: WFO slice for symbol + distill rules (offline)
```

**Avoid:** LLM choosing position size or bypassing `RiskGuardian`.

---

## 5. Knowledge layer — realistic architecture

> **User vision:** feed books, papers, videos, theory to Ollama so the app learns and simplifies decisions.  
> **Grounded approach:** RAG + rule distillation + human-approved patches — **not** fine-tuning Ollama on every PDF.

### Why not fine-tune by default

| Approach | RAM | Risk | Fit |
|----------|-----|------|-----|
| Fine-tune per PDF | High VRAM, slow | Catastrophic forgetting, hallucination on gates | Poor |
| RAG + citations | Low incremental | Source traceable, disable per corpus | **Best** |
| LoRA on weekly journal | Medium | Overfits noise | Optional 10.1+ research |

### Ingestion pipeline

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ PDF/epub/   │   │ Extract text │   │ Chunk 512-  │   │ Embed batch  │
│ txt/md/     │──►│ (pymupdf /   │──►│ 768 tokens  │──►│ fastembed /  │
│ VTT transcript│  │ ebooklib)    │   │ + overlap   │   │ CUDA optional│
└─────────────┘   └──────────────┘   └─────────────┘   └──────┬───────┘
                                                              │
                                                              ▼
                                                    ┌──────────────────┐
                                                    │ sqlite-vec table │
                                                    │ + metadata JSON  │
                                                    │ (source, page,   │
                                                    │  lang, tags)     │
                                                    └──────────────────┘
```

**YouTube path:** prefer manual transcript paste or `yt-dlp --write-auto-sub` → VTT → same chunker. Local Whisper is **optional** (GPU/RAM heavy); not default in low-RAM.

### Vector store choice: **sqlite-vec**

| Option | Verdict |
|--------|---------|
| **sqlite-vec** | **Pick** — same WAL discipline as `arbitragem.db`; backup one folder; no extra daemon |
| ChromaDB | Viable but second process + RAM overhead |
| LanceDB | Excellent for huge corpora; overkill for <10k chunks on laptop |

Store vectors in `data/knowledge.db` (separate file to keep main DB slim) or attach as `knowledge_vec` with FK to chunk metadata.

### Theory cards

Bridge between retrieval and UI:

```json
{
  "id": "tc_042",
  "title": "VWAP reclaim — failed auction",
  "source": "kozlowski_market_structure.pdf",
  "page": 88,
  "excerpt": "…",
  "tags": ["vwap_reclaim", "auction", "scalp"],
  "symbols": ["PETR4", "PRIO3"],
  "linked_ideas": [1204],
  "linked_patterns": ["vwap_reclaim"]
}
```

Cards are **curated views** over chunks — auto-created on link, human-editable title/tags in library UI.

### Simplification outputs

| Artifact | Purpose |
|----------|---------|
| **Decision brief** | ≤5 bullets: thesis, trigger, stop, target, *when skip* + `[card:tc_042]` citations |
| **Rule distillation** | Offline job proposes `axiom_candidates.json` — e.g. "Skip first 5 min B3" with support count |
| **Conflict detection** | Brief vs `RiskProfile` vs `backtest_proof` — surface before confirm |

### Ollama role (strictly bounded)

- **Do:** synthesize retrieved chunks + scan context into brief; analyze trade with journal row attached; comment on ranking (existing `OllamaStrategist`)
- **Do not:** run on SSE path; invent citations (must pass citation validator — chunk ID exists); override kill switch

**Prompt pattern:** system prompt + `CONTEXT:` block of retrieved chunks only + JSON schema for brief bullets.

### GPU

- **Embeddings:** batch ingest in subprocess with `KNOWLEDGE_GPU_EMBED=true` when `detect_compute_device()` reports CUDA
- **Ollama:** user runs `ollama serve` with GPU layers via Ollama's own config — app does not manage LLM VRAM
- **Fallback:** CPU embed + smaller model (`bge-small`); brief latency acceptable offline

### Portuguese + B3 context

- Ingest PT-BR books natively; store `lang` metadata
- Prefer multilingual embed model (`paraphrase-multilingual-MiniLM-L12-v2` or `bge-m3` if RAM allows)
- Tags map to scanner patterns in `src/autonomous/scanner.py` and sector baskets in `filipe_universe.py`

---

## 6. Technology recommendations

### Add (10.0)

| Tech | Use |
|------|-----|
| **sqlite-vec** | Vector search, local, backup-friendly |
| **fastembed** or **sentence-transformers** | Embeddings (choose one; fastembed lighter) |
| **pymupdf** | PDF text extract |
| **Polars lazy** | Ingest batch analytics, journal ranking aggregates — **not** hot API path |
| **pydantic v2** | Knowledge + patch schemas (already in stack) |
| **watchdog** (optional) | `data/knowledge/inbox/` drop folder for ingest |

### Optional (later)

| Tech | When |
|------|------|
| **Redis** | Only if SSE fan-out or multi-process API — **not needed** for Filipe's single-machine 10.0 |
| **Temporal / Celery** | Overkill — use existing motor + `asyncio.to_thread` + ingest CLI |
| **LangChain** | Avoid heavy framework; thin RAG in `src/services/knowledge/` |
| **Whisper local** | YouTube without captions — manual path first |

### Avoid

| Tech | Why |
|------|-----|
| Cloud vector DB (Pinecone, etc.) | Violates local-first; 7.0 principle |
| Fine-tune on every upload | RAM, safety, maintenance |
| Clear scrapers | Already excluded in 4.0 |
| Second uvicorn worker | SQLite + motor singleton — stay `--workers 1` |
| Real-time full-corpus re-embed | Batch only |

---

## 7. Self-learning loop

```
 Trade outcome (journal FILL)
        │
        ▼
 Outcome ranker ──► pattern × symbol stats (PF, win%, slippage, time-of-day)
        │
        ▼
 Retrieve theory cards/chunks for that pattern
        │
        ▼
 Patch proposal generator (Ollama + structured diff)
        │
        ▼
 Human approve/reject in board drawer
        │
        ▼
 Symbol factory config update + audit log
        │
        └──────► next scan uses new thresholds (paper only until re-graduated)
```

**Ranking inputs:** `MotorJournal`, `Trade`, `BacktestRun`, `OptimizationRun`, archaeology timeline (4.2).

**Proposal types (enum):**

- `threshold_adjust` — scanner min volume, ATR band
- `gate_adjust` — PF floor per symbol
- `session_filter` — exclude open auction
- `sizing_adjust` — within `RiskProfile` caps only

**Hard rule:** no proposal may increase daily loss limit or disable kill switch.

---

## 8. Security & safety

| Control | Implementation |
|---------|----------------|
| **Kill switch** | Existing `POST /risk/kill-switch` — blocks all auto-execute |
| **Paper default** | Cold start `paper_trading_mode=true`; live requires per-symbol unlock file + UI |
| **Knowledge poisoning** | Ingest only from `data/knowledge/inbox/` + explicit URI allowlist; hash dedupe; no HTML URL fetch by default |
| **Citation validator** | Brief must reference chunk IDs that exist; reject hallucinated refs |
| **Prompt injection in PDF** | Strip "ignore previous instructions" patterns; display raw excerpt alongside brief |
| **Patch audit** | Immutable `patch_audit.jsonl` |
| **Crypto** | Watch-only unless `CRYPTO_AUTO_ENABLED=false` default |
| **Secrets** | Still `.env` only — no tokens in corpus |

---

## 9. What NOT to build (scope traps)

- **Hedge-fund multi-asset portfolio optimizer** — stay Core14 + optional crypto watch
- **Social auto-trade** — RSS/Twitter remain read-only signals (4.1 rule)
- **Hosted SaaS / multi-tenant auth** — local-first
- **Replacing Profit with Clear** — Profit bridge remains truth
- **Autonomous live without graduation** — no "YOLO" mode
- **Real-time fine-tuning** on every trade
- **Full browser inside app** for YouTube — ingest transcripts only
- **Pair-only strategies** until both legs pass individual graduation (7.0 rule carries)
- **GPU-required path** — always CPU fallback
- **Replacing HTMX board with Electron** — Streamlit stays analytics-only

---

## 10. Suggested first 3 milestones (start tomorrow)

These are deliberately small, shippable, and parallelizable — **Supervisor + Worker same sprint**.

### Milestone 1 — **A10.1 + W10.1** Knowledge DB + library shell

| ID | Owner | Deliverable |
|----|-------|-------------|
| **A10.1** | Supervisor | `src/services/knowledge/store.py` — sqlite-vec schema, chunk table, empty search |
| **W10.1** | Worker | Board partial: library panel with "corpus empty" state + file drop UI (POST stub) |

**Exit:** `GET /api/v1/knowledge/status` → `{chunks:0}`; board panel renders; tests green.

### Milestone 2 — **A10.2 + W10.2** First ingest path (txt/md)

| ID | Owner | Deliverable |
|----|-------|-------------|
| **A10.2** | Supervisor | `scripts/ingest_knowledge.py --path docs/STRUCTURES.md` — chunk + CPU embed + search CLI |
| **W10.2** | Worker | HTMX search box calling `/knowledge/search`; snippet list |

**Exit:** Search "iron condor" (or PT term) returns STRUCTURES chunks; RAM snapshot unchanged ±50 MB.

### Milestone 3 — **A10.6 + A10.4** Resource profile + API contract

| ID | Owner | Deliverable |
|----|-------|-------------|
| **A10.6** | Supervisor | `knowledge_enabled` in `resource_profile.py`; disabled when `low_ram_enabled` unless `KNOWLEDGE_ENABLED=1` |
| **A10.4** | Supervisor | Document + implement search endpoint; update `docs/agent_integration.md` |

**Exit:** Golden path mode keeps knowledge off hot path; explicit opt-in documented in `.env.example`.

---

## Appendix A — Gap fill from `docs/agent_integration.md`

10.0 should close or extend:

| Gap today | 10.0 action |
|-----------|-------------|
| Walk-forward on tick data | Still stub/synthetic unless DLL candles — **do not block 10.0**; brief cites backtest limitations |
| Ollama disabled low-RAM | Knowledge ingest/briefs opt-in with RAM cap |
| No RAG contract | New § Knowledge in agent_integration |
| Autonomous motor off by default | Graduation makes per-symbol opt-in explicit |
| Worker archaeology UI | Link archaeology events to theory cards (10.0-beta) |

---

## Appendix B — Version lineage

| Release | Focus |
|---------|-------|
| **7.0** | PETR4 golden path, symbol factory, RAM budget |
| **8.x** *(planned)* | Factory at scale, 5+ symbols shadow, desk multi-symbol |
| **9.x** *(planned)* | Health loop, circuit breakers, engine 2.0 scheduler skeleton |
| **10.0** | Knowledge layer + grounded autonomy + self-learning loop |

---

*Local-first. Grounded decisions. Human approves what learns.*

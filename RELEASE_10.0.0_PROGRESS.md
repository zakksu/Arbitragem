# Release 10.0.0 — Progress (Eternal Golden Path)

**Version:** `10.0.0` **GA**  
**Agent 1 (Backend):** COMPLETE  
**Agent 2 (UI):** COMPLETE

---

## Shipped — alpha through GA

| Phase | Backend | UI |
|-------|---------|-----|
| **Alpha** | Replay engine, strategy store, knowledge FTS, engine mind, self-healing | Engine Mind, Replay Player, Companion, Briefing, Strategy Store, Knowledge library |
| **Beta** | Theory cards, decision brief, conflict detector, rule distill | Brief on confirm, theory chips, conflict block |
| **RC** | Patch proposals, outcome ranker, paper graduation | Learning rail, patch drawer, graduation badges |
| **GA** | Motor universe, poison guard, health registry | Theory Deck layout, decision queue, degraded banner, ops corpus |

---

## API surface

```http
POST /api/v1/replay/run
GET  /api/v1/engine/mind
GET  /api/v1/knowledge/search?q=
POST /api/v1/ideas/{id}/brief
GET  /api/v1/autonomous/patches
POST /api/v1/autonomous/patches/{id}/approve
GET  /api/v1/symbols/{sym}/graduation
GET  /api/v1/self-healing/health
GET  /api/v1/daily-briefing
```

Board partials: `/board/partials/engine-mind`, `learning-rail`, `decision-queue`, `replay-player`, `profitchart-companion`, `strategy-store`, `daily-briefing`, `knowledge-library`.

---

## Tests

```powershell
pytest tests/test_10_0_ga.py tests/test_10_0_ui_ga.py tests/test_engine_mind_10_0.py tests/test_knowledge_store.py tests/test_replay_engine_10.py -q
```

---

## Manual GA bar (Filipe)

- [ ] 5 green B3 golden-path sessions
- [ ] Decision briefs feel simpler than 4.0 symbol report
- [ ] ≥1 approved patch from real journal data
- [ ] Stack RSS ≤ 1.5 GB under real load

See [RELEASE_10.0_VISION.md](RELEASE_10.0_VISION.md) for 11.x follow-ups (live graduation per symbol, GPU embed batch).

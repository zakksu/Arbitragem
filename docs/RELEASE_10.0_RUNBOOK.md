# Release 10.0.0 — Runbook (Eternal Golden Path)

**Version:** `10.0.0` · **Board:** http://localhost:8000/board

## One command start

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/dev.py start --wait --open
```

## Golden path checklist

1. Set `GOLDEN_PATH_MODE=true` in `.env` for PETR4-only motor.
2. Open board → golden path checklist + ops strip green.
3. Run `python scripts/status_tick.py --json` — verify `ram_mb` ≤ budget.

## Knowledge corpus

```powershell
python scripts/ingest_knowledge.py --path docs/STRUCTURES.md --symbol PETR4
python scripts/ingest_youtube.py --path transcripts/lesson.vtt --title "Aula VWAP"
curl -X POST http://localhost:8000/api/v1/knowledge/ingest/strategies
```

Search: `GET /api/v1/knowledge/search?q=vwap+reclaim&symbol=PETR4`

## Replay training loop

- Automatic: scheduler every `REPLAY_TRAINING_INTERVAL_MIN` minutes.
- Manual: `POST /api/v1/replay/training/run`
- Engine Mind footer shows cycle breakdown.

## Decision flow (Theory Deck)

1. Scanner generates idea → theory cards auto-attached (`meta.theory_cards`).
2. `POST /api/v1/ideas/{id}/brief` → ≤5 bullets + conflicts.
3. Confirm blocked when `conflicts[].severity == hard`.
4. Paper execute within graduation gates.

## Self-learning patches

```http
POST /api/v1/autonomous/patches/generate
GET  /api/v1/autonomous/patches
POST /api/v1/autonomous/patches/{id}/approve
POST /api/v1/autonomous/patches/{id}/reject
```

## B3 history import

```http
POST /api/v1/archaeology/import/excel
```

Upload Filipe's full `.xlsx` export from Profit/CEI.

## Kill switch

```http
POST /api/v1/risk/kill-switch
{"active": true, "reason": "manual halt"}
```

Pauses all sleeves & active strategies in &lt;1s.

## Graduation per symbol

`GET /api/v1/symbols/{sym}/graduation` — fills, reconcile, trust ≥85%, motor membership.

## Manual GA sign-off (Filipe)

- [ ] 5+ Core14 symbols in factory shadow/motor mix
- [ ] Knowledge corpus ≥50 chunks
- [ ] 3+ approved patches, 0 unapproved auto-applied
- [ ] Decision briefs feel simpler than 4.0 symbol report

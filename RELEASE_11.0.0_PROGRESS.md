# Release 11.0 — Progress tracker

**Version target:** `11.0.0` (GA)

## Shipped

| Phase | Scope | Status |
|-------|--------|--------|
| 11.0-alpha | FIFO archaeology P&L, summary API, insights ingest, layout presets | ✅ |
| 11.0-beta | Strategy Lab strip, structure replay, NTSL match | ✅ |
| 11.0-rc | Core17 scanner, sector strip + corr, motor queue 12, pack version, options refresh | ✅ |

## API highlights

- `SCANNER_MODE=filipe_core17`
- `GET /api/v1/universe/filipe-core17`
- `POST /api/v1/knowledge/ingest/insights`
- `POST /api/v1/options/core17/refresh`
- Strategy store scan returns `pack_version` + diff counts

## GA gates (manual)

- ≥9,000 archaeology rows imported
- 50 NTSL indexed
- Phase C sign-off (`docs/PHASE_C_GATE.md`)

## Tests

```powershell
pytest tests/test_filipe_core17.py tests/test_11_0_strategy_lab.py tests/test_b3_history_import.py -q
```

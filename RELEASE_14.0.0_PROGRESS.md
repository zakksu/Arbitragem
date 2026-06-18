# Release 14.0.0 — Progress

**Version:** `14.0.0-alpha`

## Backend (Agent 1) — shipped this increment

| ID | Deliverable | Status |
|----|-------------|--------|
| A14.1 | `board_tab_metadata()` + `GET /api/v1/board/tabs` | ✅ |
| A14.2 | `pnl_intraday.py` — intraday buckets + lanes | ✅ |
| A14.3 | `GET /pnl/intraday` + `GET /pnl/projection` | ✅ |
| A14.4 | `GET /board/stream/pnl` SSE (5s) | ✅ |
| — | `GET /board/partials/journal-tab` + filters | ✅ |
| — | `PATCH /api/v1/trades/{id}/note` | ✅ |
| — | Journal desk filters (`range`, `symbol`, `setup_tag`) | ✅ |

## Worker (Agent 2) — in progress

| ID | Deliverable | Status |
|----|-------------|--------|
| W14.1 | Tab bar + `?tab=` routing | 🔲 |
| W14.2 | Remove journal from Desk | 🔲 |
| W14.3 | `journal_tab.html` polish | partial |
| W14.5 | PnL chart + SSE client JS | partial |

## Tests

```powershell
pytest tests/test_pnl_intraday.py -q
```

**10 passed** (14.0 backend slice).

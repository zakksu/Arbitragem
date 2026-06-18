# Release 14.0.0 — Progress

**Version:** `14.0.0` (GA)

## Shipped

| Phase | Scope | Status |
|-------|--------|--------|
| 14.0-alpha | Tab shell, journal off desk, `blackboard_14_0.css` | ✅ |
| 14.0-beta | `pnl_intraday.py`, API, SSE `/board/stream/pnl`, PnL tab chart | ✅ |
| 14.0-rc | Strategy Lab strip, learning rail, engine mind on desk, layout presets | ✅ |
| 14.0-GA | Journal filters, trade notes API, PnL 5D/20D, status sparkline, mobile CSS | ✅ |

## Tests

```powershell
pytest tests/test_14_0_ui.py tests/test_pnl_intraday.py -q
```

## Board

- Desk: http://localhost:8000/board
- Journal: http://localhost:8000/board?tab=journal
- PnL: http://localhost:8000/board?tab=pnl

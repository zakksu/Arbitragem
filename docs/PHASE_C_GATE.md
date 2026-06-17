# Phase C gate — live Profit execution

Phase C ships **only after** paper trading journal proves the agent is trustworthy.

## Criteria (all required)

| # | Check | Target |
|---|--------|--------|
| 1 | Paper sessions with motor ON | ≥ 5 full B3 days |
| 2 | Motor journal errors | < 5% of cycles |
| 3 | Executed trades with journal FILL rows | ≥ 20 |
| 4 | Day P&L vs Profit truth | Within 2% when bridge sync on |
| 5 | Manual review | Filipe signs off on blotter accuracy |

## Phase C deliverables

- Profit DLL ctypes order placement (replace stub)
- Chart Trading hint → optional auto-arm
- Kill switch tested on live account profile
- Strong passwords (replace admin/admin)
- Optional: hosting for **read-only** remote desk (not execution)

## Until gate passes

- `EXECUTION_BACKEND=profit` + stub bridge + outbox NTSL
- `PAPER_TRADING_MODE=true`
- Sim account **3368** only

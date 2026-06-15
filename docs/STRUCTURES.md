# Structure types — Structure Deck 3.0

User guide for multi-leg options structures on the HTMX blackboard (`/board`).

## Overview

Each trade idea has a `structure_type` and `legs[]`. Confirm exports **NTSL** to `exports/profit/` for Profit Editor import. Paper mode logs fills locally — no Clear API required.

## Structure types

| Type | Legs | When to use |
|------|------|-------------|
| **scalp** | Single cash leg | Intraday Core14 momentum |
| **covered_call** | Long stock + short OTM call | IV rank high, bullish bias |
| **vertical** | Buy/sell call spread | Defined-risk directional |
| **collar** | Stock + long put + short call | Protect long with capped upside |
| **bova_hedge** | Core14 cash + BOVA put | Basket beta hedge vs IBOV |
| **pair_spread** | Long weak / short strong | PETR/PRIO or steel basket z-score |

## Gates before confirm

1. **Backtest gate** — PF ≥ 1.3, max DD ≤ 8% (`BACKTEST_MIN_PROFIT_FACTOR`, `BACKTEST_MAX_DRAWDOWN_PCT`)
2. **Portfolio gate** — net delta after confirm ≤ `MAX_PORTFOLIO_NET_DELTA` (default 0.5)
3. **Walk-forward badge** — ideas promoted via nightly job show `WF N/4`

## 2-step confirm flow

1. **Review** — legs, backtest proof, structure summary
2. **Confirm** — risk cockpit warning, portfolio impact, NTSL export

On mobile (≤768px) the board shows **Idea Stack + confirm only**.

## BOVA hedge sizing

`bova_hedge` uses delta-aware sizing (`src/services/bova_hedge.py`):

- Estimates cash beta vs IBOV
- Picks ATM BOVA put from chain
- Sizes put qty for target delta neutrality

Preview in Structure Builder shows hedge ratio before create.

## NTSL export

Per-structure templates in `src/services/ntsl_templates.py`:

- Comments describe leg order (cash first, then options)
- Import in Profit Editor → arm on underlying
- Live execution remains manual — paper mode default

## Kill switch

**STOP ALL** in status bar:

- Pauses all active strategies
- Rejects pending ideas (`detected` / `backtested`)
- Logs `kill_switch` system event

## Opportunity rail

Footer shows PETR/PRIO and steel basket z-scores plus sector heat from `GET /api/v1/signals/opportunity-rail`.

## Layout presets

Status bar: **scalp** | **options_hedge** | **pairs** — saves column widths via `POST /api/v1/board/layout/{preset}`.

## Paper first

Keep `PAPER_TRADING_MODE=true` until journal review of at least 5 structure trades (paper week #2).

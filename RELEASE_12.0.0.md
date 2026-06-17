# Release 12.0.0 — Live Tomorrow (Clear stocks · 100 lots)

**Version:** `12.0.0` (GA shipped)  
**Prerequisite:** [RELEASE_11.0.0.md](../RELEASE_11.0.0.md) scope (Hybrid Cockpit, Live Radar, archaeology)  
**Broker:** [Clear Corretora](https://corretora.clear.com.br/custos/) + ProfitChart execution  
**Codename:** First Light

**Shipped in 12.0.0 GA:**
- Live Radar (`GET /api/v1/ops/live-radar`, board partial, `status_tick.py` mirror)
- Clear/B3 cost chip on confirm + breakeven gate on `POST /ideas/{id}/confirm`
- Bridge `/health` exposes `dll_mode`, `is_paper`
- Crypto watchlist/paper **off by default** (deferred from active scope)

---

## Executive summary

Release 12.0 makes **manual live stock scalps** on B3 **tomorrow-ready**: fixed **100-share lots**, **Clear/B3 cost math** in the confirm path, **pre-market checklist**, and an honest split between **manual Chart Trading** (now) vs **DLL auto** (Phase C).

**Crypto live is deferred** — Binance in the app is read-only quotes + paper only; we do not have a signed broker margin/fee policy for live crypto execution.

---

## Clear cost model (100-share day trade)

Source: [Clear custos operacionais](https://corretora.clear.com.br/custos/) — day trade ações.

| Fee | Rate | Notes |
|-----|------|-------|
| Corretagem Clear | **R$ 0** | Electronic + RLP |
| Emolumentos B3 | **0.005%** | per leg |
| Taxa liquidação B3 | **0.018%** | per leg |
| **Total B3 per leg** | **0.023%** | of notional |
| **Round trip (buy+sell)** | **~0.046%** | of notional |

### Worked example — PETR4 @ R$38, 100 shares

| Item | Value |
|------|-------|
| Notional per leg | R$ 3,800 |
| B3 fees per leg | ~R$ 0.87 |
| **B3 round trip** | **~R$ 1.75** |
| Tick value (R$0.01 × 100) | R$ 1.00 |
| Slippage (1 tick/side) | ~R$ 2.00 |
| **Breakeven friction** | **~3–4 ticks** (~R$ 4) |
| Margin @ 50× leverage | R$ 76 |
| Margin @ 125× (Clear example) | R$ 30 |

**R$500 account:** afford **~6 lots @ 50×** on paper — trade **1 lot max**; daily loss cap **R$50**.

Code: `src/services/clear_cost_model.py` · data: `data/clear_costs.json`  
API: `GET /api/v1/costs/scalp/{symbol}?price=38&quantity=100&leverage=50`

---

## Crypto policy (explicit deferral)

| Topic | Status |
|-------|--------|
| Binance spot quotes | Read-only in dashboard |
| Binance live orders | **Not shipped** — no Clear-equivalent fee/margin contract in repo |
| B3 crypto futures (BIT/ETR/SOL) | Margins published on Clear custos page; **phase 13+** after stock path proven |
| `CRYPTO_PAPER_ENABLED` | Paper sleeve only |

Do not enable live crypto until: broker API + margin table + fee model + tests exist (same bar as `clear_cost_model`).

---

## Are we ready to trade live tomorrow?

### Manual live (Chart Trading) — **YES, if checklist passes**

| Requirement | How to verify |
|-------------|---------------|
| Stack up | `python scripts/dev.py start --wait` |
| Pre-market | `python scripts/premarket_check.py --symbol PETR4 --price 38 --capital-brl 500` |
| Profit bridge | `http://localhost:9100/health` → OK |
| Board | MOTOR + Profit OK + GATE OK |
| Live mode | `PAPER_TRADING_MODE=false`, `PROFIT_LIVE_STYLE=day`, day account ID |
| Risk | `DEFAULT_DAILY_LOSS_LIMIT_BRL=50`, `DEFAULT_MAX_OPEN_POSITIONS=1` |
| Execution | Confirm idea → outbox hint → **click in Profit Chart Trading** |

### Auto-live (motor fires DLL orders) — **NO**

| Blocker | Until |
|---------|-------|
| Phase C gate | 5 paper days, 20 fills, P&L reconcile ([PHASE_C_GATE.md](PHASE_C_GATE.md)) |
| DLL ctypes orders | `profit_dll_bridge.py` callbacks wired |
| Live Radar `ready_to_execute` | Phase 12.0-rc |

---

## Tomorrow morning runbook (Filipe)

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/dev.py start --wait
python scripts/premarket_check.py --symbol PETR4 --price 38 --capital-brl 500
```

1. Open http://127.0.0.1:8000/board — Live Radar (when shipped) or status bar all green.  
2. Open ProfitChart on **day account** with RLP active.  
3. Golden path / scanner: start with **one symbol** (PETR4 or VALE3 from archaeology).  
4. Idea → confirm → read **cost breakeven** in brief → execute hint in Profit.  
5. **One position at a time**; stop day at −R$50.  
6. EOD: reconcile P&L board vs Profit; journal in motor.

**.env for first live day (manual):**

```env
PAPER_TRADING_MODE=false
EXECUTION_BACKEND=profit
PROFIT_BRIDGE_ENABLED=true
MOTOR_FIXED_LOT_SHARES=100
STOCK_DAY_LEVERAGE_ASSUMED=50
PAPER_CAPITAL_BRL=500
DEFAULT_DAILY_LOSS_LIMIT_BRL=50
DEFAULT_MAX_OPEN_POSITIONS=1
GOLDEN_PATH_MODE=true
```

---

## Strategy pack — stock scalps (100 lots)

Aligned with external algo research ([Bookmap](https://bookmap.com/blog/key-algorithmic-trading-strategies-from-trend-following-to-mean-reversion-and-beyond), [QuantInsti mean reversion](https://blog.quantinsti.com/mean-reversion-strategies-introduction-building-blocks/), session/bracket bots):

| ID | Structure | Entry | Stop | Target | Min edge |
|----|-----------|-------|------|--------|----------|
| **S1** | VWAP reclaim | Close back above VWAP | 4 ticks | 6 ticks | ≥4 ticks after costs |
| **S2** | Opening range break | 15m high/low break 10:00–12:00 | Range other side | 1.5× range | vol filter |
| **S3** | Mean reversion band | Touch lower BB + RSI&lt;35 | 5 ticks | VWAP | range day only |
| **S4** | Archaeology bias long | VALE3/PETR4 when history net flow green | 5 ticks | 8 ticks | symbol from insights |
| **S5** | Pulse scalp | Live Radar all green + sleeve CASH | 3 ticks | 5 ticks | max 3 trades/day |

**Futures (WIN/WDO)** remain in 11.0 scope — not primary for R$500 stock-first tomorrow path.

---

## Release 12.0 phases

### 12.0-alpha — Live Tomorrow (ship now)

| ID | Owner | Deliverable | Status |
|----|-------|-------------|--------|
| A12.1 | Backend | `clear_cost_model.py` + `data/clear_costs.json` | ✅ |
| A12.2 | Backend | `GET /costs/scalp/{symbol}` | ✅ |
| A12.3 | Backend | `MOTOR_FIXED_LOT_SHARES=100` in capital manager | ✅ |
| A12.4 | Backend | `scripts/premarket_check.py` | ✅ |
| W12.1 | Worker | Cost chip on confirm step / decision brief | ✅ |
| W12.2 | Worker | Live Radar lamps (from 11.0 spec) | ✅ |
| A12.5 | Backend | `GET /ops/live-radar` | ✅ |

### 12.0-beta — Cost-aware motor (1 week)

| ID | Task |
|----|------|
| A12.6 | Reject confirm if target ticks &lt; breakeven_ticks |
| A12.7 | Paper fills include `fees_brl` from cost model |
| W12.3 | Trade product shows margin + fees for 100 lot |
| A12.8 | Clear API sync trades when `CLEAR_API_KEY` set (optional) |

### 12.0-rc — Semi-auto live (after Phase C)

| ID | Task |
|----|------|
| A12.9 | DLL `place_order` wired |
| A12.10 | `ready_to_execute` true on Live Radar |
| W12.4 | Outbox auto-copy to clipboard |

### 12.0-GA

| Gate | Target |
|------|--------|
| Manual live week | 5 days, 20+ fills, P&L within 2% of Profit |
| Cost model | Breakeven within 1 tick of actual Clear note |
| Max positions | 1 concurrent 100-lot |
| Crypto | Still deferred or documented NO |

---

## Master timeline (11.0 + 12.0)

```
Week 0 (tomorrow)     12.0-alpha manual live — PETR4/VALE3, 100 lot, Chart Trading
Week 1–2              12.0-beta cost gates + Live Radar UI
Week 2–4              11.0-alpha archaeology + hybrid cockpit
Week 4+               Phase C → 12.0-rc semi-auto
Later                 B3 BIT/ETR futures OR Binance (only with broker cost model)
```

---

## Tests

```powershell
pytest tests/test_clear_cost_model.py tests/test_b3_history_import.py -q
python scripts/premarket_check.py --json
curl "http://127.0.0.1:8000/api/v1/costs/scalp/PETR4?price=38"
```

---

## Related

- [RELEASE_11.0_SCOPE.md](RELEASE_11.0_SCOPE.md) — Hybrid cockpit, futures, archaeology  
- [PHASE_C_GATE.md](PHASE_C_GATE.md) — auto-live gate  
- [profit_bridge.md](profit_bridge.md) — DLL + outbox  
- [Clear custos](https://corretora.clear.com.br/custos/)

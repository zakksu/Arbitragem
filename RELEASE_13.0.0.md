# Release 13.0.0 — Core5 desk · Replay factory · Phase C live

**Version:** `13.0.0`  
**Prerequisite:** [RELEASE_12.0.0.md](RELEASE_12.0.0.md)  
**Capital model:** R$1.000 · Clear/B3 costs · daily **stop-loss** only (no trade count cap)

---

## Universe (locked)

| Bucket | Symbols |
|--------|---------|
| **Core5 stocks** | PETR4, VALE3, ITUB4, BOVA11, PRIO3 |
| **Options** | On Core5 + BOVA chain only |
| **Futures** | WINFUT, WDOFUT only |
| **Excluded** | Core14/17 extras, crypto, pairs sleeve focus |

`SCANNER_MODE=filipe_core5` · `data/filipe_core5.csv`

---

## 13.0-alpha — Lock & paper (shipped)

| ID | Deliverable |
|----|-------------|
| A13.1 | `filipe_core5` scanner mode + CSV |
| A13.2 | `AUTONOMY_MAX_TRADES_PER_DAY=0` → unlimited trades |
| A13.3 | Loopback health probe (fixes false `api_offline`) |
| A13.4 | Paper auto defaults: R$1k, 20s motor, stop-loss R$100 |

---

## 13.0-beta — Replay factory (shipped)

| ID | Deliverable |
|----|-------------|
| A13.5 | `POST /api/v1/replay/batch` + `scripts/replay_batch_runner.py` |
| A13.6 | WFO auto-promote on Core5 symbols |
| A13.7 | `strategies/ntsl/core5/` — S1–S5 stock + F1–F5 WIN templates |

Generate NTSL pack:

```powershell
python scripts/generate_core5_ntsl_pack.py
```

---

## 13.0-rc — Desk journal (shipped)

| ID | Deliverable |
|----|-------------|
| W13.1 | Board partial `/board/partials/trade-journal` |
| W13.2 | `GET /api/v1/journal/export.csv` |
| W13.3 | WIN archaeology overlay from B3 history |

---

## Phase C — Live auto (shipped)

| ID | Deliverable |
|----|-------------|
| A13.8 | `phase_c_gate.py` — criteria from [PHASE_C_GATE.md](docs/PHASE_C_GATE.md) |
| A13.9 | `ready_to_execute` true when gate + DLL + all green + live mode |
| A13.10 | WIN `cross_order` on bridge tickets |
| A13.11 | `live_capital_gate` — 1 WIN **or** 1 stock lot @ R$1k |

Manual sign-off override: `PHASE_C_SIGNED_OFF=true`

---

## Pre-open

```powershell
python scripts/dev.py start --wait
python scripts/premarket_check.py --json
python scripts/replay_batch_runner.py --json   # optional overnight
python scripts/status_tick.py --json
```

---

## Tests

```powershell
pytest tests/test_13_0_ga.py tests/test_live_radar.py -q
```

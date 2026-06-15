# ProfitChart / ProfitDLL Bridge

ProfitDLL is **Windows-only**. VPS (Linux) talks to a local HTTP bridge on your trading PC.

```
[Trading PC - Windows]                    [VPS - Linux]
 ProfitChart + ProfitDLL                      Docker Compose
       |                                      API + /board
 profit_dll_bridge.py  <--- Tailscale --->  PROFIT_BRIDGE_URL
```

## Bridge scripts

| Script | When |
|--------|------|
| `scripts/profit_bridge_stub.py` | Dev default — synthetic Core14 + BOVA chains |
| `scripts/profit_dll_bridge.py` | Windows + `PROFIT_DLL_PATH` set — prefers DLL, falls back to stub |

`python scripts/dev.py start --wait` auto-starts:

- `profit_dll_bridge.py` if `PROFIT_DLL_PATH` exists (Windows)
- else `profit_bridge_stub.py`

## Windows setup

1. Install ProfitChart with Módulo de Automação.
2. Set in `.env`:
   ```
   PROFIT_BRIDGE_ENABLED=true
   PROFIT_BRIDGE_URL=http://localhost:9100
   PROFIT_DLL_PATH=C:/Nelogica/Profit/ProfitDLL.dll
   ```
3. Run bridge:
   ```powershell
   python scripts/profit_dll_bridge.py
   ```
4. Health: `http://localhost:9100/health` → `mode: fallback` until ctypes wired, `version: 3.0.0`

## VPS / Tailscale

1. Install Tailscale on VPS and trading PC.
2. Bind bridge to Tailscale IP only (or localhost + tailscale serve).
3. VPS `.env`:
   ```
   PROFIT_BRIDGE_URL=http://100.x.x.x:9100
   ```
4. Never expose :9100 on public internet.

## HTTP contract (3.0)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Bridge mode + version |
| `GET /quotes/{symbol}` | Cash quote |
| `GET /options/chain/{underlying}` | Unified chain + max pain |
| `GET /greeks/{symbol}` | Option greeks |
| `GET /iv-rank/{underlying}` | IV rank proxy |
| `POST /backtest/run` | Stub backtest metrics |

## NTSL export flow

1. Confirm idea on board → NTSL written to `exports/profit/`
2. Profit Editor → Importar
3. Tick-a-Tick backtest → export CSV
4. Watcher promotes `backtest_proof` on ideas (`WALK_FORWARD_AUTO_PROMOTE=true`)

## Real DLL integration

Replace `_try_load_dll()` in `profit_dll_bridge.py` with Nelogica ctypes callbacks. Keep JSON HTTP surface unchanged so VPS needs no redeploy.

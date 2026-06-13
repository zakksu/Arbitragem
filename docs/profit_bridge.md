# ProfitChart / ProfitDLL Bridge

ProfitDLL is a **Windows-only** native library. Your VPS (Linux) cannot load it directly.
Use a **hybrid topology**:

```
[Trading PC - Windows]                    [VPS - Linux]
 ProfitChart + ProfitDLL                      Docker Compose
       |                                      API + Dashboard
 Profit Bridge (HTTP)  <---- VPN/SSH tunnel ---->  PROFIT_BRIDGE_URL
 Clear Smart Trader API  <---------------------->  CLEAR_API_*
```

## Steps on your trading PC

1. Install ProfitChart with Módulo de Automação.
2. Clone this repo (or copy `scripts/profit_bridge_stub.py`).
3. Run the bridge stub (replace with real DLL bindings later):
   ```powershell
   pip install fastapi uvicorn
   python scripts/profit_bridge_stub.py
   ```
4. Expose port 9100 only on localhost or via Tailscale/WireGuard to your VPS.
5. In VPS `.env`:
   ```
   PROFIT_BRIDGE_ENABLED=true
   PROFIT_BRIDGE_URL=http://YOUR_PC_TAILSCALE_IP:9100
   ```

## NTSL export flow

1. Edit strategy in dashboard → **Export NTSL to Profit**
2. File lands in `exports/profit/`
3. In ProfitChart: Editor de Estratégias → Importar
4. Run Tick-a-Tick backtest in Profit
5. Export CSV → upload path in dashboard **Backtest & Optimize** page

## Real ProfitDLL integration (next iteration)

- Request ProfitDLL docs from Nelogica
- Use `ctypes` or `pywin32` in `scripts/profit_bridge.py`
- Callbacks: quotes, trades, order book, strategy events
- Keep bridge thin — only serialize JSON over HTTP to VPS

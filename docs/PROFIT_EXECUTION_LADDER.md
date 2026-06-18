# Profit execution ladder (no DLL required)

Four rungs — pick one in `.env` via `PROFIT_EXEC_LADDER` or leave `auto`.

| Mode | When | What happens |
|------|------|----------------|
| **paper_stub** | Learning, Phase C paper days | Motor fills via HTTP stub; journal + PnL update instantly |
| **manual_outbox** | Profit open, no DLL | Ticket + `chart_trading_hint` → copy into Chart Trading (sim **3368**) |
| **ntsl_export** | Backtest in Profit Editor | NTSL written to `exports/ntsl/` + optional folder open on execute |
| **dll_auto** | ProfitDLL installed | Bridge loads DLL (full auto when ctypes callbacks ship) |

## Auto (default)

```
PAPER_TRADING_MODE=true  → paper_stub
DLL loadable            → dll_auto
else                    → manual_outbox (+ NTSL sidecar if PROFIT_NTSL_ON_EXECUTE=true)
```

## ProfitDLL / automation module

ProfitChart **does not ship** ProfitDLL in the default installer. It is a **separate Nelogica license** (“Módulo de Automação” / ProfitDLL).

**How to obtain (no public download URL):**

1. Profit → **Ajuda** → **Suporte** / chat Nelogica  
2. Broker or Nelogica sales — ask for **ProfitDLL / API de automação** on your license  
3. After install, `ProfitDLL.dll` usually appears under `%APPDATA%\Nelogica\Profit\` or `x64\`

Verify:

```powershell
python scripts/detect_profit_dll.py
python scripts/dev.py restart --wait
```

Until then use **paper_stub** or **manual_outbox**.

## Manual assist (one command)

```powershell
python scripts/profit_manual_assist.py
```

Copies latest Chart Trading hint to clipboard and opens `exports/ntsl/` in Explorer.

## API

- `GET /api/v1/profit/execution-ladder` — active mode + fallbacks  
- Execute/confirm responses include `execution_assist` when applicable

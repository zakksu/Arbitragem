# Integration setup wizard — what Filipe provides vs what agents detect

Use this with **Settings → Connect accounts** (2.0) or manually for 1.0.

---

## Quick checklist

| Integration | Auto-detect? | You must provide |
|-------------|--------------|------------------|
| API + dashboard | ✅ `dev.py start` | Nothing |
| Profit bridge stub | ✅ port 9100 | Nothing (dev) |
| ProfitDLL live | ✅ DLL file exists | Profit open, logged in, automation module |
| Ollama | ✅ `/api/tags` | `ollama serve` running |
| Clear live | ✅ keys in `.env` | API key, secret, account ID |

---

## Clear Corretora (live trading + balances)

### What we need in `.env`

```env
CLEAR_API_KEY=
CLEAR_API_SECRET=
CLEAR_ACCOUNT_ID=
PAPER_TRADING_MODE=false
```

### Where to find it (step by step)

1. Log in to **Clear Corretora** (site or app).
2. Open **Área do cliente** → look for **Smart Trader**, **API**, or **Integrações**.
   - If missing: email your **assessor** or Clear support: *“Preciso de acesso à API Smart Trader para automação.”*
3. **Create API credentials** (key + secret). Copy secret immediately — shown once.
4. **Account ID** = your brokerage account number (often shown in statements or account header).
5. Paste into `.env` and run:
   ```powershell
   python scripts/dev.py restart --wait
   ```
6. Dashboard → **Settings → Test Clear connection**.

### What agents cannot do

- Log in with your CPF/password or 2FA
- Enable API on your account (broker must approve)

### Verify in Arbitragem

```powershell
curl http://localhost:8000/api/v1/integrations/clear/test
```

Expect `"mock_mode": false` when configured.

---

## ProfitChart / Nelogica (quotes, backtests, automation)

### What we need

```env
PROFIT_BRIDGE_ENABLED=true
PROFIT_BRIDGE_URL=http://localhost:9100
PROFIT_DLL_PATH=C:/Nelogica/Profit/ProfitDLL.dll
PROFIT_EXPORT_DIR=./exports/profit
```

### Where to find it

1. **Install Profit** (Profit Pro) with **Módulo de Automação** on your **Windows trading PC**.
2. **DLL path:** after install, check:
   - `C:\Nelogica\Profit\ProfitDLL.dll`
   - Or search `ProfitDLL.dll` under `C:\Nelogica\`
3. **Keep Profit running and logged in** when using the bridge.
4. **Start bridge** (dev uses stub; 2.0 uses real DLL wrapper):
   ```powershell
   python scripts/profit_bridge_stub.py
   ```
   Or let `python scripts/dev.py start` launch it.
5. Dashboard → **Settings → Test Profit connection** — sample PETR4 quote + volume.

### Backtest exports (1.0 manual → 2.0 automatic)

1. Profit → **Editor de Estratégias** → import NTSL from `exports/profit/`
2. Run backtest → **Exportar CSV**
3. Save to `exports/profit/` or upload in **Backtest & Optimize**

**2.0:** bridge watches folder and ingests automatically.

### What agents cannot do

- Activate Nelogica license or accept EULA
- Click inside ProfitChart UI
- **Can:** run bridge, test quotes, parse CSV, export NTSL from API

### Verify

```powershell
curl http://localhost:9100/health
curl http://localhost:8000/api/v1/integrations/profit/test
```

---

## Ollama (AI reports & trade ideas)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_ENABLED=true
```

1. Install [Ollama](https://ollama.com)
2. `ollama pull llama3.2`
3. `ollama serve` (or run as service)

---

## Hybrid setup (VPS + home PC)

If dashboard runs on **VPS** and Profit on **Windows PC**:

1. Run Profit bridge on PC port 9100
2. Expose via **Tailscale** / WireGuard (not public internet)
3. VPS `.env`: `PROFIT_BRIDGE_URL=http://100.x.x.x:9100`

See `docs/profit_bridge.md`.

---

## When stuck — send this to your assessor (Clear)

> Olá, estou integrando minha conta via Smart Trader API para um painel de trading pessoal.  
> Preciso de: API Key, API Secret e confirmação do Account ID para ambiente de desenvolvimento.  
> A integração é somente para minha conta [número].

---

## Agent self-check script (1.0)

```powershell
python scripts/dev.py status --json
curl http://localhost:8000/api/v1/bootstrap
curl http://localhost:8000/api/v1/integrations/profit/test
curl http://localhost:8000/api/v1/integrations/clear/test
```

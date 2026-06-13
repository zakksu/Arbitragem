# Clear API — setup for Filipe

Paper mode is **on** until you add credentials. The dashboard works fully in mock mode (R$ 50k balance, sample positions).

## What you need from Clear

1. **Smart Trader API** access (Clear corretora — ask your account manager or Clear support if not enabled).
2. These values (from Clear’s developer portal or account settings):
   - API key
   - API secret
   - Account ID

## Steps

1. Copy `.env.example` → `.env` if you haven’t already.
2. Fill in:

```env
CLEAR_API_KEY=your-key-here
CLEAR_API_SECRET=your-secret-here
CLEAR_ACCOUNT_ID=your-account-id
PAPER_TRADING_MODE=false
```

3. Restart the stack:

```powershell
python scripts/dev.py restart --wait
```

4. In the dashboard: **Settings → Test Clear connection** — should show `configured: true`, `mock_mode: false`.

## What changes when Clear is live

| Feature | Paper (now) | Live (with keys) |
|---------|-------------|------------------|
| Sidebar Clear dot | Yellow | Green |
| Balance / P&L | Mock R$ 50k | Real account |
| Positions | Sample BOVA option | Your book |
| Journal sync | Clear trades imported | Real fills |
| Order routing | Not sent | Via Smart Trader API |

## If you don’t have API access yet

Keep `PAPER_TRADING_MODE=true` (default). Use Profit bridge for quotes and journal sync from Profit fills. Clear is only required for **live execution** and **real balances**.

## Security

- Never commit `.env` (already in `.gitignore`).
- Use read-only API keys for testing if Clear offers them.

# Cloudflare Tunnel (Windows PC → public HTTPS)

Expose Arbitragem from your Windows machine without opening router ports. Traffic flows through Cloudflare to `cloudflared` on your PC, which forwards to local API (`:8000`) and Streamlit (`:8501`).

**Default hostnames** (dmconsultoria.seg.br):

| URL | Local service |
|-----|----------------|
| `https://trading.dmconsultoria.seg.br` | API + `/board` blackboard (`localhost:8000`) |
| `https://dashboard.dmconsultoria.seg.br` | Streamlit dashboard (`localhost:8501`) |

Override hostnames in `.env` via `CLOUDFLARE_TUNNEL_HOSTNAME` and `CLOUDFLARE_DASHBOARD_HOSTNAME`.

## 1. Install cloudflared (Windows)

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/dev.py tunnel install
```

This downloads `tools/cloudflared.exe` (no admin; works when `winget` is missing).

Alternatively:

```powershell
winget install --id Cloudflare.cloudflared
```

Or download from [Cloudflare docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/). Open a **new** terminal after a global install.

Verify:

```powershell
python scripts/dev.py tunnel status
```

## 2. Cloudflare account + domain

1. Add `dmconsultoria.seg.br` to [Cloudflare](https://dash.cloudflare.com) (free plan is fine).
2. **Option A — Full DNS (recommended):** At GoDaddy, change nameservers to the two Cloudflare NS records. Cloudflare manages all DNS.
3. **Option B — Partial DNS at GoDaddy:** Keep GoDaddy NS; add CNAME records only for subdomains (see step 4).

For a quick smoke test without DNS, Cloudflare offers a temporary quick tunnel — not for production; use named tunnel below.

## 3. One-time tunnel setup

```powershell
cd C:\Users\godin\Desktop\Arbitragem
python scripts/dev.py tunnel setup --run
```

This runs (when `--run`):

- `cloudflared tunnel login` — browser auth
- `cloudflared tunnel create arbitragem`
- Writes `config/cloudflared/config.yml` from `docker/cloudflared/config.yml.example`
- Suggests DNS routes

Without `--run`, the same steps are printed for manual copy/paste.

## 4. DNS records

**If nameservers are on Cloudflare:**

```powershell
cloudflared tunnel route dns arbitragem trading.dmconsultoria.seg.br
cloudflared tunnel route dns arbitragem dashboard.dmconsultoria.seg.br
```

**If DNS stays at GoDaddy:** Create CNAME records:

| Name | Target |
|------|--------|
| `trading` | `<TUNNEL_UUID>.cfargotunnel.com` |
| `dashboard` | `<TUNNEL_UUID>.cfargotunnel.com` |

Find `<TUNNEL_UUID>` in `%USERPROFILE%\.cloudflared\*.json` or `cloudflared tunnel list`.

## 5. Enable passwords (required)

Before sharing URLs, merge [.env.tunnel.example](../.env.tunnel.example) into `.env`:

```env
BOARD_AUTH_ENABLED=true
DASHBOARD_AUTH_ENABLED=true
BOARD_PASSWORD=your-strong-password
DASHBOARD_PASSWORD=your-strong-password
```

Restart the stack after changing `.env`.

## 6. Run

```powershell
python scripts/dev.py start --wait
python scripts/dev.py tunnel start
```

- Blackboard: `https://trading.dmconsultoria.seg.br/board`
- Dashboard: `https://dashboard.dmconsultoria.seg.br`
- Stop tunnel: `python scripts/dev.py tunnel stop`
- Status: `python scripts/dev.py tunnel status`

Logs: `logs/cloudflared.log`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `cloudflared not found` | Install via winget; new terminal |
| `config missing` | `python scripts/dev.py tunnel setup` |
| 502 / connection refused | Run `python scripts/dev.py start --wait` first |
| DNS not resolving | Run `python scripts/dev.py tunnel dns-fix`. Common mistakes: hostname `tracing` instead of `trading`; CNAME target `*.cloud.com` instead of `<TUNNEL_UUID>.cfargotunnel.com`. Or switch GoDaddy NS to Cloudflare (routes already configured). |
| Login page missing | Set `BOARD_AUTH_ENABLED` / `DASHBOARD_AUTH_ENABLED` in `.env` and restart |
| `UnicodeEncodeError` on setup (Windows) | Fixed in `scripts/tunnel.py` — re-run `tunnel setup` if setup crashed after DNS step |

## Security notes

- Never commit `.env` or tunnel credential JSON files.
- Keep `PAPER_TRADING_MODE=true` until you intentionally go live.
- Tunnel exposes your PC — use strong passwords and stop the tunnel when not needed.

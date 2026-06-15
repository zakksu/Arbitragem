# Arbitragem Dashboard

Self-hosted web dashboard for **B3 IBOV scalping** (Filipe Core14 + BOVA options), built around your existing stack:

- **ProfitChart / NTSL** — data, tape, Tick-a-Tick backtests, execution export
- **Clear Corretora Smart Trader API** — execution & account sync
- **Ollama** — symbol reports, journal analysis, NTSL optimization
- **Python** — autonomous scans, trade ideas, backtest gates, performance tracking

**Primary UI (3.0-alpha):** http://localhost:8000/board — Structure Deck (options chain · max pain · multi-leg ideas)

**Legacy UI:** http://localhost:8501 — Streamlit (maintenance / admin)

---

## What's new in 3.0-alpha (Structure Deck)

- **Version** `3.0.0-alpha` — multi-leg `structure_type` + `legs[]` on trade ideas
- **Options chain panel** — calls/puts table on symbol panel (Profit stub or bridge)
- **Max pain signal** — scanner tags + `GET /api/v1/signals/max-pain/{underlying}`
- **Structure types API** — `GET /api/v1/structures/types`
- **Unified chain** — `GET /api/v1/options/chain/{underlying}`
- **Multi-leg NTSL** — confirm exports per-leg NTSL when `legs.length > 1`
- **Lightweight Charts** — mini session chart with max-pain price line
- **Walk-forward** — `POST /api/v1/walk-forward/run`

Quick start:

```powershell
.\.venv\Scripts\python.exe scripts/dev.py start --wait --open
# Structure Deck → http://localhost:8000/board
```

---

## What's new in 2.0.0

- **HTMX Blackboard** — ProfitChart-like workspace at `/board`
- **Filipe Core14** — 14 liquid IBOV names + BOVA index options (`SCANNER_MODE=filipe_core14`)
- **Idea Stack** — scanner → ranked ideas → 2-step review → **Confirm → NTSL** export
- **Backtest gate** — ideas need PF ≥ 1.3 and max DD ≤ 8% (Profit bridge)
- **Board notes** — per-symbol notes + AI report (Ollama)
- **Setup wizard** — `/api/v1/setup/status` + board Setup drawer
- **Kill switch** — `POST /api/v1/strategies/pause-all` from status bar
- **SSE quotes** — `GET /api/v1/stream/quotes` for live watchlist refresh

Quick start:

```powershell
python scripts/dev.py restart --wait --open
# Blackboard → http://localhost:8000/board
```

---

## What's in 1.0.0

- **IBOV Top 20 scanner** — PETR4, VALE3, ITUB4, … BOVA11 by 30d avg volume
- **Scalp engine** — reliability score, long/short bias, stop/target ticks
- **`GET /scanner/insights`** — top 5 picks for the dashboard
- **Profit bridge** — auto-starts with `python scripts/dev.py start --wait`
- **Home + Scanner UI** — scalp picks, ranked table, universe tab
- **26 automated tests** (full suite ~15s)

---

| Approach | When to use | Why |
|----------|-------------|-----|
| **ProfitChart Tick-a-Tick** (primary) | Validating NTSL strategies before live | Mature B3 microstructure, realistic fills, zero rebuild |
| **Python supplement** (this repo) | Grid search, genetic algo, walk-forward, portfolio stats | Fast iteration across parameters; ML-friendly |
| **Full custom Python backtester** | Only if you leave NTSL entirely | High effort; hard to match Profit's B3 accuracy |

**Verdict: Hybrid.** Keep Profit as source of truth for NTSL execution realism. Use Python here for optimization, comparison, and ML — not as a replacement on day one.

Workflow:

1. Prototype NTSL in Profit Editor → Tick-a-Tick backtest → export CSV
2. Import CSV metrics into dashboard (`engine=profit`)
3. Run Python grid/GA on same parameters (`engine=python`)
4. If metrics diverge wildly, align data feeds before trusting Python results
5. One-click export optimized NTSL back to Profit for final validation

---

## Architecture

```
FastAPI (API + scheduler + HTMX blackboard)
    ├── Integrations: Profit bridge, Clear API, Ollama
    ├── Services: scanner, trade ideas, journal, backtest, optimizer, risk
    └── SQLite (default) or PostgreSQL

HTMX Blackboard (/board) ──same host──► FastAPI
Streamlit (legacy UI) ──HTTP──► FastAPI

Docker Compose on VPS (24/7)
Windows PC: ProfitChart + ProfitDLL bridge (port 9100)
```

**Why FastAPI + Streamlit (not Streamlit-only)?**

- FastAPI runs 24/7 with APScheduler (daily scans, journal sync) independent of browser
- Clean REST API for future mobile alerts, webhooks, Clear callbacks
- Streamlit = fast MVP UI for a beginner — swap to React later if needed

---

## Folder structure

```
Arbitragem/
├── src/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings from .env
│   ├── models.py            # SQLAlchemy models
│   ├── scheduler.py         # Cron jobs
│   ├── api/                 # REST routes
│   ├── integrations/        # Profit, Clear, Ollama clients
│   └── services/            # Business logic
├── dashboard/
│   ├── app.py               # Streamlit router
│   ├── utils.py             # API helpers
│   ├── scanner_ui.py        # Pattern scanner (Plotly)
│   ├── components/          # theme, charts, alerts, sidebar
│   └── views/               # home, monitor, performance, journal, etc.
├── scripts/
│   ├── start.ps1 / start.sh # One-command local launch
│   ├── profit_bridge_stub.py
│   ├── run_optimization.py
│   └── run_scanner.py
├── docker/
│   └── Caddyfile            # Optional HTTPS reverse proxy
├── tests/
├── docs/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quick start (one command — beginner friendly)

The **dev orchestrator** does everything automatically: `.env`, venv, pip install, database, start API + dashboard, health checks.

```bash
cd Arbitragem
python scripts/dev.py start --wait --open
```

**Windows shortcut:**
```powershell
.\scripts\start.ps1
```

**What it does for you:**
1. Creates `.env` from `.env.example` if missing
2. Creates `.venv` and installs `requirements.txt`
3. Initializes SQLite database
4. Starts API (`:8000`) and dashboard (`:8501`) in the background
5. Waits until both are healthy, then opens your browser

**Other commands:**

| Command | Purpose |
|---------|---------|
| `python scripts/dev.py status` | Is it running? |
| `python scripts/dev.py stop` | Stop everything |
| `python scripts/dev.py restart --wait` | After code changes |
| `python scripts/dev.py setup` | Fix broken venv/deps |

Logs: `logs/api.log` and `logs/dashboard.log`

**Cursor browser preview:** run `start --wait` first, then refresh `http://localhost:8501` in the right panel.

---

### Manual setup (only if dev.py fails)

<details>
<summary>Advanced: two terminals</summary>

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
# second terminal:
streamlit run dashboard/app.py
```

</details>

### 4. Ollama (optional but recommended)

```bash
# Install from https://ollama.com
ollama pull llama3.2
ollama serve
```

Or use Docker profile: `docker compose --profile ollama up -d ollama`

### 5. Run tests

```bash
pytest -v
```

---

## Docker (VPS deploy)

```bash
cp .env.example .env
# Set APP_SECRET_KEY, timezone America/Sao_Paulo

docker compose up -d --build
```

Services:

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | `http://YOUR_VPS:8000/docs` |
| Dashboard | 8501 | `http://YOUR_VPS:8501` |
| Ollama (optional) | 11434 | `docker compose --profile ollama up -d` |

### VPS checklist

1. Ubuntu 22.04+ VPS (Hetzner, DigitalOcean, etc.)
2. Point subdomain `trading.yourdomain.com` → VPS IP (Cloudflare proxy optional)
3. Reverse proxy with Caddy or Nginx + HTTPS (Let's Encrypt)
4. `ufw allow 80,443` — do **not** expose 8000/8501 publicly; proxy through 443
5. Set `OLLAMA_BASE_URL=http://ollama:11434` if using compose Ollama profile

### Connect ProfitChart (Windows PC)

See [docs/profit_bridge.md](docs/profit_bridge.md).

### Connect Clear API

1. Get Smart Trader API credentials from Clear
2. Set in `.env`:
   ```
   CLEAR_API_KEY=...
   CLEAR_API_SECRET=...
   CLEAR_ACCOUNT_ID=...
   ```
3. Without credentials, dashboard runs in **mock mode** (safe for development)

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite default; use PostgreSQL on VPS |
| `OLLAMA_BASE_URL` | Ollama server |
| `OLLAMA_MODEL` | e.g. `llama3.2` or your fine-tuned model |
| `CLEAR_API_*` | Clear Smart Trader credentials |
| `PROFIT_BRIDGE_*` | Windows bridge for ProfitDLL |
| `SCANNER_CRON_HOUR` | Daily scan time (BRT) |
| `DEFAULT_DAILY_LOSS_LIMIT_BRL` | Global risk default |
| `ALERTS_ENABLED` | Telegram/Discord on scanner warnings |
| `DASHBOARD_AUTH_ENABLED` | Login gate for public VPS |

Full list in [.env.example](.env.example).

---

## Dashboard pages

| Page | Purpose | Status |
|------|---------|--------|
| **Home** | Account summary, scanner alerts, quick actions, auto-refresh | ✅ MVP |
| **Live Monitor** | Start/stop strategies, risk limits, NTSL export | ✅ MVP |
| **Performance** | Cumulative & daily P&L, win/loss charts | ✅ MVP |
| **Daily Scanner** | Volume/spike heatmaps, pattern tags, Ollama insights | ✅ MVP |
| **Strategies** | NTSL management, export to Profit | ✅ MVP |
| **Backtest & Optimize** | Profit vs Python compare, grid/GA/walk-forward | ✅ MVP |
| **Journal** | Auto-sync Clear trades, filters, CSV export, AI notes | ✅ MVP |
| **Ollama Insights** | Chat with history, quick prompts, scanner context | ✅ MVP |

**UI views live in `dashboard/views/`** (not `pages/` — avoids Streamlit multipage blank screen).

---

## Current MVP status (production-ready)

| Area | Status | Notes |
|------|--------|-------|
| FastAPI + SQLite + scheduler | ✅ | Daily scan + journal sync + alerts |
| Streamlit UI (8 pages) | ✅ | `dashboard/pages/` + scanner charts |
| Profit CSV parser | ✅ | Upload + parse in backtest flow |
| Walk-forward optimizer | ✅ | API + UI (`method=walk_forward`) |
| Pattern scanner | ✅ | Volume, OI proxy, IV skew, price Δ |
| Telegram / Discord alerts | ✅ | `ALERTS_ENABLED=true` in `.env` |
| Dashboard auth | ✅ | `DASHBOARD_AUTH_ENABLED=true` on VPS |
| Strategy PATCH + pause | ✅ | Edit NTSL, risk, pause without full stop |
| Risk pre-check on start | ✅ | Daily loss limit before activation |
| Docker Compose | ✅ | API, dashboard, Caddy/Ollama/Postgres profiles |
| ProfitDLL bridge | 🔶 | HTTP stub — real DLL on Windows PC |
| Clear API | 🔶 | Mock until credentials configured |
| Fine-tuned Ollama | ⏳ | Optional Modelfile when ready |

---

## Autonomous scripts

```bash
# Daily scan (also runs on scheduler)
python scripts/run_scanner.py

# Overnight optimization
python scripts/run_optimization.py --strategy-id 1 --method grid

# Profit bridge (Windows only)
python scripts/profit_bridge_stub.py
```

---

## GitHub setup

```bash
git init
git add .
git commit -m "Initial MVP: Arbitragem dashboard"
gh repo create Arbitragem --public --source=. --push
```

Or create repo on github.com → add remote → push.

---

## Development status

| Area | Status |
|------|--------|
| FastAPI core + scheduler + alerts | ✅ Done |
| Profit CSV parser + upload | ✅ Done |
| Walk-forward optimizer | ✅ Done |
| Scanner (volume, OI, skew, price Δ) | ✅ Done |
| Streamlit UI + auth + alerts panel | ✅ Done |
| Telegram/Discord webhooks | ✅ Done |
| Docker + Caddy proxy profile | ✅ Done |
| Real ProfitDLL ctypes bridge | 🔶 Pending |
| Clear API live endpoints | 🔶 Pending |
| Fine-tuned Ollama model | ⏳ Optional |

---

## Safety & risk

- **Paper trade first** — use Profit simulation + Clear demo if available
- Daily loss limits enforced in `RiskManager` before strategy start
- Never commit `.env` or API keys
- Mock mode is default when Clear credentials are missing
- This is tooling, not financial advice

---

## Optional enhancements

1. **Real ProfitDLL bridge** — ctypes callbacks on Windows PC
2. **Clear API** — wire exact Smart Trader endpoints from Clear docs
3. **Fine-tuned Ollama** — Modelfile with journal + NTSL corpus
4. **Real B3 options chain** — replace IV skew proxy with live OI/IV data

---

## License

MIT — use at your own risk. Trading involves substantial risk of loss.

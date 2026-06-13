# Performance & architecture options

## What was slow (root cause)

1. **`GET /health` on every load** — probes Ollama (up to 5s) + Profit bridge (up to 5s) sequentially.
2. **Streamlit reruns the full script** on every click — duplicate API calls before caching warmed up.
3. **Pandas `style.apply` on watchlist** — very slow to render in Streamlit.
4. **Scanner with Ollama on each symbol** — a full scan could take 10+ minutes.

## What we did (v1.0.0 — stay on Streamlit)

| Fix | Effect |
|-----|--------|
| `GET /bootstrap` | One fast DB call for sidebar + home (no external probes) |
| `GET /integrations/status` | Only on "Refresh connectors" or Settings |
| Removed `/health` from hot path | First paint avoids 5–10s stall |
| Shorter probe timeouts (1.5s) | Faster when you do probe |
| `SCANNER_OLLAMA_ON_SCAN=false` | Scans finish in seconds, not minutes |
| Plain `st.dataframe` (no styling) | Faster watchlist render |

**Target:** first load &lt; 1s after API warm; navigation &lt; 300ms with cache.

## If Streamlit is still too slow

Streamlit is great for MVPs but **reruns the entire app** on interaction. For ProfitChart-like snappiness:

### Option A — HTMX + FastAPI templates (recommended next step)

- Keep existing FastAPI backend (`src/api/routes.py`)
- Add `src/web/` with Jinja + HTMX — partial page updates, no full rerun
- **Effort:** ~2–3 days for Home + Scanner + Monitor
- **Pros:** Fast, simple, same Python stack, easy VPS deploy
- **Cons:** Less fancy than React

### Option B — React / Vite SPA

- Full SPA consuming `/api/v1/*`
- **Effort:** ~1–2 weeks for feature parity
- **Pros:** Best UX, mobile, charts
- **Cons:** Two codebases to maintain

### Option C — API-only + ProfitChart as UI

- Dashboard becomes headless API + alerts (Telegram/Discord)
- Trade from ProfitPro; journal/scanner via API scripts
- **Pros:** Minimal UI work
- **Cons:** No custom web dashboard

### Recommendation for Filipe

1. **Ship 1.0.0 on Streamlit** with `/bootstrap` (now).
2. If still unhappy after testing → **Option A (HTMX)** for v1.1.
3. Keep Streamlit for internal/admin; public-facing could be HTMX.

## Verify speed

```powershell
python scripts/dev.py restart --wait
```

```powershell
# Should be < 100ms after warm
curl -w "%{time_total}s" http://localhost:8000/api/v1/bootstrap
```

In dashboard: sidebar shows ⚪ for AI/Profit until you click **Refresh connectors**.

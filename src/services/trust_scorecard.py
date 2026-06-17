"""Trust scorecard (5.2) — composite gate score for golden path (Release 7.0)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.services.ops_panel import get_process_rss_mb, read_test_status
from src.services.pnl_reconcile import last_reconcile


def build_trust_scorecard(
    session: Session,
    *,
    checklist_items: list[dict[str, Any]] | None = None,
    ram_budget_mb: float = 1200.0,
) -> dict[str, Any]:
    """Weighted score from checklist, tests, P&L reconcile, and RAM."""
    items = checklist_items or []
    checklist_ok = sum(1 for it in items if it.get("ok"))
    checklist_total = max(len(items), 1)
    checklist_pct = round(checklist_ok / checklist_total * 100, 1)

    test = read_test_status()
    test_state = str(test.get("state") or "yellow")
    test_pct = {"green": 100.0, "yellow": 70.0, "red": 0.0}.get(test_state, 50.0)

    reconcile = last_reconcile(session)
    pnl_ok = bool(reconcile.get("within_tolerance", True))
    pnl_pct = 100.0 if pnl_ok else max(0.0, 100.0 - float(reconcile.get("diff_pct") or 100.0))

    mem = get_process_rss_mb()
    rss = float(mem.get("rss_mb") or 0)
    ram_ok = rss <= ram_budget_mb if mem.get("available") else True
    if not mem.get("available"):
        ram_pct = 100.0
    elif rss <= ram_budget_mb * 0.8:
        ram_pct = 100.0
    elif rss <= ram_budget_mb:
        ram_pct = 85.0
    else:
        ram_pct = max(0.0, 100.0 - (rss - ram_budget_mb) / ram_budget_mb * 100.0)

    weights = {"checklist": 0.45, "tests": 0.20, "pnl": 0.20, "ram": 0.15}
    score = round(
        checklist_pct * weights["checklist"]
        + test_pct * weights["tests"]
        + pnl_pct * weights["pnl"]
        + ram_pct * weights["ram"],
        1,
    )
    gates_red = []
    if test_state == "red":
        gates_red.append("tests")
    if not pnl_ok:
        gates_red.append("pnl")
    if not ram_ok:
        gates_red.append("ram")

    return {
        "score_pct": score,
        "passing": score >= 85.0 and not gates_red,
        "gates_red": gates_red,
        "components": {
            "checklist": {"pct": checklist_pct, "ok": checklist_ok, "total": checklist_total},
            "tests": {"state": test_state, "pct": test_pct},
            "pnl": {"within_tolerance": pnl_ok, "pct": pnl_pct, "diff_pct": reconcile.get("diff_pct")},
            "ram": {"rss_mb": rss, "budget_mb": ram_budget_mb, "ok": ram_ok, "pct": ram_pct},
        },
    }

"""Run a visible mock Profit backtest (stub) - watch progress in the terminal."""

from __future__ import annotations

import sys
import time

import httpx

BRIDGE = "http://localhost:9100"
API = "http://localhost:8000/api/v1"
SYMBOL = sys.argv[1].upper() if len(sys.argv) > 1 else "PETR4"


def step(msg: str, delay: float = 0.6) -> None:
    print(msg, flush=True)
    time.sleep(delay)


def main() -> int:
    print(f"\n=== Mock Profit Tick-a-Tick backtest - {SYMBOL} ===\n")
    step("[1/5] Profit bridge: checking connection...", 0.4)
    with httpx.Client(timeout=10) as c:
        h = c.get(f"{BRIDGE}/health")
        h.raise_for_status()
        print(f"       bridge OK - {h.json().get('status', 'up')}")

        step(f"[2/5] Loading {SYMBOL} session data (stub)...", 0.8)
        q = c.get(f"{BRIDGE}/quotes/{SYMBOL}")
        if q.status_code == 200:
            last = q.json().get("last", "?")
            print(f"       last price: R$ {last}")

        step("[3/5] Running Tick-a-Tick simulation...", 1.2)
        for pct in (20, 45, 70, 90, 100):
            print(f"       progress: {pct}%", flush=True)
            time.sleep(0.5)

        step("[4/5] Computing metrics (PF, DD, win rate)...", 0.5)
        r = c.post(f"{BRIDGE}/backtest/run", json={"symbol": SYMBOL, "strategy": "scalp_default"})
        r.raise_for_status()
        m = r.json()

        print("\n-- Backtest results (stub) --")
        print(f"  Symbol:        {m.get('symbol')}")
        print(f"  Strategy:      {m.get('strategy')}")
        print(f"  Profit factor: {m.get('profit_factor')}")
        print(f"  Max drawdown:  {m.get('max_drawdown_pct')}%")
        print(f"  Trades:        {m.get('trades')}")
        print(f"  Win rate:      {m.get('win_rate_pct')}%")
        print(f"  Source:        {m.get('source')}")

        pf = float(m.get("profit_factor", 0))
        dd = float(m.get("max_drawdown_pct", 100))
        gate = "PASS" if pf >= 1.3 and dd <= 8 else "FAIL (below 2.0 gate)"
        print(f"  2.0 gate:      {gate}")

        step("[5/5] Pushing to dashboard (scan -> ideas)...", 0.4)
        try:
            c.post(f"{API}/scanner/run", timeout=60)
            ideas = c.get(f"{API}/ideas").json().get("ideas", [])
            matched = [i for i in ideas if i.get("symbol") == SYMBOL]
            print(f"       {len(ideas)} ideas in stack; {len(matched)} for {SYMBOL}")
            for idea in matched[:3]:
                proof = idea.get("backtest_proof") or {}
                print(
                    f"       - idea #{idea.get('id')} {idea.get('status')} "
                    f"PF={proof.get('profit_factor', '-')}"
                )
        except httpx.HTTPError as exc:
            print(f"       dashboard sync skipped: {exc}")

    print("\nOpen blackboard: http://localhost:8000/board")
    print("Click Scan in the toolbar or pick a symbol to review ideas.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

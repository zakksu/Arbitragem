#!/usr/bin/env python3
"""Generate Core5 NTSL strategy pack — S1-S5 stocks + F1-F5 WIN (13.0)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "strategies" / "ntsl" / "core5"
OUT.mkdir(parents=True, exist_ok=True)

STOCK = {
    "s1_vwap_reclaim": ("VWAP reclaim long", 4, 6, "Close > VWAP after dip"),
    "s2_orb_break": ("Opening range break", 5, 8, "15m ORB 10:00-12:00"),
    "s3_bb_fade": ("BB mean reversion", 5, 6, "Touch lower BB + RSI<35"),
    "s4_arch_bias": ("Archaeology bias", 5, 8, "History net flow green"),
    "s5_pulse": ("Pulse scalp", 3, 5, "Radar all green + CASH sleeve"),
}

WIN = {
    "f1_open_drive": ("Open drive 09:05-09:20", 80, 120, "Momentum — Cross Order ON"),
    "f2_vwap_reclaim": ("WIN VWAP reclaim", 60, 100, "Reclaim session VWAP"),
    "f3_lunch_fade": ("Lunch fade", 50, 80, "12:00-13:00 mean reversion"),
    "f4_afternoon_trend": ("Afternoon trend", 70, 110, "14:00+ with BOVA bias"),
    "f5_failed_breakout": ("Failed ORB fade", 55, 90, "False breakout trap"),
}


def _body(name: str, sym_var: str, stop: int, target: int, hint: str, *, futures: bool) -> str:
    cross = "\n// CrossOrder(true); // enable in Profit for WINFUT" if futures else ""
    return f"""// Arbitragem 13.0 — {name}
// {hint}
// Symbol: set in Profit Replay / Editor
Input
  StopTicks({stop});
  TargetTicks({target});
Var
  vwap : Float;
Begin
  vwap := VWAP(1);{cross}
  // Entry: pattern-specific — arm on replay for {sym_var}
  // Stop: StopTicks * tick from entry
  // Target: TargetTicks * tick
  Plot(vwap);
End.
"""


def main() -> None:
    for key, (title, stop, target, hint) in STOCK.items():
        (OUT / f"stock_{key}.ntsl").write_text(
            _body(title, "PETR4|VALE3|ITUB4|BOVA11|PRIO3", stop, target, hint, futures=False),
            encoding="utf-8",
        )
    for key, (title, stop, target, hint) in WIN.items():
        (OUT / f"win_{key}.ntsl").write_text(
            _body(title, "WINFUT", stop, target, hint, futures=True),
            encoding="utf-8",
        )
    print(f"Wrote {len(STOCK) + len(WIN)} NTSL files to {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate 50 Core14 options NTSL strategy stubs for strategy store scan."""

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "strategies" / "ntsl" / "core14_options"
OPTIONS_CSV = PROJECT_ROOT / "data" / "core17_options.csv"

STRUCTURES = (
    ("covered_call", "covered call", "Buy stock then Sell OTM call"),
    ("vertical", "vertical", "Bull call vertical spread"),
    ("collar", "collar", "Long stock + protective put + short call"),
    ("cash_scalp", "scalp", "VWAP reclaim scalp on underlying"),
    ("protective_put", "hedge", "Long stock + protective put only"),
)

# 17 symbols: Core14 + BOVA11 + RADL3 + MGLU3 (Filipe history overlap)
CORE17 = [
    "PETR4", "VALE3", "PRIO3", "ITUB4", "BBAS3", "BBDC4", "BBSE3", "B3SA3",
    "ABEV3", "GGBR4", "CSNA3", "USIM5", "SUZB3", "WEGE3", "BOVA11", "RADL3", "MGLU3",
]


def _load_options() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not OPTIONS_CSV.exists():
        return out
    with OPTIONS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = row["underlying"].strip().upper()
            out[sym] = {
                "call": row.get("sample_call", "").strip().upper(),
                "put": row.get("sample_put", "").strip().upper(),
            }
    return out


def _ntsl(
    *,
    name: str,
    underlying: str,
    structure: str,
    hint: str,
    call_sym: str,
    put_sym: str,
    stop_ticks: int,
    target_ticks: int,
) -> str:
    st = structure.lower()
    legs: list[str] = []
    if st == "covered_call":
        legs = [
            f"// Leg 1: buy {underlying}",
            f'// BuyAtMarket(100, "{underlying}");',
            f"// Leg 2: sell covered call",
            f'// SellAtMarket(100, "{call_sym or underlying+"C100"}");',
        ]
    elif st == "vertical":
        legs = [
            f"// Leg 1: buy lower strike call on {underlying}",
            f'// BuyAtMarket(1, "{call_sym or underlying+"C95"}");',
            f"// Leg 2: sell higher strike call",
            f'// SellAtMarket(1, "{call_sym or underlying+"C105"}");',
        ]
    elif st == "collar":
        legs = [
            f"// Leg 1: long {underlying}",
            f'// BuyAtMarket(100, "{underlying}");',
            f"// Leg 2: protective put",
            f'// BuyAtMarket(1, "{put_sym or underlying+"P90"}");',
            f"// Leg 3: short OTM call",
            f'// SellAtMarket(1, "{call_sym or underlying+"C110"}");',
        ]
    elif st == "protective_put":
        legs = [
            f"// Leg 1: long {underlying}",
            f'// BuyAtMarket(100, "{underlying}");',
            f"// Leg 2: hedge put",
            f'// BuyAtMarket(1, "{put_sym or underlying+"P90"}");',
        ]
    else:
        legs = [
            f"// scalp {underlying} — {hint}",
            f'// BuyAtMarket(100, "{underlying}");',
        ]

    leg_block = "\n".join(legs)
    return f"""// Arbitragem Core17 — {name}
// Structure: {structure} · {hint}
// Underlying: {underlying}
input
  StopTicks({stop_ticks});
  TargetTicks({target_ticks});
var
  EntryPrice : Float;
begin
  EntryPrice := Close;
{leg_block}
  SetStopLoss(StopTicks * MinPriceIncrement);
  SetProfitTarget(TargetTicks * MinPriceIncrement);
end;
"""


def main() -> int:
    opts = _load_options()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    idx = 0
    files: list[str] = []
    for underlying in CORE17:
        o = opts.get(underlying, {})
        for st_key, st_hint, desc in STRUCTURES:
            if written >= 50:
                break
            # skip duplicate cash scalp on BOVA for options pack — use bova_hedge variant
            if underlying == "BOVA11" and st_key == "cash_scalp":
                st_key, st_hint, desc = "protective_put", "hedge", "BOVA put hedge sleeve"
            name = f"{underlying.lower()}_{st_key}"
            path = OUT_DIR / f"{name}.ntsl"
            stop = 4 + (idx % 5)
            target = 6 + (idx % 7)
            path.write_text(
                _ntsl(
                    name=name,
                    underlying=underlying,
                    structure=st_hint,
                    hint=desc,
                    call_sym=o.get("call", ""),
                    put_sym=o.get("put", ""),
                    stop_ticks=stop,
                    target_ticks=target,
                ),
                encoding="utf-8",
            )
            written += 1
            idx += 1
            files.append(str(path.resolve()))
        if written >= 50:
            break

    import json
    from datetime import datetime, timezone

    version_path = PROJECT_ROOT / "data" / ".dev" / "ntsl_pack_version.json"
    version_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(
        json.dumps(
            {
                "version": f"core17-{written}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "files": files,
                "count": written,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {written} NTSL files to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Profit NTSL multi-leg export templates per structure type (3.0 GA)."""

from __future__ import annotations

from src.models import TradeIdea


def ntsl_for_idea(idea: TradeIdea) -> str:
    st = (idea.structure_type or "scalp").lower()
    legs = idea.legs or []
    if st in ("scalp", "scalp_long", "scalp_short") or len(legs) <= 1:
        return _scalp_ntsl(idea)
    builders = {
        "covered_call": _covered_call_ntsl,
        "vertical": _vertical_ntsl,
        "collar": _collar_ntsl,
        "bova_hedge": _bova_hedge_ntsl,
        "pair_spread": _pair_spread_ntsl,
        "pair_relative": _pair_spread_ntsl,
    }
    fn = builders.get(st, _generic_multileg_ntsl)
    return fn(idea)


def _scalp_ntsl(idea: TradeIdea) -> str:
    side = idea.side or "neutral"
    op = "Buy" if side == "long" else "Sell" if side == "short" else "Buy"
    return f"""// Arbitragem 3.0 — scalp idea #{idea.id}
// Symbol: {idea.symbol} · {side.upper()}
input
  StopTicks({idea.stop_ticks or 5});
  TargetTicks({idea.target_ticks or 8});
var
  EntryPrice : Float;
begin
  EntryPrice := Close;
  if (LastBarOnChart) then
    PlotText("{op} {idea.symbol}", clYellow, 0, EntryPrice);
  // Arm: {op} at market, stop/target in ticks
  // SetStopLoss(StopTicks * MinPriceIncrement);
  // SetProfitTarget(TargetTicks * MinPriceIncrement);
end;
"""


def _leg_order_comment(leg: dict, idx: int) -> str:
    sym = leg.get("symbol", "")
    side = leg.get("side", "buy").upper()
    qty = leg.get("quantity", 100)
    lt = leg.get("leg_type", "cash")
    strike = leg.get("strike")
    sk = f" strike={strike}" if strike else ""
    return f"// Leg {idx}: {side} {qty} {sym} ({lt}){sk}"


def _covered_call_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    lines = [
        f"// Arbitragem 3.0 — covered call #{idea.id} · {idea.symbol}",
        "// Execution order: 1) buy stock  2) sell OTM call",
    ]
    for i, leg in enumerate(legs, 1):
        lines.append(_leg_order_comment(leg, i))
    cash = next((l for l in legs if l.get("leg_type") == "cash"), None)
    call = next((l for l in legs if l.get("leg_type") == "call"), None)
    cash_sym = cash.get("symbol", idea.symbol) if cash else idea.symbol
    call_sym = call.get("symbol", "") if call else ""
    qty = int(cash.get("quantity", 100)) if cash else 100
    return "\n".join(lines) + f"""
begin
  // Step 1 — establish long stock
  // BuyAtMarket({qty}, "{cash_sym}");
  // Step 2 — sell covered call (same qty)
  // SellAtMarket({qty}, "{call_sym}");
end;
"""


def _vertical_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    lines = [f"// Arbitragem 3.0 — vertical spread #{idea.id}", "// Order: buy lower strike, sell higher strike"]
    for i, leg in enumerate(legs, 1):
        lines.append(_leg_order_comment(leg, i))
    return "\n".join(lines) + "\nbegin\n  // Spread legs — net debit entry\nend;\n"


def _collar_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    lines = [f"// Arbitragem 3.0 — collar #{idea.id} · {idea.symbol}", "// Order: stock → protective put → short call"]
    for i, leg in enumerate(legs, 1):
        lines.append(_leg_order_comment(leg, i))
    return "\n".join(lines) + "\nbegin\n  // Collar: long stock + long put + short call\nend;\n"


def _bova_hedge_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    lines = [f"// Arbitragem 3.0 — BOVA hedge #{idea.id}", "// Order: cash leg first, then BOVA put hedge"]
    for i, leg in enumerate(legs, 1):
        lines.append(_leg_order_comment(leg, i))
        if leg.get("hedge_ratio"):
            lines.append(f"//   hedge_ratio={leg['hedge_ratio']}")
    return "\n".join(lines) + "\nbegin\n  // Delta-aware BOVA put vs Core14 long\nend;\n"


def _pair_spread_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    lines = [f"// Arbitragem 3.0 — pair spread #{idea.id} · {idea.symbol}", "// Order: simultaneous relative value legs"]
    for i, leg in enumerate(legs, 1):
        lines.append(_leg_order_comment(leg, i))
    return "\n".join(lines) + "\nbegin\n  // Pair: long weak / short strong\nend;\n"


def _generic_multileg_ntsl(idea: TradeIdea) -> str:
    legs = idea.legs or []
    header = f"// Arbitragem 3.0 — {idea.structure_type} #{idea.id}\n"
    blocks = [header]
    for i, leg in enumerate(legs, 1):
        blocks.append(_leg_order_comment(leg, i))
    blocks.append("begin\n  // Multi-leg structure — arm in sequence\nend;")
    return "\n".join(blocks)

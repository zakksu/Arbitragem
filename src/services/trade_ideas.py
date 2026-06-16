"""Trade idea engine — scanner v2 output for Idea Stack."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.integrations.profit_bridge import get_profit_client
from src.logging_config import get_logger
from src.models import ScanResult, TradeIdea
from src.services.filipe_universe import sector_for

logger = get_logger(__name__)


class TradeIdeaService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.profit = get_profit_client()

    def list_ideas(self, limit: int = 20, status: str | None = None) -> list[TradeIdea]:
        q = self.session.query(TradeIdea).order_by(
            desc(TradeIdea.reliability), desc(TradeIdea.created_at)
        )
        if status:
            q = q.filter(TradeIdea.status == status)
        return q.limit(limit).all()

    def generate_from_latest_scan(
        self, limit: int = 10, structure_type: str | None = None
    ) -> list[TradeIdea]:
        latest = (
            self.session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
        )
        if not latest:
            return []

        scans = (
            self.session.query(ScanResult)
            .filter(ScanResult.scan_date == latest[0])
            .order_by(desc(ScanResult.spike_score))
            .all()
        )
        created: list[TradeIdea] = []
        for scan in scans:
            raw = scan.raw_data or {}
            if raw.get("signal_type") == "sector_pair":
                idea = self._idea_from_pair_scan(scan)
                if idea:
                    self.session.add(idea)
                    created.append(idea)
                if len(created) >= limit:
                    break
                continue

            reliability = float(raw.get("reliability", 0) or 0)
            if reliability < 20 and not scan.pattern_tags:
                continue
            if len(created) >= limit:
                break

            side = str(raw.get("side_bias", "neutral")).lower()
            structure = self._infer_structure(scan, side, structure_type)
            quote = self.profit.get_quote(scan.symbol)
            last = quote.last if quote else raw.get("last")
            stop_t = int(raw.get("stop_ticks", 5))
            target_t = int(raw.get("target_ticks", 8))
            tick = 0.01 if last and last < 50 else 0.05
            entry = float(last) if last else None
            stop_p = round(entry - stop_t * tick, 4) if entry and side == "long" else (
                round(entry + stop_t * tick, 4) if entry and side == "short" else None
            )
            target_p = round(entry + target_t * tick, 4) if entry and side == "long" else (
                round(entry - target_t * tick, 4) if entry and side == "short" else None
            )

            tags = list(scan.pattern_tags or [])
            sector = sector_for(scan.symbol)
            if sector:
                tags.append(f"sector:{sector.lower()}")
            tags.extend(self._iv_rank_tags(scan.symbol))

            legs = self._legs_for_structure(structure, scan.symbol, side, quote)

            idea = TradeIdea(
                symbol=scan.symbol,
                structure_type=structure,
                side=side,
                status="detected",
                reliability=reliability,
                entry_price=entry,
                stop_price=stop_p,
                target_price=target_p,
                stop_ticks=stop_t,
                target_ticks=target_t,
                title=self._title_for_structure(structure, scan.symbol, side),
                rationale_tags=tags,
                legs=legs,
                scan_result_id=scan.id,
            )
            self.session.add(idea)
            created.append(idea)

            metrics = self.profit.run_backtest(scan.symbol)
            if self.passes_backtest_gate(metrics):
                idea.backtest_proof = metrics
                idea.status = "backtested"
                idea.rationale_tags = list(idea.rationale_tags or []) + ["backtest_pass"]

        self.session.commit()
        logger.info("trade_ideas_generated", count=len(created))
        return created

    def create_from_structure(
        self,
        symbol: str,
        structure_type: str,
        side: str = "long",
    ) -> TradeIdea:
        sym = symbol.upper()
        structure = structure_type.lower()
        quote = self.profit.get_quote(sym)
        last = quote.last if quote else None
        stop_t, target_t = 5, 8
        tick = 0.01 if last and last < 50 else 0.05
        entry = float(last) if last else None
        side_l = side.lower()
        stop_p = round(entry - stop_t * tick, 4) if entry and side_l == "long" else (
            round(entry + stop_t * tick, 4) if entry and side_l == "short" else None
        )
        target_p = round(entry + target_t * tick, 4) if entry and side_l == "long" else (
            round(entry - target_t * tick, 4) if entry and side_l == "short" else None
        )
        legs = self._legs_for_structure(structure, sym, side_l, quote)
        tags = [f"structure:{structure}", "builder"] + self._iv_rank_tags(sym)

        idea = TradeIdea(
            symbol=sym,
            structure_type=structure,
            side=side_l,
            status="detected",
            reliability=55.0,
            entry_price=entry,
            stop_price=stop_p,
            target_price=target_p,
            stop_ticks=stop_t,
            target_ticks=target_t,
            title=self._title_for_structure(structure, sym, side_l),
            rationale_tags=tags,
            legs=legs,
        )
        self.session.add(idea)
        self.session.flush()

        metrics = self.profit.run_backtest(sym, strategy=structure)
        if self.passes_backtest_gate(metrics):
            idea.backtest_proof = metrics
            idea.status = "backtested"
            idea.rationale_tags = list(idea.rationale_tags or []) + ["backtest_pass"]

        self.session.commit()
        self.session.refresh(idea)
        logger.info("structure_idea_created", symbol=sym, structure=structure)
        return idea

    def _iv_rank_tags(self, symbol: str) -> list[str]:
        try:
            iv = self.profit.get_iv_rank(symbol)
            rank = float(iv.get("iv_rank", 50))
            tags: list[str] = []
            if rank >= 70:
                tags.extend(["iv_rank_high", "covered_call_bias"])
            elif rank <= 25:
                tags.extend(["iv_rank_low", "protective_put_bias"])
            return tags
        except Exception:
            return []

    def attach_backtest_proof(self, symbol: str, metrics: dict) -> TradeIdea | None:
        """Promote detected idea or create one when CSV export passes gate (A2.4b)."""
        if not self.passes_backtest_gate(metrics):
            return None

        sym = symbol.upper()
        idea = (
            self.session.query(TradeIdea)
            .filter(
                TradeIdea.symbol == sym,
                TradeIdea.status.in_(["detected", "backtested"]),
            )
            .order_by(desc(TradeIdea.reliability), desc(TradeIdea.created_at))
            .first()
        )
        if not idea and "/" in sym:
            long_sym = sym.split("/")[0]
            idea = (
                self.session.query(TradeIdea)
                .filter(
                    TradeIdea.symbol.like(f"{long_sym}/%"),
                    TradeIdea.status.in_(["detected", "backtested"]),
                )
                .order_by(desc(TradeIdea.reliability))
                .first()
            )

        if idea:
            idea.backtest_proof = metrics
            idea.status = "backtested"
            tags = list(idea.rationale_tags or [])
            if "backtest_pass" not in tags:
                tags.append("backtest_pass")
            idea.rationale_tags = tags
            return idea

        pf = float(metrics.get("profit_factor") or 0)
        idea = TradeIdea(
            symbol=sym,
            structure_type="scalp",
            side="neutral",
            status="backtested",
            reliability=min(100.0, pf * 30.0),
            title=f"{sym} backtest promotion",
            rationale_tags=["backtest_pass", "csv_import"],
            backtest_proof=metrics,
        )
        self.session.add(idea)
        return idea

    def _idea_from_pair_scan(self, scan: ScanResult) -> TradeIdea | None:
        raw = scan.raw_data or {}
        long_sym = raw.get("pair_long")
        short_sym = raw.get("pair_short")
        if not long_sym or not short_sym:
            return None

        reliability = float(raw.get("reliability", 0) or 0)
        basket = raw.get("basket", "sector")
        long_q = self.profit.get_quote(long_sym)
        short_q = self.profit.get_quote(short_sym)
        tags = list(scan.pattern_tags or [])

        return TradeIdea(
            symbol=f"{long_sym}/{short_sym}",
            structure_type="pair_relative",
            side="long",
            status="detected",
            reliability=reliability,
            entry_price=long_q.last if long_q else None,
            title=f"Long {long_sym} / Short {short_sym}",
            rationale_tags=tags + [f"sector:{basket}"],
            legs=[
                {"symbol": long_sym, "side": "buy", "quantity": 100},
                {"symbol": short_sym, "side": "sell", "quantity": 100},
            ],
            scan_result_id=scan.id,
        )

    def confirm_idea(self, idea_id: int, paper_override: bool = False) -> TradeIdea:
        """Lifecycle: detected/backtested → confirmed (A2.10). Execution is separate."""
        from src.config import get_settings
        from src.services.kill_switch import ensure_not_blocked
        from src.services.risk_cockpit import confirm_blocked_by_portfolio

        ensure_not_blocked("confirm")

        idea = self.session.get(TradeIdea, idea_id)
        if not idea:
            raise ValueError("Idea not found")
        if idea.status in ("executed", "rejected", "confirmed"):
            raise ValueError(f"Idea already {idea.status}")
        if idea.status not in ("detected", "backtested"):
            raise ValueError(f"Cannot confirm idea in status '{idea.status}'")

        if not paper_override and not self.passes_backtest_gate(idea.backtest_proof):
            settings = get_settings()
            raise ValueError(
                f"Backtest gate failed — need PF >= {settings.backtest_min_profit_factor} "
                f"and max DD <= {settings.backtest_max_drawdown_pct}% "
                "(or pass paper_override=true)"
            )

        if idea.backtest_proof and self.passes_backtest_gate(idea.backtest_proof):
            idea.status = "backtested"

        block_msg = confirm_blocked_by_portfolio(self.session, idea.legs)
        if block_msg:
            raise ValueError(block_msg)

        settings = get_settings()
        idea.status = "confirmed"
        idea.confirmed_at = datetime.utcnow()

        if settings.execution_backend == "ntsl":
            from src.services.ntsl_templates import ntsl_for_idea

            ntsl_code = ntsl_for_idea(idea)
            ntsl_path = get_profit_client().export_ntsl_strategy(
                f"idea_{idea.id}_{idea.symbol}", ntsl_code
            )
            idea.rationale = (
                (idea.rationale or "")
                + f"\n[NTSL] Exported to {ntsl_path} — import in Profit Editor and arm strategy."
            )

        self.session.commit()
        self.session.refresh(idea)
        from src.services.system_audit import log_event

        log_event(
            self.session,
            level="info",
            component="trade_ideas",
            message=f"Idea #{idea.id} confirmed",
            details={
                "symbol": idea.symbol,
                "structure_type": idea.structure_type,
                "legs": len(idea.legs or []),
                "paper_override": paper_override,
            },
        )
        self.session.commit()
        return idea

    def execute_idea(self, idea_id: int) -> TradeIdea:
        """Lifecycle: confirmed → executed with paper slippage (A2.6a)."""
        from src.config import get_settings
        from src.services.kill_switch import ensure_not_blocked

        ensure_not_blocked("execute")

        idea = self.session.get(TradeIdea, idea_id)
        if not idea:
            raise ValueError("Idea not found")
        if idea.status != "confirmed":
            raise ValueError(f"Idea must be confirmed before execute (status={idea.status})")

        settings = get_settings()
        if settings.paper_trading_mode:
            self._log_paper_trades(idea)
            idea.rationale = (
                (idea.rationale or "")
                + "\n[Paper] Filled with spread + 1 tick slippage per leg."
            )
        elif settings.execution_backend == "clear":
            self._execute_clear_legs(idea)
        else:
            self._log_paper_trades(idea)
            idea.rationale = (idea.rationale or "") + "\n[Paper] Filled (NTSL arm in Profit for live)."

        idea.status = "executed"
        idea.executed_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(idea)
        from src.services.system_audit import log_event

        log_event(
            self.session,
            level="info",
            component="trade_ideas",
            message=f"Idea #{idea.id} executed",
            details={"symbol": idea.symbol, "paper": settings.paper_trading_mode},
        )
        self.session.commit()
        return idea

    @staticmethod
    def passes_backtest_gate(metrics: dict | None) -> bool:
        if not metrics:
            return False
        from src.config import get_settings

        s = get_settings()
        pf = float(metrics.get("profit_factor") or metrics.get("profitFactor") or 0)
        if pf < s.backtest_min_profit_factor:
            return False
        dd_raw = metrics.get("max_drawdown_pct") or metrics.get("max_drawdown") or metrics.get("maxDrawdown")
        if dd_raw is None:
            return True
        dd = float(dd_raw)
        if dd <= 1.0:
            dd *= 100.0
        if dd > s.backtest_max_drawdown_pct:
            return False
        return True

    @staticmethod
    def _infer_structure(
        scan: ScanResult, side: str, requested: str | None = None
    ) -> str:
        if requested:
            return requested
        tags = scan.pattern_tags or []
        if "near_max_pain" in tags or "max_pain" in tags:
            if side == "long":
                return "covered_call"
        if side in ("long", "short"):
            return f"scalp_{side}"
        return "scalp"

    @staticmethod
    def _title_for_structure(structure: str, symbol: str, side: str) -> str:
        labels = {
            "covered_call": f"{symbol} covered call",
            "vertical": f"{symbol} vertical spread",
            "collar": f"{symbol} collar",
            "bova_hedge": f"{symbol} + BOVA hedge",
            "pair_spread": f"{symbol} pair spread",
        }
        if structure in labels:
            return labels[structure]
        return f"{symbol} {side.upper()} scalp"

    def _legs_for_structure(
        self, structure: str, symbol: str, side: str, quote
    ) -> list[dict]:
        sym = symbol.upper()
        cash_side = "buy" if side == "long" else "sell" if side == "short" else "flat"
        if structure in ("scalp", "scalp_long", "scalp_short"):
            return [
                {
                    "symbol": sym,
                    "side": cash_side,
                    "quantity": 100,
                    "leg_type": "cash",
                }
            ]
        chain = self.profit.get_option_chain(sym)
        calls = chain.get("calls") or []
        puts = chain.get("puts") or []
        otm_call = calls[-1] if calls else None
        otm_put = puts[0] if puts else None
        if structure == "covered_call" and otm_call:
            return [
                {"symbol": sym, "side": "buy", "quantity": 100, "leg_type": "cash"},
                {
                    "symbol": otm_call["symbol"],
                    "side": "sell",
                    "quantity": 100,
                    "leg_type": "call",
                    "strike": otm_call.get("strike"),
                },
            ]
        if structure == "vertical" and len(calls) >= 2:
            return [
                {
                    "symbol": calls[0]["symbol"],
                    "side": "buy",
                    "quantity": 100,
                    "leg_type": "call",
                    "strike": calls[0].get("strike"),
                },
                {
                    "symbol": calls[1]["symbol"],
                    "side": "sell",
                    "quantity": 100,
                    "leg_type": "call",
                    "strike": calls[1].get("strike"),
                },
            ]
        if structure == "collar" and otm_call and otm_put:
            return [
                {"symbol": sym, "side": "buy", "quantity": 100, "leg_type": "cash"},
                {
                    "symbol": otm_put["symbol"],
                    "side": "buy",
                    "quantity": 100,
                    "leg_type": "put",
                    "strike": otm_put.get("strike"),
                },
                {
                    "symbol": otm_call["symbol"],
                    "side": "sell",
                    "quantity": 100,
                    "leg_type": "call",
                    "strike": otm_call.get("strike"),
                },
            ]
        if structure == "bova_hedge":
            from src.services.bova_hedge import suggest_bova_hedge

            hedge = suggest_bova_hedge(sym, 100)
            bova = self.profit.get_option_chain("BOVA11")
            b_puts = bova.get("puts") or []
            b_put = b_puts[len(b_puts) // 2] if b_puts else None
            legs = [
                {"symbol": sym, "side": cash_side, "quantity": 100, "leg_type": "cash"},
            ]
            if b_put:
                legs.append(
                    {
                        "symbol": b_put["symbol"],
                        "side": "buy",
                        "quantity": hedge["bova_put_qty"],
                        "leg_type": "bova_put",
                        "strike": b_put.get("strike"),
                        "hedge_ratio": hedge["hedge_ratio"],
                    }
                )
            return legs
        return [
            {"symbol": sym, "side": cash_side, "quantity": 100, "leg_type": "cash"},
        ]

    @staticmethod
    def _ntsl_for_idea(idea: TradeIdea) -> str:
        from src.services.ntsl_templates import ntsl_for_idea

        return ntsl_for_idea(idea)

    def _log_paper_trades(self, idea: TradeIdea) -> None:
        from src.integrations.clear_api import ClearOrder, get_clear_client
        from src.models import JournalEntry, Trade
        from src.services.paper_execution import paper_fill_price

        fills: list[dict] = []
        for leg in idea.legs or []:
            side = leg.get("side", "buy")
            if side == "flat":
                continue
            qty = int(leg.get("quantity", 100))
            sym = leg.get("symbol", idea.symbol)
            quote = self.profit.get_quote(sym)
            price = paper_fill_price(quote, side, idea.entry_price)
            get_clear_client().place_order(ClearOrder(symbol=sym, side=side, quantity=qty))
            trade = Trade(
                external_id=f"idea-{idea.id}-{sym}-{side}",
                source="paper",
                symbol=sym,
                side=side,
                quantity=qty,
                price=price,
                fees=0.0,
                executed_at=datetime.utcnow(),
                raw_payload={
                    "idea_id": idea.id,
                    "legs": idea.legs,
                    "slippage_model": "spread_plus_1_tick",
                    "quote_bid": quote.bid if quote else None,
                    "quote_ask": quote.ask if quote else None,
                },
            )
            self.session.add(trade)
            fills.append({"symbol": sym, "side": side, "price": price, "quantity": qty})
        self.session.flush()
        self.session.add(
            JournalEntry(
                title=f"Idea #{idea.id} {idea.symbol}",
                content=idea.rationale or idea.title or "",
                tags=["idea", "paper", idea.structure_type],
                ai_generated=False,
            )
        )

    def _execute_clear_legs(self, idea: TradeIdea) -> None:
        from src.integrations.clear_api import ClearOrder, get_clear_client

        client = get_clear_client()
        for leg in idea.legs or []:
            side = leg.get("side", "buy")
            if side == "flat":
                continue
            client.place_order(
                ClearOrder(
                    symbol=leg.get("symbol", idea.symbol),
                    side=side,
                    quantity=int(leg.get("quantity", 100)),
                )
            )
        idea.status = "executed"
        idea.executed_at = datetime.utcnow()

    def to_dict(self, idea: TradeIdea) -> dict:
        proof = idea.backtest_proof or {}
        wf_passed = proof.get("walk_forward_folds_passed")
        wf_total = proof.get("walk_forward_folds_total")
        tags = idea.rationale_tags or []
        return {
            "id": idea.id,
            "symbol": idea.symbol,
            "structure_type": idea.structure_type,
            "side": idea.side,
            "status": idea.status,
            "reliability": idea.reliability,
            "entry_price": idea.entry_price,
            "stop_price": idea.stop_price,
            "target_price": idea.target_price,
            "stop_ticks": idea.stop_ticks,
            "target_ticks": idea.target_ticks,
            "title": idea.title,
            "rationale": idea.rationale,
            "rationale_tags": tags,
            "tags": tags,
            "legs": idea.legs or [],
            "backtest_proof": idea.backtest_proof,
            "walk_forward_pass": "walk_forward_pass" in tags,
            "walk_forward_folds": (
                f"{wf_passed}/{wf_total}" if wf_passed is not None and wf_total else None
            ),
            "created_at": idea.created_at.isoformat() if idea.created_at else None,
            "confirmed_at": idea.confirmed_at.isoformat() if idea.confirmed_at else None,
            "executed_at": idea.executed_at.isoformat() if idea.executed_at else None,
        }

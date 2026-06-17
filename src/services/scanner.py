"""Daily pattern scanner — IBOV Top 20 by 30d volume, scalping signals."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.config import get_settings
from src.integrations.clear_api import get_clear_client
from src.integrations.ollama_client import get_ollama_client
from src.integrations.profit_bridge import ProfitQuote, get_profit_client
from src.logging_config import get_logger
from src.models import ScanResult, SystemEvent
from src.services.ibov_universe import load_ibov_top20
from src.services.scalp_patterns import analyze_scalp
from src.services.structure_signals import compute_max_pain, max_pain_tags

logger = get_logger(__name__)

_UNIVERSE_MAP: dict[str, int] | None = None


def _symbol_seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest()[:8], 16)


def _bova_option_metrics(symbol: str, volume: int) -> tuple[int | None, float | None]:
    """Synthetic OI / IV skew for BOVA option series (until live feed)."""
    s = symbol.upper()
    if not s.startswith("BOVA") or len(s) <= 6:
        return None, None
    seed = _symbol_seed(s)
    oi = 40_000 + (seed % 600_000) + volume // 20
    iv_skew = round(((seed % 200) - 100) / 1000.0, 4)
    return oi, iv_skew


def _avg_volume_map() -> dict[str, int]:
    global _UNIVERSE_MAP
    settings = get_settings()
    from src.services.resource_profile import get_resource_profile

    prof = get_resource_profile(settings)

    def _load() -> dict[str, int]:
        if settings.scanner_mode == "filipe_core14":
            from src.services.filipe_universe import load_filipe_core14

            return {s.symbol: s.avg_volume_30d for s in load_filipe_core14()}
        return {s.symbol: s.avg_volume_30d for s in load_ibov_top20()}

    if not prof.scanner_universe_cache:
        return _load()
    if _UNIVERSE_MAP is None:
        _UNIVERSE_MAP = _load()
    return _UNIVERSE_MAP


class PatternScanner:
    """Scans IBOV top 20 for volume, momentum, and scalping patterns."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.clear = get_clear_client()
        self.profit = get_profit_client()
        self.ollama = get_ollama_client()

    def run_daily_scan(self) -> list[ScanResult]:
        results: list[ScanResult] = []
        scan_date = datetime.utcnow()
        symbols = self.settings.scanner_symbol_list

        logger.info("scan_start", mode=self.settings.scanner_mode, symbols=len(symbols))

        quote_map = self.profit.get_quotes_batch(symbols)

        for symbol in symbols:
            try:
                result = self._scan_symbol(
                    symbol,
                    scan_date,
                    quote_map.get(symbol.upper()),
                )
                results.append(result)
                self.session.add(result)
            except Exception as exc:
                logger.error("scan_symbol_failed", symbol=symbol, error=str(exc))
                self.session.add(
                    SystemEvent(
                        level="error",
                        component="scanner",
                        message=f"Scan failed for {symbol}",
                        details={"error": str(exc)},
                    )
                )

        pair_results = self._scan_sector_pairs(results, scan_date)
        for pr in pair_results:
            results.append(pr)
            self.session.add(pr)

        self.session.commit()
        logger.info("daily_scan_complete", count=len(results))
        return results

    def get_scalp_insights(self, limit: int = 5) -> list[dict]:
        """Top scalp candidates from the latest scan batch."""
        latest = self.session.query(ScanResult.scan_date).order_by(desc(ScanResult.scan_date)).first()
        if not latest:
            return []

        scans = (
            self.session.query(ScanResult)
            .filter(ScanResult.scan_date == latest[0])
            .all()
        )
        ranked: list[dict] = []
        for s in scans:
            raw = s.raw_data or {}
            reliability = raw.get("reliability", 0)
            if reliability < 15 and not s.pattern_tags:
                continue
            ranked.append(
                {
                    "symbol": s.symbol,
                    "reliability": reliability,
                    "side_bias": raw.get("side_bias", "neutral"),
                    "pattern_tags": s.pattern_tags or [],
                    "spike_score": s.spike_score,
                    "volume": s.volume,
                    "price_change_pct": s.price_change_pct,
                    "stop_ticks": raw.get("stop_ticks", 5),
                    "target_ticks": raw.get("target_ticks", 8),
                    "alert_level": s.alert_level,
                    "ai_summary": s.ai_summary,
                    "scan_date": s.scan_date.isoformat() if s.scan_date else None,
                }
            )

        ranked.sort(key=lambda x: (x["reliability"], x.get("spike_score") or 0), reverse=True)
        return ranked[:limit]

    def _scan_symbol(
        self,
        symbol: str,
        scan_date: datetime,
        quote: ProfitQuote | None = None,
    ) -> ScanResult:
        if quote is None:
            quote = self.profit.get_quote(symbol)
        volume = quote.volume if quote else 0
        last_price = quote.last if quote else None
        spread = round(quote.ask - quote.bid, 4) if quote and quote.ask and quote.bid else None

        prev = (
            self.session.query(ScanResult)
            .filter(ScanResult.symbol == symbol)
            .order_by(desc(ScanResult.scan_date))
            .first()
        )
        price_change_pct = self._price_change_pct(last_price, prev)
        avg_vol = _avg_volume_map().get(symbol)
        spike_score = min(
            100.0,
            (volume / max(avg_vol or self.settings.scanner_min_volume, 1)) * 100,
        )

        oi, iv_skew = _bova_option_metrics(symbol, volume)
        if oi is None:
            oi = int(volume * 0.12) if volume else None
            iv_skew = self._estimate_spread_skew(quote) if quote else None

        prev_last = (prev.raw_data or {}).get("last") if prev and prev.raw_data else None
        candles = self.profit.get_session_candles(symbol)
        from src.services.vwap import session_vwap, vwap_context

        vwap = session_vwap(candles)
        vwap_info = vwap_context(last=last_price, prev_last=prev_last, vwap=vwap)

        scalp = analyze_scalp(
            volume=volume,
            spike_score=spike_score,
            price_change_pct=price_change_pct,
            spread=spread,
            min_volume=self.settings.scanner_min_volume,
            avg_volume_30d=avg_vol,
            vwap_reclaim_long=vwap_info["vwap_reclaim_long"],
            vwap_reclaim_short=vwap_info["vwap_reclaim_short"],
        )
        pattern_tags = list(dict.fromkeys(scalp.pattern_tags or []))
        if iv_skew is not None and abs(iv_skew) > 0.03:
            pattern_tags.append("iv_skew")

        max_pain_signal = None
        if self.settings.max_pain_signal_enabled:
            max_pain_signal = self._max_pain_for_symbol(symbol)
            if max_pain_signal:
                pattern_tags.extend(max_pain_tags(max_pain_signal))
                pattern_tags = list(dict.fromkeys(pattern_tags))

        alert_level = "info"
        if scalp.reliability >= 60:
            alert_level = "warning"
        if scalp.reliability >= 80:
            alert_level = "critical"

        raw_data = {
            "bid": quote.bid if quote else None,
            "ask": quote.ask if quote else None,
            "last": last_price,
            "volume": volume,
            "spread": spread,
            "reliability": scalp.reliability,
            "side_bias": scalp.side_bias,
            "stop_ticks": scalp.stop_ticks,
            "target_ticks": scalp.target_ticks,
            "avg_volume_30d": avg_vol,
            "open_interest": oi,
            "iv_skew": iv_skew,
            "scanner_mode": self.settings.scanner_mode,
        }
        if max_pain_signal:
            raw_data["max_pain"] = max_pain_signal
        raw_data.update(vwap_info)

        iv_tags = self._iv_rank_tags(symbol)
        if iv_tags:
            pattern_tags.extend(iv_tags)
            pattern_tags = list(dict.fromkeys(pattern_tags))

        scan = ScanResult(
            scan_date=scan_date,
            symbol=symbol,
            volume=volume,
            open_interest=oi,
            iv_skew=iv_skew,
            price_change_pct=price_change_pct,
            spike_score=spike_score,
            pattern_tags=pattern_tags,
            alert_level=alert_level,
            raw_data=raw_data,
        )

        if (
            pattern_tags
            and self.settings.scanner_ollama_on_scan
            and self.ollama.is_available()
            and scalp.reliability >= 40
        ):
            scan.ai_summary = self.ollama.suggest_scalp_from_scan(
                {
                    "symbol": symbol,
                    "side_bias": scalp.side_bias,
                    "patterns": pattern_tags,
                    "reliability": scalp.reliability,
                    "volume": volume,
                    "price_change_pct": price_change_pct,
                    "stop_ticks": scalp.stop_ticks,
                    "target_ticks": scalp.target_ticks,
                    "hold_time": "seconds to few minutes — no overnight",
                }
            )

        return scan

    def _scan_sector_pairs(
        self,
        results: list[ScanResult],
        scan_date: datetime,
    ) -> list[ScanResult]:
        """Append pair scan rows when sector baskets diverge (A2.5a)."""
        from src.services.sector_pairs import detect_sector_pairs

        member_data = {
            r.symbol: {
                "price_change_pct": r.price_change_pct,
                "last": (r.raw_data or {}).get("last"),
            }
            for r in results
            if "/" not in r.symbol
        }
        pair_scans: list[ScanResult] = []
        for sig in detect_sector_pairs(member_data):
            label = sig.pair_label()
            raw_data = {
                "pair_long": sig.long_symbol,
                "pair_short": sig.short_symbol,
                "basket": sig.basket,
                "spread_pct": sig.spread_pct,
                "reliability": sig.reliability,
                "side_bias": "long",
                "scanner_mode": self.settings.scanner_mode,
                "signal_type": "sector_pair",
            }
            pair_scans.append(
                ScanResult(
                    scan_date=scan_date,
                    symbol=label,
                    volume=0,
                    price_change_pct=sig.spread_pct,
                    spike_score=sig.reliability,
                    pattern_tags=sig.pattern_tags,
                    alert_level="warning" if sig.reliability >= 50 else "info",
                    raw_data=raw_data,
                )
            )
        return pair_scans

    def _iv_rank_tags(self, symbol: str) -> list[str]:
        sym = symbol.upper()
        if sym.startswith("BOVAX") or sym.startswith("BOVAY") or len(sym) > 6:
            return []
        try:
            iv = self.profit.get_iv_rank(sym)
            rank = float(iv.get("iv_rank", 50))
            if rank >= 70:
                return ["iv_rank_high"]
            if rank <= 25:
                return ["iv_rank_low"]
        except Exception:
            pass
        return []

    @staticmethod
    def _price_change_pct(last_price: float | None, prev: ScanResult | None) -> float | None:
        if last_price is None or prev is None:
            return None
        prev_last = (prev.raw_data or {}).get("last") if prev.raw_data else None
        if not prev_last or prev_last == 0:
            return None
        return round((last_price - prev_last) / prev_last * 100, 4)

    @staticmethod
    def _estimate_spread_skew(quote) -> float | None:
        if quote.ask <= 0 or quote.bid <= 0:
            return None
        mid = (quote.ask + quote.bid) / 2
        if mid <= 0:
            return None
        return round((quote.ask - quote.bid) / mid, 4)

    def _max_pain_for_symbol(self, symbol: str) -> dict | None:
        sym = symbol.upper()
        from src.services.filipe_universe import BOVA_UNDERLYING, load_filipe_core14

        core14 = {s.symbol for s in load_filipe_core14()}
        if sym not in core14 and sym != BOVA_UNDERLYING and not sym.startswith("BOVA"):
            return None
        underlying = BOVA_UNDERLYING if sym.startswith("BOVA") and sym != BOVA_UNDERLYING else sym
        if underlying.startswith("BOVAX") or underlying.startswith("BOVAY"):
            underlying = BOVA_UNDERLYING
        if len(underlying) > 6 and underlying[4:5] in ("X", "Y"):
            underlying = underlying[:4] + ("4" if underlying.endswith("4") else "3")
        try:
            chain = self.profit.get_option_chain(underlying)
            if chain.get("max_pain"):
                return chain["max_pain"]
            return compute_max_pain(chain)
        except Exception as exc:
            logger.debug("max_pain_skip", symbol=sym, error=str(exc))
            return None

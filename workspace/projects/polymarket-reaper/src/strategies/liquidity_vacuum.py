"""
Stage 3: Liquidity Vacuum + Vol-Price Divergence (DESIGN.md 5.6절, AC-15, AC-16).

WebSocket 오더북/체결 이벤트 기반.
스프레드 > 0.05, 깊이 비대칭 > 3:1 → Liquidity Vacuum 감지.
Vol-Price Divergence: 흡수 괴리 + 진공 괴리.
"""

from __future__ import annotations

import time
import logging
from collections import deque
from typing import Any

from config import Config
from src.shared.types import (
    MarketData,
    Signal,
    OrderBookLevel,
    StrategyType,
    ReactorType,
    SignalUrgency,
    OrderSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger("reaper.strategy.liquidity_vacuum")


class _TradeRecord:
    """60초 윈도우 내 체결 기록."""
    __slots__ = ("timestamp", "price", "size")

    def __init__(self, timestamp: float, price: float, size: float) -> None:
        self.timestamp = timestamp
        self.price = price
        self.size = size


class LiquidityVacuumStrategy(BaseStrategy):
    """Liquidity Vacuum + Vol-Price Divergence 전략.

    Stage 3에서 Hit List 마켓의 WebSocket 이벤트를 모니터링한다.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(
            name="Liquidity Vacuum",
            strategy_type=StrategyType.LIQUIDITY_VACUUM,
            reactor=ReactorType.ALPHA,
            stage=3,
            requires_ws=True,
            enabled=getattr(config, "STRATEGY_LIQUIDITY_VACUUM", True),
        )
        self.config = config
        self.spread_threshold: float = getattr(config, "LIQUIDITY_SPREAD_THRESHOLD", 0.05)
        self.depth_ratio: float = getattr(config, "LIQUIDITY_DEPTH_RATIO", 3.0)

        # Vol-Price Divergence 파라미터
        self.vol_surge: float = getattr(config, "VOL_PRICE_VOLUME_SURGE", 3.0)
        self.vol_drought: float = getattr(config, "VOL_PRICE_VOLUME_DROUGHT", 0.3)
        self.price_threshold: float = getattr(config, "VOL_PRICE_PRICE_THRESHOLD", 0.02)
        self.price_vacuum: float = getattr(config, "VOL_PRICE_PRICE_VACUUM", 0.05)

        # 마켓별 체결 히스토리 (60초 슬라이딩 윈도우)
        self._trade_history: dict[str, deque[_TradeRecord]] = {}
        # 마켓 데이터 캐시 (on_ws_event에서 시그널 생성에 필요)
        self._market_data: dict[str, MarketData] = {}

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """Hit List 마켓을 등록한다.

        실제 시그널 생성은 on_ws_event()에서 발생한다.
        여기서는 market_data 캐시를 갱신한다.
        """
        for market in markets:
            self._market_data[market.condition_id] = market
        return []

    async def on_ws_event(self, event: dict[str, Any]) -> list[Signal]:
        """WebSocket 이벤트를 처리하여 시그널을 생성한다.

        - book 이벤트: 오더북 분석 (스프레드, 깊이 비대칭)
        - last_trade_price 이벤트: Vol-Price Divergence 체결 기록
        """
        event_type = event.get("event_type", "")
        signals: list[Signal] = []

        try:
            if event_type == "book":
                signal = self._handle_book_event(event)
                if signal is not None:
                    signals.append(signal)
            elif event_type == "last_trade_price":
                self._record_trade(event)
        except Exception as e:
            logger.error("Liquidity Vacuum WS event error: %s", e)

        return signals

    # ------------------------------------------------------------------
    # 오더북 분석 (AC-15)
    # ------------------------------------------------------------------

    def _handle_book_event(self, event: dict[str, Any]) -> Signal | None:
        """book 이벤트에서 스프레드와 깊이 비대칭을 분석한다."""
        market_id = event.get("market", "")
        asset_id = event.get("asset_id", "")

        raw_bids = event.get("bids", [])
        raw_asks = event.get("asks", [])

        bids = self._parse_levels(raw_bids)
        asks = self._parse_levels(raw_asks)

        if not bids or not asks:
            return None

        best_bid = bids[0].price
        best_ask = asks[0].price
        spread = best_ask - best_bid

        # 깊이 비대칭: 상위 5단계
        top_n = 5
        bid_depth = sum(b.size for b in bids[:top_n])
        ask_depth = sum(a.size for a in asks[:top_n])

        if bid_depth <= 0 or ask_depth <= 0:
            return None

        # 비대칭 비율
        if bid_depth > ask_depth:
            asymmetry_ratio = bid_depth / ask_depth
        else:
            asymmetry_ratio = ask_depth / bid_depth

        # 조건 체크: 스프레드 또는 깊이 비대칭
        vacuum_detected = False
        if spread > self.spread_threshold:
            vacuum_detected = True
        if asymmetry_ratio > self.depth_ratio:
            vacuum_detected = True

        if not vacuum_detected:
            return None

        # Vol-Price Divergence 보너스 (AC-16)
        vol_price_div = self._check_vol_price_divergence(market_id)
        vol_bonus = 0.10 if vol_price_div is not None else 0.0

        # 시그널 방향: 유동성 부족 쪽의 반대
        if bid_depth < ask_depth:
            # 매수벽 부재 → BUY
            side = OrderSide.BUY
        else:
            # 매도벽 부재 → SELL
            side = OrderSide.SELL

        # 마켓 데이터에서 토큰 ID
        market_data = self._market_data.get(market_id)
        if side == OrderSide.BUY:
            token_id = market_data.yes_token_id if market_data else asset_id
            price_at = best_ask
        else:
            token_id = market_data.no_token_id if market_data else asset_id
            price_at = best_bid

        if not token_id:
            token_id = asset_id

        # confidence: 0.45 ~ 0.75 (Vol-Price 보너스 포함 시 최대 0.85)
        base_conf = 0.45 + min(0.30, spread * 3.0 + (asymmetry_ratio - 1.0) * 0.05)
        confidence = min(0.85, base_conf + vol_bonus)

        # urgency: CRITICAL (스프레드 > 0.10), HIGH (0.05~0.10)
        if spread > 0.10:
            urgency = SignalUrgency.CRITICAL
        else:
            urgency = SignalUrgency.HIGH

        metadata: dict[str, Any] = {
            "spread": round(spread, 4),
            "bid_depth": round(bid_depth, 4),
            "ask_depth": round(ask_depth, 4),
            "asymmetry_ratio": round(asymmetry_ratio, 4),
            "vol_price_divergence": vol_price_div,
            "volume_ratio": None,
        }

        # volume_ratio 정보 추가
        if vol_price_div is not None:
            vr = self._get_volume_ratio(market_id)
            metadata["volume_ratio"] = round(vr, 4) if vr is not None else None

        logger.debug(
            "Liquidity Vacuum signal: market=%s spread=%.3f asymmetry=%.1f vpd=%s",
            market_id, spread, asymmetry_ratio, vol_price_div,
        )

        return self._create_signal(
            condition_id=market_id,
            token_id=token_id,
            side=side,
            confidence=confidence,
            urgency=urgency,
            price_at_signal=price_at,
            metadata=metadata,
            expires_seconds=120,  # 유동성 상황은 빠르게 변함
        )

    # ------------------------------------------------------------------
    # Vol-Price Divergence (AC-16)
    # ------------------------------------------------------------------

    def _record_trade(self, event: dict[str, Any]) -> None:
        """체결 이벤트를 60초 윈도우에 기록한다."""
        asset_id = event.get("asset_id", "")
        now = time.time()

        try:
            price = float(event.get("price", 0))
            size = float(event.get("size", 0))
        except (ValueError, TypeError):
            return

        if asset_id not in self._trade_history:
            self._trade_history[asset_id] = deque(maxlen=1000)

        history = self._trade_history[asset_id]
        history.append(_TradeRecord(timestamp=now, price=price, size=size))

        # 120초 이전 데이터 제거 (현재 60초 + 이전 60초 비교 필요)
        cutoff = now - 130
        while history and history[0].timestamp < cutoff:
            history.popleft()

    def _check_vol_price_divergence(self, market_id: str) -> str | None:
        """60초 슬라이딩 윈도우로 흡수 괴리/진공 괴리를 감지한다.

        Returns:
            "absorption" | "vacuum" | None
        """
        # market_id에 대응하는 asset_id 찾기
        market_data = self._market_data.get(market_id)
        if not market_data:
            return None

        asset_id = market_data.yes_token_id
        if not asset_id or asset_id not in self._trade_history:
            return None

        history = self._trade_history[asset_id]
        if len(history) < 2:
            return None

        now = time.time()

        # 최근 60초 vs 이전 60초
        recent: list[_TradeRecord] = []
        previous: list[_TradeRecord] = []

        for rec in history:
            age = now - rec.timestamp
            if age <= 60:
                recent.append(rec)
            elif age <= 120:
                previous.append(rec)

        if not recent or not previous:
            return None

        recent_volume = sum(r.size for r in recent)
        prev_volume = sum(r.size for r in previous)

        # 가격 변동
        if recent:
            price_change = abs(recent[-1].price - recent[0].price)
        else:
            price_change = 0.0

        if prev_volume <= 0:
            return None

        volume_ratio = recent_volume / prev_volume

        # 흡수 괴리: 거래량 급등인데 가격 불변
        if volume_ratio > self.vol_surge and price_change < self.price_threshold:
            return "absorption"

        # 평균 거래량 (이전 구간 기준)
        avg_volume = prev_volume

        # 진공 괴리: 거래량 급감인데 가격 급변
        if recent_volume < avg_volume * self.vol_drought and price_change > self.price_vacuum:
            return "vacuum"

        return None

    def _get_volume_ratio(self, market_id: str) -> float | None:
        """최근/이전 60초 거래량 비율을 반환한다."""
        market_data = self._market_data.get(market_id)
        if not market_data:
            return None

        asset_id = market_data.yes_token_id
        if not asset_id or asset_id not in self._trade_history:
            return None

        history = self._trade_history[asset_id]
        now = time.time()

        recent_vol = sum(r.size for r in history if now - r.timestamp <= 60)
        prev_vol = sum(r.size for r in history if 60 < now - r.timestamp <= 120)

        if prev_vol <= 0:
            return None
        return recent_vol / prev_vol

    # ------------------------------------------------------------------
    # 유틸리티
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_levels(raw: list[Any]) -> list[OrderBookLevel]:
        """WS 오더북 레벨을 OrderBookLevel로 파싱한다."""
        levels: list[OrderBookLevel] = []
        for item in raw:
            try:
                if isinstance(item, dict):
                    price = float(item.get("price", 0))
                    size = float(item.get("size", 0))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    price = float(item[0])
                    size = float(item[1])
                else:
                    continue
                levels.append(OrderBookLevel(price=price, size=size))
            except (ValueError, TypeError):
                continue
        return levels

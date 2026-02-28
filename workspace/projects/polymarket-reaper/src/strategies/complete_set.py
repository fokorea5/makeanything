"""
Reactor Omega: Complete Set Arbitrage (DESIGN.md 5.7절, AC-18, AC-19, AC-40).

WebSocket 실시간 가격 합 모니터링.
합 > 1.03 또는 < 0.97이면 차익 기회 감지.
Sniper Executor 직접 실행 (Signal Queue 우회).
Meta Brain에 anomaly 알림.
Alpha 시그널 큐 소거 (AC-40).
"""

from __future__ import annotations

import logging
from typing import Any

from config import Config
from src.shared.types import (
    MarketData,
    Signal,
    StrategyType,
    ReactorType,
    SignalUrgency,
    OrderSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger("reaper.strategy.complete_set")


class CompleteSetStrategy(BaseStrategy):
    """Complete Set Arbitrage 전략 (Reactor Omega).

    event_id별 마켓의 가격 합을 WS로 실시간 모니터링한다.
    합이 임계값을 벗어나면 Sniper Executor로 즉시 실행한다.
    """

    def __init__(
        self,
        config: Config,
        market_cache: Any = None,
        signal_queue: Any = None,
        meta_brain: Any = None,
    ) -> None:
        super().__init__(
            name="Complete Set Arbitrage",
            strategy_type=StrategyType.COMPLETE_SET,
            reactor=ReactorType.OMEGA,
            stage=0,
            requires_ws=True,
            enabled=getattr(config, "STRATEGY_COMPLETE_SET", True),
        )
        self.config = config
        self.market_cache = market_cache
        self.signal_queue = signal_queue
        self.meta_brain = meta_brain
        self.threshold: float = getattr(config, "COMPLETE_SET_THRESHOLD", 0.03)

        # event_id별 실시간 가격 합 추적
        self._event_prices: dict[str, dict[str, float]] = {}
        # asset_id → (event_id, condition_id) 매핑
        self._asset_to_event: dict[str, tuple[str, str]] = {}

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def register_event_groups(
        self, event_groups: dict[str, list[MarketData]]
    ) -> None:
        """engine에서 호출. event_id별 마켓 가격을 초기화한다."""
        self._event_prices.clear()
        self._asset_to_event.clear()

        for event_id, markets in event_groups.items():
            self._event_prices[event_id] = {}
            for m in markets:
                self._event_prices[event_id][m.condition_id] = m.yes_price
                # asset_id → event 매핑
                if m.yes_token_id:
                    self._asset_to_event[m.yes_token_id] = (event_id, m.condition_id)
                if m.no_token_id:
                    self._asset_to_event[m.no_token_id] = (event_id, m.condition_id)

        logger.info(
            "Complete Set: registered %d event groups, %d asset mappings",
            len(event_groups), len(self._asset_to_event),
        )

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """REST 폴링 기반 분석 (폴백용).

        실제 동작은 on_ws_event()에서 발생한다.
        """
        return []

    async def on_ws_event(self, event: dict[str, Any]) -> list[Signal]:
        """WebSocket price_change 이벤트에서 가격 합을 실시간 재계산한다.

        Returns:
            차익 기회 발견 시 시그널 리스트 (Sniper Executor 직접 전달용).
        """
        event_type = event.get("event_type", "")
        signals: list[Signal] = []

        try:
            if event_type in ("price_change", "last_trade_price"):
                signal = self._handle_price_event(event)
                if signal is not None:
                    signals.append(signal)
                    # AC-40: Alpha 시그널 큐 소거
                    await self._purge_alpha_signals(signal.condition_id)
                    # Meta Brain에 anomaly 알림 (Golden Cross 판정용)
                    await self._notify_omega_anomaly(signal)
        except Exception as e:
            logger.error("Complete Set WS event error: %s", e)

        return signals

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    def _handle_price_event(self, event: dict[str, Any]) -> Signal | None:
        """가격 이벤트에서 event_id의 가격 합을 재계산한다."""
        asset_id = event.get("asset_id", "")
        if not asset_id:
            return None

        mapping = self._asset_to_event.get(asset_id)
        if not mapping:
            return None

        event_id, condition_id = mapping

        # 가격 업데이트
        try:
            new_price = float(event.get("price", 0))
        except (ValueError, TypeError):
            return None

        if new_price <= 0 or new_price >= 1.0:
            return None

        if event_id in self._event_prices and condition_id in self._event_prices[event_id]:
            self._event_prices[event_id][condition_id] = new_price

        # 가격 합 재계산
        if event_id not in self._event_prices:
            return None

        prices = self._event_prices[event_id]
        price_sum = sum(prices.values())
        deviation = price_sum - 1.0

        # 임계값 체크: |deviation| > threshold
        if abs(deviation) < self.threshold:
            return None

        # 차익 방향 결정
        if deviation > 0:
            # 합 > 1.03: 고평가 → 모든 아웃컴 SELL
            arb_direction = "sell_all"
            side = OrderSide.SELL
            # 가장 고평가된 마켓 선택
            target_cid = max(prices, key=prices.get)  # type: ignore[arg-type]
        else:
            # 합 < 0.97: 저평가 → 저평가 아웃컴 BUY
            arb_direction = "buy_underpriced"
            side = OrderSide.BUY
            # 가장 저평가된 마켓 선택
            target_cid = min(prices, key=prices.get)  # type: ignore[arg-type]

        # 토큰 ID: market_cache에서 조회
        token_id = self._get_token_id(target_cid, side)
        if not token_id:
            logger.warning(
                "Complete Set: no token_id for %s, skipping", target_cid,
            )
            return None

        price_at = prices.get(target_cid, 0.0)

        # confidence: 0.70 ~ 0.95 (편차 크기에 비례)
        confidence = min(0.95, 0.70 + abs(deviation) * 5.0)

        metadata: dict[str, Any] = {
            "event_id": event_id,
            "markets_in_set": list(prices.keys()),
            "price_sum": round(price_sum, 4),
            "deviation": round(deviation, 4),
            "arb_direction": arb_direction,
        }

        logger.info(
            "Complete Set ARB: event=%s sum=%.4f dev=%.4f direction=%s",
            event_id, price_sum, deviation, arb_direction,
        )

        return self._create_signal(
            condition_id=target_cid,
            token_id=token_id,
            side=side,
            confidence=confidence,
            urgency=SignalUrgency.CRITICAL,
            price_at_signal=price_at,
            metadata=metadata,
            expires_seconds=30,  # 차익 기회는 매우 단기
        )

    def _get_token_id(self, condition_id: str, side: OrderSide) -> str | None:
        """market_cache에서 토큰 ID를 조회한다."""
        if self.market_cache is None:
            return None

        try:
            # market_cache가 동기인지 비동기인지 모르므로 직접 접근 시도
            if hasattr(self.market_cache, "_markets"):
                market = self.market_cache._markets.get(condition_id)
                if market:
                    return market.yes_token_id if side == OrderSide.BUY else market.no_token_id
        except Exception:
            pass

        # asset_to_event 역매핑으로 추정
        for asset_id, (_, cid) in self._asset_to_event.items():
            if cid == condition_id:
                return asset_id

        return None

    async def _purge_alpha_signals(self, market_id: str) -> None:
        """AC-40: Alpha 시그널 큐에서 해당 마켓 시그널을 소거한다."""
        if self.signal_queue is not None:
            try:
                purged = self.signal_queue.purge_market(market_id)
                if purged > 0:
                    logger.info(
                        "Complete Set: purged %d Alpha signals for market %s",
                        purged, market_id,
                    )
            except Exception as e:
                logger.warning("Failed to purge Alpha signals: %s", e)

    async def _notify_omega_anomaly(self, signal: Signal) -> None:
        """Meta Brain에 Omega 이상 감지를 알린다 (Golden Cross 판정용)."""
        if self.meta_brain is not None:
            try:
                event_id = signal.metadata.get("event_id", "")
                self.meta_brain.notify_omega_anomaly(
                    market_id=signal.condition_id,
                    event_id=event_id,
                )
            except Exception as e:
                logger.warning("Failed to notify Meta Brain: %s", e)

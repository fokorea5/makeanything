"""
Stage 2: Contrarian Z-score + 주말 드리프트 (DESIGN.md 5.4절, AC-11, AC-13).

가격 히스토리 Z-score |Z| > 2.0 → 반대 포지션.
금~일 가격 변동이 평일 stdev x 2 → 주말 과잉반응 감지.
Position Crowding Index: 보유자 쏠림 80%+ → confidence 보너스.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime
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

logger = logging.getLogger("reaper.strategy.contrarian")


class ContrarianStrategy(BaseStrategy):
    """Contrarian Z-score + 주말 드리프트 + Position Crowding 전략.

    Stage 2에서 Target List 마켓을 분석한다.
    """

    def __init__(self, config: Config, data_client: Any = None) -> None:
        super().__init__(
            name="Contrarian Z-score",
            strategy_type=StrategyType.CONTRARIAN,
            reactor=ReactorType.ALPHA,
            stage=2,
            requires_ws=False,
            enabled=getattr(config, "STRATEGY_CONTRARIAN", True),
        )
        self.config = config
        self.data_client = data_client  # AC-13: get_holders()용
        self.z_threshold: float = getattr(config, "CONTRARIAN_Z_THRESHOLD", 2.0)
        self.weekend_stdev_mult: float = getattr(config, "CONTRARIAN_WEEKEND_STDEV_MULT", 2.0)
        self.weekend_bonus: float = getattr(config, "CONTRARIAN_WEEKEND_BONUS", 0.10)
        self.crowding_threshold: float = getattr(config, "CROWDING_THRESHOLD", 0.80)
        self.crowding_bonus: float = getattr(config, "CROWDING_BONUS", 0.10)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """Target List 마켓을 분석하여 Contrarian 시그널을 반환한다."""
        signals: list[Signal] = []

        for market in markets:
            try:
                result = await self._analyze_market(market)
                if result is not None:
                    signals.append(result)
            except Exception as e:
                logger.error(
                    "Contrarian analysis failed for market %s: %s",
                    market.condition_id, e,
                )

        logger.info(
            "Contrarian: analyzed %d markets, produced %d signals",
            len(markets), len(signals),
        )
        return signals

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    async def _analyze_market(self, market: MarketData) -> Signal | None:
        """단일 마켓에 대해 Z-score, 주말 드리프트, Crowding을 분석한다."""
        prices = market.prices_history
        if not prices or len(prices) < 5:
            return None

        price_values = [p.price for p in prices]
        current_price = market.yes_price
        if current_price <= 0 or current_price >= 1.0:
            return None

        # Z-score 계산
        mean = statistics.mean(price_values)
        stdev = statistics.stdev(price_values) if len(price_values) > 1 else 0.0
        if stdev == 0:
            return None

        z_score = (current_price - mean) / stdev

        if abs(z_score) < self.z_threshold:
            return None

        # 주말 드리프트 감지 (AC-11)
        is_weekend_drift = False
        w_bonus = 0.0
        try:
            is_weekend_drift, w_bonus = self._detect_weekend_drift(prices, stdev)
        except Exception as e:
            logger.warning("Weekend drift detection failed: %s", e)

        # Position Crowding Index (AC-13)
        crowding_pct: float | None = None
        c_bonus = 0.0
        if self.data_client is not None:
            try:
                crowding_pct, c_bonus = await self._check_crowding(market)
            except Exception as e:
                # Graceful degradation: 보조지표 비활성화
                logger.warning(
                    "Crowding check failed for %s (graceful degradation): %s",
                    market.condition_id, e,
                )

        # 시그널 방향: Z-score 반대
        if z_score > 0:
            # 과매수 → NO 매수
            side = OrderSide.BUY
            token_id = market.no_token_id
            price_at = market.no_price
        else:
            # 과매도 → YES 매수
            side = OrderSide.BUY
            token_id = market.yes_token_id
            price_at = market.yes_price

        if not token_id:
            return None

        # confidence: min(0.85, 0.5 + |z| * 0.1 + weekend_bonus + crowding_bonus)
        confidence = min(0.85, 0.5 + abs(z_score) * 0.1 + w_bonus + c_bonus)

        # urgency: HIGH (|z| > 3.0), MEDIUM 그 외
        urgency = SignalUrgency.HIGH if abs(z_score) > 3.0 else SignalUrgency.MEDIUM

        metadata: dict[str, Any] = {
            "z_score": round(z_score, 4),
            "mean": round(mean, 4),
            "stdev": round(stdev, 4),
            "is_weekend_drift": is_weekend_drift,
            "weekend_bonus": round(w_bonus, 4),
            "crowding_pct": round(crowding_pct, 4) if crowding_pct is not None else None,
            "crowding_bonus": round(c_bonus, 4),
        }

        logger.debug(
            "Contrarian signal: market=%s z=%.2f weekend=%s crowding=%.2f",
            market.condition_id, z_score, is_weekend_drift,
            crowding_pct if crowding_pct is not None else 0.0,
        )

        return self._create_signal(
            condition_id=market.condition_id,
            token_id=token_id,
            side=side,
            confidence=confidence,
            urgency=urgency,
            price_at_signal=price_at,
            metadata=metadata,
            expires_seconds=300,
        )

    def _detect_weekend_drift(
        self, prices: list[Any], weekday_stdev: float
    ) -> tuple[bool, float]:
        """금~일 가격 변동이 평일 stdev x 2를 초과하는지 감지한다.

        Args:
            prices: PricePoint 리스트 (timestamp, price).
            weekday_stdev: 전체 가격의 표준편차.

        Returns:
            (is_weekend_drift, bonus) 튜플.
        """
        if weekday_stdev <= 0:
            return False, 0.0

        # 히스토리 포인트를 요일별로 분류
        weekday_prices: list[float] = []
        friday_prices: list[float] = []
        sunday_prices: list[float] = []

        for p in prices:
            dt = datetime.utcfromtimestamp(p.timestamp)
            day_of_week = dt.weekday()  # 0=월 ... 4=금, 5=토, 6=일
            if day_of_week == 4:
                friday_prices.append(p.price)
            elif day_of_week == 6:
                sunday_prices.append(p.price)
            elif day_of_week < 5:
                weekday_prices.append(p.price)

        if not friday_prices or not sunday_prices:
            return False, 0.0

        # 평일 stdev 재계산 (데이터가 충분하면)
        if len(weekday_prices) > 1:
            actual_weekday_stdev = statistics.stdev(weekday_prices)
        else:
            actual_weekday_stdev = weekday_stdev

        if actual_weekday_stdev <= 0:
            return False, 0.0

        # 주말 변동: 가장 최근 금/일 데이터 비교
        weekend_change = abs(sunday_prices[-1] - friday_prices[-1])

        if weekend_change > actual_weekday_stdev * self.weekend_stdev_mult:
            return True, self.weekend_bonus

        return False, 0.0

    async def _check_crowding(self, market: MarketData) -> tuple[float | None, float]:
        """Data API의 get_holders로 포지션 쏠림을 감지한다 (AC-13).

        Returns:
            (crowding_pct, bonus) 튜플.
            API 실패 시 (None, 0.0)을 반환한다.
        """
        token_id = market.yes_token_id
        if not token_id or self.data_client is None:
            return None, 0.0

        holders = await self.data_client.get_holders(token_id)
        if holders is None:
            # API 미존재 또는 실패: graceful degradation
            return None, 0.0

        if not holders:
            return 0.0, 0.0

        # 총 보유량 계산
        total_held = sum(float(h.get("size", 0)) for h in holders)
        if total_held <= 0:
            return 0.0, 0.0

        # 상위 보유자(상위 10명)의 비율 합산
        sorted_holders = sorted(holders, key=lambda h: float(h.get("size", 0)), reverse=True)
        top_n = min(10, len(sorted_holders))
        top_held = sum(float(sorted_holders[i].get("size", 0)) for i in range(top_n))
        crowding_pct = top_held / total_held

        bonus = self.crowding_bonus if crowding_pct >= self.crowding_threshold else 0.0
        return crowding_pct, bonus

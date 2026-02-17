"""
Stage 2: Correlated Markets -- 분석 전용 (DESIGN.md 5.5절, AC-12).

event_id별 가격 합 이상 감지 (임계값 0.02)와
Implied conditional 분석을 수행한다.
즉시 실행은 Reactor Omega(Complete Set)가 담당하며,
이 전략은 분석/식별만 수행하여 Hit List에 추가한다.
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

logger = logging.getLogger("reaper.strategy.correlated")


class CorrelatedStrategy(BaseStrategy):
    """Correlated Markets 전략 (분석 전용).

    Stage 2에서 Target List 마켓의 event_id별 가격 합 이상과
    implied conditional 미스프라이싱을 감지한다.
    """

    def __init__(self, config: Config, market_cache: Any = None) -> None:
        super().__init__(
            name="Correlated Markets",
            strategy_type=StrategyType.CORRELATED,
            reactor=ReactorType.ALPHA,
            stage=2,
            requires_ws=False,
            enabled=getattr(config, "STRATEGY_CORRELATED", True),
        )
        self.config = config
        self.market_cache = market_cache
        self.sum_threshold: float = getattr(config, "CORRELATED_SUM_THRESHOLD", 0.02)
        self.conditional_threshold: float = getattr(
            config, "CORRELATED_CONDITIONAL_THRESHOLD", 1.5
        )

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """Target List 마켓에서 상관 마켓 이상을 분석한다.

        market_cache에서 event_id별 그룹을 가져온다.
        """
        signals: list[Signal] = []

        # event_id별 그룹 구축
        event_groups = self._build_event_groups(markets)

        for event_id, group in event_groups.items():
            try:
                group_signals = self._analyze_event_group(event_id, group)
                signals.extend(group_signals)
            except Exception as e:
                logger.error(
                    "Correlated analysis failed for event %s: %s",
                    event_id, e,
                )

        logger.info(
            "Correlated: analyzed %d event groups, produced %d signals",
            len(event_groups), len(signals),
        )
        return signals

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    def _build_event_groups(
        self, markets: list[MarketData]
    ) -> dict[str, list[MarketData]]:
        """마켓을 event_id별로 그룹핑한다.

        event_id가 없는 마켓은 각 마켓의 condition_id를 키로 단독 그룹을 만든다
        (2-아웃컴 yes/no 합 체크).
        """
        groups: dict[str, list[MarketData]] = {}

        for market in markets:
            if market.event_id:
                groups.setdefault(market.event_id, []).append(market)
            else:
                # event_id가 없는 단일 마켓: 2-아웃컴 합 체크
                groups.setdefault(f"_single_{market.condition_id}", []).append(market)

        return groups

    def _analyze_event_group(
        self, event_id: str, group: list[MarketData]
    ) -> list[Signal]:
        """event_id 그룹 내 마켓들의 가격 합과 implied conditional을 분석한다."""
        signals: list[Signal] = []

        # 1. 가격 합 이상 감지 (Complete Set)
        sum_signals = self._check_price_sum(event_id, group)
        signals.extend(sum_signals)

        # 2. Implied conditional 분석 (2개 이상 마켓)
        if len(group) >= 2:
            cond_signals = self._check_implied_conditional(event_id, group)
            signals.extend(cond_signals)

        return signals

    def _check_price_sum(
        self, event_id: str, group: list[MarketData]
    ) -> list[Signal]:
        """그룹 내 마켓의 가격 합 이상을 감지한다.

        - 단일 마켓: yes_price + no_price
        - N-아웃컴 이벤트: 모든 마켓의 YES 가격 합

        합 > 1 + threshold 또는 < 1 - threshold → 시그널.
        """
        signals: list[Signal] = []

        if len(group) == 1:
            market = group[0]
            price_sum = market.yes_price + market.no_price
        else:
            price_sum = sum(m.yes_price for m in group)

        deviation = price_sum - 1.0

        if abs(deviation) < self.sum_threshold:
            return signals

        # 이상 감지: 저평가된 쪽을 찾아서 시그널 생성
        for market in group:
            if deviation > 0:
                # 합 > 1.02: 고평가 → SELL 시그널 (가격이 내려갈 것)
                # 가장 고평가된 쪽을 SELL
                if market.yes_price > 0.5:
                    side = OrderSide.SELL
                    token_id = market.yes_token_id
                    price_at = market.yes_price
                else:
                    continue
            else:
                # 합 < 0.98: 저평가 → BUY 시그널
                if market.yes_price < 0.5:
                    side = OrderSide.BUY
                    token_id = market.yes_token_id
                    price_at = market.yes_price
                else:
                    continue

            if not token_id:
                continue

            # confidence: 비례 계산
            confidence = min(0.80, 0.55 + abs(deviation) * 5.0)

            metadata: dict[str, Any] = {
                "event_id": event_id,
                "correlated_markets": [m.condition_id for m in group],
                "implied_conditional": 0.0,
                "complete_set_sum": round(price_sum, 4),
                "sum_deviation": round(deviation, 4),
            }

            signals.append(
                self._create_signal(
                    condition_id=market.condition_id,
                    token_id=token_id,
                    side=side,
                    confidence=confidence,
                    urgency=SignalUrgency.MEDIUM,
                    price_at_signal=price_at,
                    metadata=metadata,
                    expires_seconds=300,
                )
            )

        return signals

    def _check_implied_conditional(
        self, event_id: str, group: list[MarketData]
    ) -> list[Signal]:
        """Implied conditional 분석.

        P(A|B) 추정 = P(A and B) / P(B)
        P(A)*P(B)와 비교: 비율 > conditional_threshold(1.5)이면 미스프라이싱.
        """
        signals: list[Signal] = []

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                market_a = group[i]
                market_b = group[j]

                p_a = market_a.yes_price
                p_b = market_b.yes_price

                if p_a <= 0 or p_b <= 0 or p_a >= 1.0 or p_b >= 1.0:
                    continue

                # P(A)*P(B) 독립 가정
                p_independent = p_a * p_b

                # P(A and B) 추정: 간단한 근사 (min 기반)
                # 완전 관련: P(A and B) = min(P(A), P(B))
                # 실제 값은 알 수 없으므로, 가격에서 추론
                p_joint_estimate = min(p_a, p_b)

                if p_independent <= 0:
                    continue

                ratio = p_joint_estimate / p_independent

                if ratio <= self.conditional_threshold:
                    continue

                # 미스프라이싱: 저평가 쪽 BUY
                underpriced = market_a if p_a < p_b else market_b
                token_id = underpriced.yes_token_id
                if not token_id:
                    continue

                confidence = min(0.75, 0.55 + (ratio - self.conditional_threshold) * 0.1)

                metadata: dict[str, Any] = {
                    "event_id": event_id,
                    "correlated_markets": [market_a.condition_id, market_b.condition_id],
                    "implied_conditional": round(ratio, 4),
                    "complete_set_sum": 0.0,
                    "sum_deviation": 0.0,
                }

                signals.append(
                    self._create_signal(
                        condition_id=underpriced.condition_id,
                        token_id=token_id,
                        side=OrderSide.BUY,
                        confidence=confidence,
                        urgency=SignalUrgency.MEDIUM,
                        price_at_signal=underpriced.yes_price,
                        metadata=metadata,
                        expires_seconds=300,
                    )
                )

        return signals

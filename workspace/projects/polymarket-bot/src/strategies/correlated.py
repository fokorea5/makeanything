"""
전략4: 연관 시장 비효율 (Correlated Market Inefficiency).
DESIGN.md 섹션 4.4 기반.

핵심 아이디어:
논리적으로 연관된 시장(같은 이벤트/태그) 간의 가격 불일치 탐지.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from src.shared.types import (
    CORRELATED_DEFAULTS,
    Direction,
    EnrichedMarket,
    OrderType,
    Signal,
    StrategyConfig,
    TokenSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class CorrelatedStrategy(BaseStrategy):
    """
    전략4: 연관 시장 비효율.
    이벤트 그룹 + 태그 그룹 내 가격 불일치 탐지.
    """

    name = "correlated"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        if config is None:
            config = StrategyConfig(
                name=self.name,
                interval_seconds=120,
                params=CORRELATED_DEFAULTS.copy(),
            )
        super().__init__(config)

    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """시장 군집화 → 논리적 제약 검사 → 시그널 생성."""
        signals: List[Signal] = []
        sum_tolerance: float = self.get_param("sum_tolerance", 0.05)
        implied_threshold: float = self.get_param("implied_conditional_threshold", 1.5)
        min_group_size: int = self.get_param("min_group_size", 2)
        min_common_tags: int = self.get_param("min_common_tags", 2)

        try:
            # 이벤트 기반 그룹화
            event_signals = self._analyze_event_groups(
                markets, sum_tolerance, min_group_size
            )
            signals.extend(event_signals)

            # 태그 기반 그룹화
            tag_signals = self._analyze_tag_groups(
                markets, implied_threshold, min_common_tags
            )
            signals.extend(tag_signals)
        except Exception as exc:
            logger.error("correlated analyze 오류: %s", exc, exc_info=True)

        return signals

    # ----------------------------------------------------------------
    # 이벤트 기반 분석 (상호 배타 검사)
    # ----------------------------------------------------------------

    def _analyze_event_groups(
        self,
        markets: List[EnrichedMarket],
        sum_tolerance: float,
        min_group_size: int,
    ) -> List[Signal]:
        """같은 이벤트에 속한 시장들의 YES 확률 합 검사."""
        signals: List[Signal] = []

        # event_id → [EnrichedMarket] 그룹화
        groups: Dict[str, List[EnrichedMarket]] = defaultdict(list)
        for m in markets:
            eid = m.gamma.event_id
            if eid:
                groups[eid].append(m)

        for event_id, group in groups.items():
            if len(group) < min_group_size:
                continue
            try:
                sigs = self._check_exclusive_sum(group, sum_tolerance, event_id)
                signals.extend(sigs)
            except Exception as exc:
                logger.warning("이벤트 그룹 %s 분석 오류: %s", event_id, exc)

        return signals

    def _check_exclusive_sum(
        self,
        group: List[EnrichedMarket],
        sum_tolerance: float,
        event_id: str,
    ) -> List[Signal]:
        """
        상호 배타적 시장에서 YES 합이 1.0에서 크게 벗어나면 비효율.
        sum_yes > 1.05 → 가장 비싼 아웃컴 NO 매수
        sum_yes < 0.95 → 가장 싼 아웃컴 YES 매수
        """
        signals: List[Signal] = []
        yes_prices = [(m, m.yes_price) for m in group]
        sum_yes = sum(p for _, p in yes_prices)
        inefficiency = abs(sum_yes - 1.0)

        if inefficiency <= sum_tolerance:
            return signals

        if sum_yes > 1.0 + sum_tolerance:
            # 과대 평가: 가장 비싼 아웃컴의 NO 매수
            most_expensive = max(yes_prices, key=lambda x: x[1])
            market, _ = most_expensive
            token_id = self._get_no_token_id(market.gamma)
            if not token_id:
                token_id = market.gamma.condition_id

            signals.append(Signal(
                strategy_name=self.name,
                condition_id=market.gamma.condition_id,
                token_id=token_id,
                market_question=market.gamma.question,
                direction=Direction.BUY,
                token_side=TokenSide.NO,
                strength=min(inefficiency / 0.15, 1.0),
                confidence=0.75,
                reason=f"이벤트 내 YES 합={sum_yes:.3f} (과대 평가, 이벤트={event_id[:8]})",
                order_type=OrderType.GTC,
                raw_data={"sum_yes": sum_yes, "event_id": event_id, "group_size": len(group)},
            ))

        elif sum_yes < 1.0 - sum_tolerance:
            # 과소 평가: 가장 싼 아웃컴의 YES 매수
            cheapest = min(yes_prices, key=lambda x: x[1])
            market, _ = cheapest
            token_id = self._get_yes_token_id(market.gamma)
            if not token_id:
                token_id = market.gamma.condition_id

            signals.append(Signal(
                strategy_name=self.name,
                condition_id=market.gamma.condition_id,
                token_id=token_id,
                market_question=market.gamma.question,
                direction=Direction.BUY,
                token_side=TokenSide.YES,
                strength=min(inefficiency / 0.15, 1.0),
                confidence=0.75,
                reason=f"이벤트 내 YES 합={sum_yes:.3f} (과소 평가, 이벤트={event_id[:8]})",
                order_type=OrderType.GTC,
                raw_data={"sum_yes": sum_yes, "event_id": event_id, "group_size": len(group)},
            ))

        return signals

    # ----------------------------------------------------------------
    # 태그 기반 분석 (조건부 확률 검사)
    # ----------------------------------------------------------------

    def _analyze_tag_groups(
        self,
        markets: List[EnrichedMarket],
        implied_threshold: float,
        min_common_tags: int,
    ) -> List[Signal]:
        """태그 공유 시장 쌍에서 implied conditional 검사."""
        signals: List[Signal] = []

        # 태그별 시장 인덱스
        tag_map: Dict[str, List[EnrichedMarket]] = defaultdict(list)
        for m in markets:
            for tag in m.gamma.tags:
                tag_map[tag].append(m)

        # 공통 태그 수 기반 시장 쌍 생성
        seen_pairs = set()
        for tag, group in tag_map.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    pair_key = tuple(sorted([a.gamma.condition_id, b.gamma.condition_id]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    common_tags = set(a.gamma.tags) & set(b.gamma.tags)
                    if len(common_tags) < min_common_tags:
                        continue

                    try:
                        sig = self._check_implied_conditional(a, b, implied_threshold)
                        if sig:
                            signals.append(sig)
                    except Exception as exc:
                        logger.debug("implied_conditional 오류: %s", exc)

        return signals

    def _check_implied_conditional(
        self,
        market_a: EnrichedMarket,
        market_b: EnrichedMarket,
        threshold: float,
    ) -> Optional[Signal]:
        """
        P(B) / P(A) > threshold 이면 B가 과대 평가 → B의 NO 매수.
        P(A) > 0 일 때만 계산.
        """
        p_a = market_a.yes_price
        p_b = market_b.yes_price

        if p_a < 0.05:  # 너무 낮으면 나눗셈 불안정
            return None

        implied_conditional = p_b / p_a
        if implied_conditional <= threshold:
            return None

        inefficiency = implied_conditional - threshold
        token_id = self._get_no_token_id(market_b.gamma)
        if not token_id:
            token_id = market_b.gamma.condition_id

        return Signal(
            strategy_name=self.name,
            condition_id=market_b.gamma.condition_id,
            token_id=token_id,
            market_question=market_b.gamma.question,
            direction=Direction.BUY,
            token_side=TokenSide.NO,
            strength=min(inefficiency / 0.5, 1.0),
            confidence=0.75,
            reason=(
                f"implied_conditional={implied_conditional:.2f} > {threshold} "
                f"(P(A)={p_a:.2f}, P(B)={p_b:.2f})"
            ),
            order_type=OrderType.GTC,
            raw_data={
                "implied_conditional": implied_conditional,
                "p_a": p_a,
                "p_b": p_b,
                "market_a": market_a.gamma.condition_id,
                "market_b": market_b.gamma.condition_id,
            },
        )

    def _get_yes_token_id(self, gamma) -> str:
        for token in gamma.tokens:
            if token.outcome.lower() in ("yes", "true"):
                return token.token_id
        return gamma.tokens[0].token_id if gamma.tokens else ""

    def _get_no_token_id(self, gamma) -> str:
        for token in gamma.tokens:
            if token.outcome.lower() in ("no", "false"):
                return token.token_id
        return gamma.tokens[1].token_id if len(gamma.tokens) >= 2 else ""

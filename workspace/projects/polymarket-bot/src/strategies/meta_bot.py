"""
전략6: 메타봇 (Meta Bot) — 복합 스코어 계산.
DESIGN.md 섹션 4.6 및 섹션 5 기반.

핵심 아이디어:
5개 전략의 시그널을 수집하여 복합 스코어를 계산.
같은 방향으로 여러 시그널이 중첩되면 보너스를 부여하여 최종 거래 결정.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from src.shared.types import (
    Direction,
    MetaBotConfig,
    OrderType,
    Signal,
    TokenSide,
    TradeDecision,
)

logger = logging.getLogger(__name__)


class MetaBot:
    """
    메타봇: 5개 전략 시그널 → 복합 스코어 → TradeDecision 리스트.

    전략별 가중치 (설정 가능):
    - resolution_arb: 1.0
    - oracle_fear: 1.0
    - contrarian: 0.8
    - correlated: 1.2
    - liquidity_vacuum: 0.6

    중첩 보너스: (중첩 개수 - 1) × 0.15 (최대 0.60)
    실행 기준: composite_score >= 0.4
    """

    def __init__(self, config: Optional[MetaBotConfig] = None) -> None:
        self.config = config or MetaBotConfig()

    def evaluate(self, all_signals: List[Signal]) -> List[TradeDecision]:
        """
        시그널 리스트 → TradeDecision 리스트.
        같은 condition_id에 대한 시그널을 집계하여 복합 스코어 계산.
        """
        if not all_signals:
            return []

        # condition_id별 시그널 집계
        groups: Dict[str, List[Signal]] = defaultdict(list)
        for sig in all_signals:
            groups[sig.condition_id].append(sig)

        decisions: List[TradeDecision] = []
        for condition_id, signals in groups.items():
            decision = self._process_group(condition_id, signals)
            if decision:
                decisions.append(decision)

        logger.info(
            "MetaBot: %d개 시그널 → %d개 거래 결정",
            len(all_signals), len(decisions)
        )
        return decisions

    def _process_group(
        self, condition_id: str, signals: List[Signal]
    ) -> Optional[TradeDecision]:
        """
        단일 시장의 시그널 집계 → TradeDecision 생성 (기준 미달 시 None).
        """
        # 방향별 분류
        buy_signals = [s for s in signals if s.direction == Direction.BUY]
        sell_signals = [s for s in signals if s.direction == Direction.SELL]

        # 지배적 방향 결정
        if len(buy_signals) >= len(sell_signals):
            dominant_direction = Direction.BUY
            aligned = buy_signals
        else:
            dominant_direction = Direction.SELL
            aligned = sell_signals

        if not aligned:
            return None

        # 복합 스코어 계산
        composite_score = self._calculate_composite_score(aligned)

        if composite_score < self.config.min_composite_score:
            logger.debug(
                "MetaBot: %s 복합 스코어 %.2f < %.2f — 스킵",
                condition_id[:8], composite_score, self.config.min_composite_score
            )
            return None

        # 대표 토큰 및 시장 정보 결정
        # 여러 전략이 다른 token_id(YES/NO)를 가리킬 수 있음. 첫 번째 aligned 기준.
        representative = aligned[0]
        token_id = representative.token_id
        market_question = representative.market_question
        token_side = representative.token_side
        order_type = representative.order_type

        # 리밋 가격: liquidity_vacuum 전략이 제안한 가격 우선
        suggested_price: Optional[float] = None
        for s in aligned:
            if s.suggested_price is not None:
                suggested_price = s.suggested_price
                break

        logger.info(
            "MetaBot 결정: %s | 점수=%.2f | 시그널=%d개 | 방향=%s/%s",
            market_question[:40], composite_score, len(aligned),
            dominant_direction.value, token_side.value
        )

        return TradeDecision(
            condition_id=condition_id,
            token_id=token_id,
            market_question=market_question,
            direction=dominant_direction,
            token_side=token_side,
            composite_score=composite_score,
            contributing_signals=aligned,
            suggested_price=suggested_price,
            order_type=order_type,
            size=0.0,  # RiskManager가 최종 설정
        )

    def _calculate_composite_score(self, aligned_signals: List[Signal]) -> float:
        """
        복합 스코어 계산:
        composite_score = min(weighted_average + overlap_bonus, 1.0)

        weighted_average = Σ(strength * confidence * weight) / Σ(weight)
        overlap_bonus = min((count - 1) * bonus_per_signal, max_bonus)
        """
        weights = self.config.strategy_weights

        weighted_sum = 0.0
        weight_total = 0.0

        for sig in aligned_signals:
            w = weights.get(sig.strategy_name, 1.0)
            weighted_sum += sig.strength * sig.confidence * w
            weight_total += w

        if weight_total <= 0:
            return 0.0

        base_score = weighted_sum / weight_total

        # 중첩 보너스
        count = len(aligned_signals)
        overlap_bonus = min(
            (count - 1) * self.config.overlap_bonus_per_signal,
            self.config.max_overlap_bonus,
        )

        composite_score = min(base_score + overlap_bonus, 1.0)
        return composite_score

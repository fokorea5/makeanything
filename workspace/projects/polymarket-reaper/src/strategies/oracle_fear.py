"""
Stage 1: Oracle Fear Premium (DESIGN.md 5.2절, AC-08).

분쟁 키워드 감지 + YES 할인(>5센트) → YES 매수 시그널.
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

logger = logging.getLogger("reaper.strategy.oracle_fear")


class OracleFearStrategy(BaseStrategy):
    """오라클 공포 프리미엄 전략.

    분쟁(dispute) 키워드가 발견된 마켓에서 YES 가격이 비정상적으로
    낮으면 공포 프리미엄이 존재한다고 판단하여 YES 매수 시그널을 생산한다.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(
            name="Oracle Fear Premium",
            strategy_type=StrategyType.ORACLE_FEAR,
            reactor=ReactorType.ALPHA,
            stage=1,
            requires_ws=False,
            enabled=getattr(config, "STRATEGY_ORACLE_FEAR", True),
        )
        self.config = config
        self.keywords: list[str] = getattr(
            config,
            "ORACLE_FEAR_KEYWORDS",
            [
                "oracle", "UMA", "dispute", "resolution",
                "challenged", "appealed", "contested", "arbitration",
            ],
        )
        self.discount_threshold: float = getattr(config, "ORACLE_FEAR_DISCOUNT", 0.05)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """전체 활성 마켓에서 오라클 공포 프리미엄을 탐지한다."""
        signals: list[Signal] = []

        for market in markets:
            try:
                result = self._score_market(market)
                if result is not None:
                    signals.append(result)
            except Exception as e:
                logger.error(
                    "Oracle Fear analysis failed for market %s: %s",
                    market.condition_id, e,
                )

        logger.info(
            "Oracle Fear: analyzed %d markets, produced %d signals",
            len(markets), len(signals),
        )
        return signals

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    def _score_market(self, market: MarketData) -> Signal | None:
        """단일 마켓에서 오라클 공포 프리미엄을 평가한다."""
        text = self._get_text(market).lower()

        # 분쟁 키워드 감지
        found_keywords: list[str] = []
        for kw in self.keywords:
            if kw.lower() in text:
                found_keywords.append(kw)

        if not found_keywords:
            return None

        # fear_score: 발견 키워드 비율에 기반
        fear_score = min(1.0, len(found_keywords) / max(1, len(self.keywords) // 2))

        # YES 할인 감지
        yes_price = market.yes_price
        if yes_price <= 0 or yes_price >= 1.0:
            return None

        # discount: YES가 1.0보다 낮은 정도
        discount = 1.0 - yes_price

        # 가중된 할인: fear_score로 가중
        weighted_discount = discount * fear_score

        if weighted_discount < self.discount_threshold:
            return None

        # confidence: 0.5 ~ 0.75
        confidence = min(0.75, 0.5 + weighted_discount * 0.5)

        # YES 토큰 ID
        yes_token_id = market.yes_token_id
        if not yes_token_id:
            logger.warning(
                "Market %s has no YES token, skipping oracle fear signal",
                market.condition_id,
            )
            return None

        metadata: dict[str, Any] = {
            "fear_keywords": found_keywords,
            "fear_score": round(fear_score, 4),
            "discount": round(discount, 4),
            "yes_price": round(yes_price, 4),
        }

        logger.debug(
            "Oracle Fear signal: market=%s fear_score=%.3f discount=%.3f",
            market.condition_id, fear_score, discount,
        )

        return self._create_signal(
            condition_id=market.condition_id,
            token_id=yes_token_id,
            side=OrderSide.BUY,
            confidence=confidence,
            urgency=SignalUrgency.MEDIUM,
            price_at_signal=yes_price,
            metadata=metadata,
            expires_seconds=600,
        )

    @staticmethod
    def _get_text(market: MarketData) -> str:
        """마켓 질문 + 설명 + 태그 텍스트를 합친다."""
        parts: list[str] = []
        if market.question:
            parts.append(market.question)
        if market.description:
            parts.append(market.description)
        for tag in market.tags:
            parts.append(tag.label)
        return " ".join(parts)

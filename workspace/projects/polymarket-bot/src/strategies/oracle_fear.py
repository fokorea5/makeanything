"""
전략2: 오라클 공포 프리미엄 (Oracle Fear Premium).
DESIGN.md 섹션 4.2 기반.

핵심 아이디어:
오라클 불신으로 할인된 YES 가격을 탐지하여 매수한다.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.shared.types import (
    Direction,
    EnrichedMarket,
    ORACLE_FEAR_DEFAULTS,
    OrderType,
    Signal,
    StrategyConfig,
    TokenSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class OracleFearStrategy(BaseStrategy):
    """
    전략2: 오라클 공포 프리미엄.
    분쟁/논란 키워드 + 카테고리 + 고유동성 패턴으로 할인된 YES 탐지.
    """

    name = "oracle_fear"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        if config is None:
            config = StrategyConfig(
                name=self.name,
                interval_seconds=300,
                params=ORACLE_FEAR_DEFAULTS.copy(),
            )
        super().__init__(config)

    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """분쟁 스코어 계산 → 할인 탐지 → 시그널 생성."""
        signals: List[Signal] = []
        dispute_keywords: List[str] = self.get_param(
            "dispute_keywords", ORACLE_FEAR_DEFAULTS["dispute_keywords"]
        )
        dispute_categories: List[str] = self.get_param(
            "dispute_categories", ORACLE_FEAR_DEFAULTS["dispute_categories"]
        )
        dispute_threshold: float = self.get_param("dispute_threshold", 0.4)
        min_discount: float = self.get_param("min_discount", 0.05)
        min_yes_price: float = self.get_param("min_yes_price", 0.30)
        max_yes_price: float = self.get_param("max_yes_price", 0.85)

        for market in markets:
            try:
                signal = self._analyze_one(
                    market, dispute_keywords, dispute_categories,
                    dispute_threshold, min_discount, min_yes_price, max_yes_price
                )
                if signal:
                    signals.append(signal)
            except Exception as exc:
                logger.warning(
                    "oracle_fear: 마켓 %s 분석 오류: %s",
                    market.gamma.condition_id[:8], exc
                )
        return signals

    def _analyze_one(
        self,
        market: EnrichedMarket,
        dispute_keywords: List[str],
        dispute_categories: List[str],
        dispute_threshold: float,
        min_discount: float,
        min_yes_price: float,
        max_yes_price: float,
    ) -> Optional[Signal]:
        """단일 마켓 분쟁 스코어 분석."""
        gamma = market.gamma
        yes_price = market.yes_price

        # 가격 범위 필터
        if yes_price < min_yes_price or yes_price > max_yes_price:
            return None

        # --- 분쟁 스코어 계산 ---
        keyword_score = self._keyword_score(
            gamma.question + " " + gamma.description, dispute_keywords
        )
        category_score = self._category_score(gamma.tags, dispute_categories)
        volume_price_score = self._volume_price_score(gamma.volume, yes_price)

        dispute_score = keyword_score + category_score + volume_price_score
        dispute_score = min(dispute_score, 1.0)

        if dispute_score < dispute_threshold:
            return None

        # --- 할인 추정 ---
        discount = dispute_score * 0.15  # 최대 15센트 할인 추정
        if discount < min_discount:
            return None

        # YES 토큰 ID 추출
        yes_token_id = self._get_yes_token_id(gamma)
        if not yes_token_id:
            yes_token_id = gamma.condition_id

        confidence = min(discount / 0.15, 1.0) * 0.7
        reason = (
            f"오라클 공포 할인 {discount:.2f}¢, 분쟁 스코어 {dispute_score:.2f} "
            f"(키워드={keyword_score:.2f}, 카테고리={category_score:.2f}, "
            f"유동성={volume_price_score:.2f})"
        )

        return Signal(
            strategy_name=self.name,
            condition_id=gamma.condition_id,
            token_id=yes_token_id,
            market_question=gamma.question,
            direction=Direction.BUY,
            token_side=TokenSide.YES,
            strength=dispute_score,
            confidence=confidence,
            reason=reason,
            order_type=OrderType.GTC,
            raw_data={
                "dispute_score": dispute_score,
                "keyword_score": keyword_score,
                "category_score": category_score,
                "volume_price_score": volume_price_score,
                "estimated_discount": discount,
                "yes_price": yes_price,
                "volume": gamma.volume,
            },
        )

    def _keyword_score(self, text: str, keywords: List[str]) -> float:
        """분쟁 키워드 점수 (0.0 ~ 0.4)."""
        text_lower = text.lower()
        hit_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(hit_count / 4.0, 1.0) * 0.4

    def _category_score(self, tags: List[str], dispute_categories: List[str]) -> float:
        """카테고리 분쟁 이력 점수 (0.0 ~ 0.3)."""
        tags_lower = [t.lower() for t in tags]
        for cat in dispute_categories:
            if cat.lower() in tags_lower:
                return 0.3
        return 0.0

    def _volume_price_score(self, volume: float, yes_price: float) -> float:
        """고유동성 but 낮은 가격 점수 (0.0 ~ 0.3)."""
        if volume > 500_000 and yes_price < 0.70:
            return 0.3
        if volume > 100_000 and yes_price < 0.80:
            return 0.2
        return 0.0

    def _get_yes_token_id(self, gamma) -> str:
        """GammaMarket에서 YES 토큰 ID 추출."""
        for token in gamma.tokens:
            if token.outcome.lower() in ("yes", "true"):
                return token.token_id
        # tokens가 있으면 첫 번째가 YES
        if gamma.tokens:
            return gamma.tokens[0].token_id
        return ""

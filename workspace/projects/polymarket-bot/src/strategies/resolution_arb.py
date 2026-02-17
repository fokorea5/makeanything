"""
전략1: 해결 기준 아비트라지 (Resolution Arbitrage).
DESIGN.md 섹션 4.1 기반.

핵심 아이디어:
시장의 해결 기준이 모호할수록 NO로 해결될 가능성이 높다.
모호한 시장에서 NO 포지션을 매수한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.shared.types import (
    Direction,
    EnrichedMarket,
    OrderType,
    RESOLUTION_ARB_DEFAULTS,
    Signal,
    StrategyConfig,
    TokenSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

# 공식 도메인 (명확한 해결 소스)
_OFFICIAL_DOMAINS = [
    "gov", "reuters", "apnews", "bls.gov", "sec.gov",
    "federalreserve.gov", "who.int", "un.org",
]


class ResolutionArbStrategy(BaseStrategy):
    """
    전략1: 해결 기준 아비트라지.
    모호성 스코어가 높고 NO 가격이 낮은 시장에서 NO 매수 시그널.
    """

    name = "resolution_arb"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        if config is None:
            config = StrategyConfig(
                name=self.name,
                interval_seconds=300,
                params=RESOLUTION_ARB_DEFAULTS.copy(),
            )
        super().__init__(config)

    # ----------------------------------------------------------------
    # 공개 인터페이스
    # ----------------------------------------------------------------

    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """모호성 스코어 계산 → 시그널 생성."""
        signals: List[Signal] = []
        keywords: List[str] = self.get_param("keywords", RESOLUTION_ARB_DEFAULTS["keywords"])
        ambiguity_threshold: float = self.get_param("ambiguity_threshold", 0.5)
        max_no_price: float = self.get_param("max_no_price", 0.60)
        min_yes_price: float = self.get_param("min_yes_price", 0.40)

        for market in markets:
            try:
                signal = self._analyze_one(
                    market, keywords, ambiguity_threshold, max_no_price, min_yes_price
                )
                if signal:
                    signals.append(signal)
            except Exception as exc:
                logger.warning(
                    "resolution_arb: 마켓 %s 분석 오류: %s",
                    market.gamma.condition_id[:8], exc
                )
        return signals

    # ----------------------------------------------------------------
    # 내부 로직
    # ----------------------------------------------------------------

    def _analyze_one(
        self,
        market: EnrichedMarket,
        keywords: List[str],
        ambiguity_threshold: float,
        max_no_price: float,
        min_yes_price: float,
    ) -> Optional[Signal]:
        """단일 마켓 모호성 분석."""
        gamma = market.gamma
        yes_price = market.yes_price
        no_price = market.no_price  # = 1.0 - yes_price

        # 가격 범위 필터
        if yes_price < min_yes_price or no_price >= max_no_price:
            return None

        # --- 모호성 스코어 계산 ---
        keyword_score = self._keyword_score(
            gamma.question + " " + gamma.description, keywords
        )
        source_score = self._source_score(gamma.resolution_source)
        deadline_score = self._deadline_score(gamma.end_date)

        ambiguity_score = keyword_score + source_score + deadline_score
        ambiguity_score = min(ambiguity_score, 1.0)

        if ambiguity_score < ambiguity_threshold:
            return None

        # NO 토큰 ID 추출
        no_token_id = self._get_no_token_id(gamma)
        if not no_token_id:
            no_token_id = gamma.condition_id  # fallback

        reason_parts = []
        if keyword_score > 0:
            reason_parts.append(f"키워드={keyword_score:.2f}")
        if source_score > 0:
            reason_parts.append(f"소스={source_score:.2f}")
        if deadline_score > 0:
            reason_parts.append(f"마감={deadline_score:.2f}")
        reason = f"모호성 점수 {ambiguity_score:.2f}: {', '.join(reason_parts)}"

        return Signal(
            strategy_name=self.name,
            condition_id=gamma.condition_id,
            token_id=no_token_id,
            market_question=gamma.question,
            direction=Direction.BUY,
            token_side=TokenSide.NO,
            strength=ambiguity_score,
            confidence=ambiguity_score * 0.8,
            reason=reason,
            order_type=OrderType.GTC,
            raw_data={
                "ambiguity_score": ambiguity_score,
                "keyword_score": keyword_score,
                "source_score": source_score,
                "deadline_score": deadline_score,
                "yes_price": yes_price,
                "no_price": no_price,
            },
        )

    def _keyword_score(self, text: str, keywords: List[str]) -> float:
        """주관적 키워드 점수 (0.0 ~ 0.4)."""
        text_lower = text.lower()
        hit_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(hit_count / 5.0, 1.0) * 0.4

    def _source_score(self, resolution_source: str) -> float:
        """해결 소스 명확성 점수 (0.0 ~ 0.35)."""
        if not resolution_source or not resolution_source.strip():
            return 0.35  # 소스 없음 → 최대 모호

        source_lower = resolution_source.lower()
        for domain in _OFFICIAL_DOMAINS:
            if domain in source_lower:
                return 0.0  # 공식 소스 → 명확

        return 0.15  # 비공식 소스 → 중간

    def _deadline_score(self, end_date: str) -> float:
        """마감일 근접성 점수 (0.0 ~ 0.25)."""
        if not end_date:
            return 0.0
        try:
            # 여러 날짜 형식 시도
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    end_dt = datetime.strptime(end_date[:19], fmt[:len(end_date[:19])])
                    break
                except ValueError:
                    continue
            else:
                # ISO 형식 파싱 시도
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_dt = end_dt.replace(tzinfo=None)

            now = datetime.utcnow()
            days_until_end = (end_dt - now).days

            if days_until_end < 3:
                return 0.25
            elif days_until_end < 7:
                return 0.15
            return 0.0
        except Exception:
            return 0.0

    def _get_no_token_id(self, gamma) -> str:
        """GammaMarket에서 NO 토큰 ID 추출."""
        for token in gamma.tokens:
            if token.outcome.lower() in ("no", "false"):
                return token.token_id
        # tokens가 2개면 두 번째가 NO
        if len(gamma.tokens) >= 2:
            return gamma.tokens[1].token_id
        return ""

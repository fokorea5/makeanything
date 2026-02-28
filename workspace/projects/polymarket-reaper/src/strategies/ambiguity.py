"""
Stage 1: Ambiguity Scoring (DESIGN.md 5.1절, AC-07).

TF-IDF 기반 모호성 스코어링 + resolution source 미명시 감지.
모호성 > 0.6이면 NO 매수 시그널을 생산한다.
"""

from __future__ import annotations

import math
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

logger = logging.getLogger("reaper.strategy.ambiguity")


class AmbiguityStrategy(BaseStrategy):
    """모호성 스코어링 전략.

    마켓 질문/설명에서 모호 키워드를 TF-IDF로 스코어링하고,
    resolution source가 미명시되면 penalty를 추가한다.
    최종 모호성 스코어 > 0.6이면 NO 매수 시그널을 생산한다.
    """

    def __init__(self, config: Config) -> None:
        super().__init__(
            name="Ambiguity Scoring",
            strategy_type=StrategyType.AMBIGUITY,
            reactor=ReactorType.ALPHA,
            stage=1,
            requires_ws=False,
            enabled=getattr(config, "STRATEGY_AMBIGUITY", True),
        )
        self.config = config
        self.keywords: list[str] = getattr(
            config,
            "AMBIGUITY_KEYWORDS",
            [
                "might", "could", "possibly", "approximately", "around",
                "unclear", "ambiguous", "depending on", "subject to",
                "estimated", "roughly", "if", "unless",
            ],
        )
        self.threshold: float = getattr(config, "AMBIGUITY_THRESHOLD", 0.6)
        self.source_penalty: float = getattr(config, "AMBIGUITY_SOURCE_PENALTY", 0.2)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """전체 활성 마켓을 분석하여 모호성 시그널을 반환한다."""
        signals: list[Signal] = []
        total_markets = len(markets) if markets else 1

        # IDF 사전: keyword -> 해당 키워드를 포함하는 마켓 수
        idf_map = self._build_idf_map(markets, total_markets)

        for market in markets:
            try:
                result = self._score_market(market, total_markets, idf_map)
                if result is not None:
                    signals.append(result)
            except Exception as e:
                logger.error(
                    "Ambiguity analysis failed for market %s: %s",
                    market.condition_id, e,
                )
        logger.info("Ambiguity: analyzed %d markets, produced %d signals", len(markets), len(signals))
        return signals

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    def _build_idf_map(
        self, markets: list[MarketData], total_markets: int
    ) -> dict[str, float]:
        """모호 키워드별 IDF를 계산한다.

        IDF = log(전체 마켓 수 / 해당 키워드 포함 마켓 수)
        포함 마켓 수가 0이면 0으로 처리한다.
        """
        keyword_doc_freq: dict[str, int] = {kw: 0 for kw in self.keywords}

        for market in markets:
            text = self._get_text(market).lower()
            for kw in self.keywords:
                if kw.lower() in text:
                    keyword_doc_freq[kw] += 1

        idf_map: dict[str, float] = {}
        for kw, doc_freq in keyword_doc_freq.items():
            if doc_freq > 0:
                idf_map[kw] = math.log(total_markets / doc_freq)
            else:
                idf_map[kw] = 0.0
        return idf_map

    def _score_market(
        self,
        market: MarketData,
        total_markets: int,
        idf_map: dict[str, float],
    ) -> Signal | None:
        """단일 마켓에 대해 모호성을 스코어링한다."""
        text = self._get_text(market)
        text_lower = text.lower()
        words = text_lower.split()
        total_words = len(words) if words else 1

        # TF-IDF 스코어링
        keywords_found: list[str] = []
        tf_idf_sum = 0.0
        max_possible = 0.0

        for kw in self.keywords:
            kw_lower = kw.lower()
            idf = idf_map.get(kw, 0.0)
            max_possible += idf  # 모든 키워드가 등장했을 때의 최대치

            # TF: 등장 횟수 / 전체 단어 수 (multi-word 키워드 대응)
            count = text_lower.count(kw_lower)
            if count > 0:
                tf = count / total_words
                tf_idf_sum += tf * idf
                keywords_found.append(kw)

        # 0~1 정규화
        keyword_score = tf_idf_sum / max_possible if max_possible > 0 else 0.0

        # resolution source 미명시 감지 (AC-07, MINOR-10)
        has_resolution_source = bool(
            market.resolution_source and market.resolution_source.strip()
        )
        s_penalty = 0.0 if has_resolution_source else self.source_penalty

        ambiguity_score = keyword_score + s_penalty

        # 임계값 체크
        if ambiguity_score <= self.threshold:
            return None

        # confidence 계산: min(0.8, 0.5 + ambiguity_score * 0.3)
        confidence = min(0.8, 0.5 + ambiguity_score * 0.3)

        # NO 토큰 ID
        no_token_id = market.no_token_id
        if not no_token_id:
            logger.warning(
                "Market %s has no NO token, skipping ambiguity signal",
                market.condition_id,
            )
            return None

        metadata: dict[str, Any] = {
            "ambiguity_score": round(ambiguity_score, 4),
            "keyword_score": round(keyword_score, 4),
            "keywords_found": keywords_found,
            "has_resolution_source": has_resolution_source,
            "source_penalty": s_penalty,
        }

        logger.debug(
            "Ambiguity signal: market=%s score=%.3f keywords=%s",
            market.condition_id, ambiguity_score, keywords_found,
        )

        return self._create_signal(
            condition_id=market.condition_id,
            token_id=no_token_id,
            side=OrderSide.BUY,
            confidence=confidence,
            urgency=SignalUrgency.MEDIUM,
            price_at_signal=market.no_price,
            metadata=metadata,
            expires_seconds=600,
        )

    @staticmethod
    def _get_text(market: MarketData) -> str:
        """마켓 질문 + 설명 텍스트를 합친다."""
        parts: list[str] = []
        if market.question:
            parts.append(market.question)
        if market.description:
            parts.append(market.description)
        return " ".join(parts)

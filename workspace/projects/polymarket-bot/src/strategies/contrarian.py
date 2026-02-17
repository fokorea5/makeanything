"""
전략3: 군중 반대 지표 (Contrarian Indicator).
DESIGN.md 섹션 4.3 기반.

핵심 아이디어:
가격이 통계적으로 비정상(Z-score > 2)이거나 특정 패턴(주말 드리프트, 결제일 과열)
감지 시 군중 과잉 반응으로 간주하고 반대 포지션을 잡는다.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from src.shared.types import (
    CONTRARIAN_DEFAULTS,
    Direction,
    EnrichedMarket,
    OrderType,
    PricePoint,
    Signal,
    StrategyConfig,
    TokenSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class ContrarianStrategy(BaseStrategy):
    """
    전략3: 군중 반대 지표.
    Z-score 이상치 + 특수 패턴 감지 → 반대 방향 시그널.
    """

    name = "contrarian"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        if config is None:
            config = StrategyConfig(
                name=self.name,
                interval_seconds=60,
                params=CONTRARIAN_DEFAULTS.copy(),
            )
        super().__init__(config)

    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """Z-score + 패턴 감지 → 시그널 생성."""
        signals: List[Signal] = []
        zscore_threshold: float = self.get_param("zscore_threshold", 2.0)
        zscore_with_pattern: float = self.get_param("zscore_with_pattern_threshold", 1.5)

        for market in markets:
            try:
                signal = self._analyze_one(market, zscore_threshold, zscore_with_pattern)
                if signal:
                    signals.append(signal)
            except Exception as exc:
                logger.warning(
                    "contrarian: 마켓 %s 분석 오류: %s",
                    market.gamma.condition_id[:8], exc
                )
        return signals

    def _analyze_one(
        self,
        market: EnrichedMarket,
        zscore_threshold: float,
        zscore_with_pattern: float,
    ) -> Optional[Signal]:
        """단일 마켓 Z-score + 패턴 분석."""
        gamma = market.gamma
        current_price = market.yes_price

        # 가격 히스토리 필요
        if not market.price_history or len(market.price_history) < 3:
            return None

        # --- Z-score 계산 ---
        prices = [p.price for p in market.price_history]
        try:
            mean = statistics.mean(prices)
            std = statistics.stdev(prices)
        except statistics.StatisticsError:
            return None

        if std < 1e-6:  # 표준편차가 0에 가까우면 스킵
            return None

        zscore = (current_price - mean) / std

        # --- 패턴 감지 ---
        pattern_flags = self._detect_patterns(market)
        pattern_count = sum(1 for v in pattern_flags.values() if v)
        matched_patterns = [k for k, v in pattern_flags.items() if v]

        # 시그널 조건
        abs_z = abs(zscore)
        if abs_z <= zscore_threshold and not (abs_z > zscore_with_pattern and pattern_count > 0):
            return None

        # --- 방향 결정 ---
        if zscore > 0:
            # 가격이 비정상적으로 높음 → 반대 = NO 매수
            direction = Direction.BUY
            token_side = TokenSide.NO
            token_id = self._get_no_token_id(gamma)
        else:
            # 가격이 비정상적으로 낮음 → 반대 = YES 매수
            direction = Direction.BUY
            token_side = TokenSide.YES
            token_id = self._get_yes_token_id(gamma)

        if not token_id:
            token_id = gamma.condition_id

        strength = min(abs_z / 4.0, 1.0)
        confidence = min(0.6 + pattern_count * 0.1, 0.9)
        reason = (
            f"Z-score={zscore:.2f}, 패턴={matched_patterns if matched_patterns else '없음'}, "
            f"평균={mean:.3f}, std={std:.3f}"
        )

        return Signal(
            strategy_name=self.name,
            condition_id=gamma.condition_id,
            token_id=token_id,
            market_question=gamma.question,
            direction=direction,
            token_side=token_side,
            strength=strength,
            confidence=confidence,
            reason=reason,
            order_type=OrderType.GTC,
            raw_data={
                "zscore": zscore,
                "mean": mean,
                "std": std,
                "current_price": current_price,
                "patterns": pattern_flags,
                "history_count": len(prices),
            },
        )

    def _detect_patterns(self, market: EnrichedMarket) -> dict:
        """
        패턴 플래그 감지.
        반환: {"weekend_drift": bool, "settlement_frenzy": bool, "rapid_move": bool}
        """
        history = market.price_history or []
        current_price = market.yes_price
        gamma = market.gamma
        now = datetime.utcnow()

        weekend_drift_pct: float = self.get_param("weekend_drift_pct", 0.05)
        settlement_days: int = self.get_param("settlement_days", 3)
        settlement_change_pct: float = self.get_param("settlement_change_pct", 0.10)
        rapid_move_hours: int = self.get_param("rapid_move_hours", 6)
        rapid_move_pct: float = self.get_param("rapid_move_pct", 0.08)

        # 주말 드리프트: 토/일 + 금요일 대비 5% 이상 변동
        is_weekend_drift = False
        if now.weekday() >= 5:  # 5=토, 6=일
            # 금요일 가격 (48시간 이전 근사)
            fri_price = self._price_n_hours_ago(history, 48)
            if fri_price and fri_price > 0:
                change = abs(current_price - fri_price) / fri_price
                if change > weekend_drift_pct:
                    is_weekend_drift = True

        # 결제일 과열: endDate까지 3일 이내 + 24시간 변동 > 10%
        is_settlement_frenzy = False
        try:
            if gamma.end_date:
                end_dt = datetime.fromisoformat(
                    gamma.end_date.replace("Z", "+00:00")
                ).replace(tzinfo=None)
                days_left = (end_dt - now).days
                if days_left < settlement_days:
                    price_24h = self._price_n_hours_ago(history, 24)
                    if price_24h and price_24h > 0:
                        change_24h = abs(current_price - price_24h) / price_24h
                        if change_24h > settlement_change_pct:
                            is_settlement_frenzy = True
        except Exception:
            pass

        # 급변 감지: 최근 6시간 변동 > 8%
        is_rapid_move = False
        price_6h = self._price_n_hours_ago(history, rapid_move_hours)
        if price_6h and price_6h > 0:
            change_6h = abs(current_price - price_6h) / price_6h
            if change_6h > rapid_move_pct:
                is_rapid_move = True

        return {
            "weekend_drift": is_weekend_drift,
            "settlement_frenzy": is_settlement_frenzy,
            "rapid_move": is_rapid_move,
        }

    def _price_n_hours_ago(
        self, history: List[PricePoint], hours: int
    ) -> Optional[float]:
        """N시간 전 가격 추출 (가장 가까운 히스토리 포인트)."""
        if not history:
            return None
        import time
        target_ts = time.time() - hours * 3600
        # 타겟 시각에 가장 가까운 과거 포인트 찾기
        best = None
        best_diff = float("inf")
        for pt in history:
            diff = abs(pt.timestamp - target_ts)
            if diff < best_diff:
                best_diff = diff
                best = pt
        return best.price if best else None

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

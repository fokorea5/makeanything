"""
Meta Brain -- Golden Cross (DESIGN.md 3.8절, AC-20, AC-21, AC-22).

시그널 버퍼링 (600초 윈도우).
Golden Cross 판정: Alpha + Omega 교차 → confidence 보너스 + Kelly 1.5x.
전략별 가중치 → 가중 평균 confidence.
TradeDecision 생성.
"""

from __future__ import annotations

import uuid
import time
import logging
from typing import Any

from config import Config
from src.shared.types import (
    Signal,
    TradeDecision,
    StrategyType,
    ReactorType,
    SignalUrgency,
    ExecutorMode,
)

logger = logging.getLogger("reaper.core.meta_brain")


class MetaBrain:
    """Meta Brain: Golden Cross 탐지 및 TradeDecision 생성.

    Alpha와 Omega의 시그널을 교차 분석하여 증폭한다.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.signal_window_sec: int = getattr(config, "META_SIGNAL_WINDOW_SEC", 600)
        self.golden_cross_kelly_mult: float = getattr(
            config, "META_GOLDEN_CROSS_KELLY_MULT", 1.5
        )
        self.golden_cross_bonus: float = 0.10

        # 전략별 가중치
        self.weights: dict[StrategyType, float] = {
            StrategyType.AMBIGUITY: getattr(config, "WEIGHT_AMBIGUITY", 1.2),
            StrategyType.ORACLE_FEAR: getattr(config, "WEIGHT_ORACLE_FEAR", 1.0),
            StrategyType.CONTRARIAN: getattr(config, "WEIGHT_CONTRARIAN", 1.1),
            StrategyType.CORRELATED: getattr(config, "WEIGHT_CORRELATED", 1.3),
            StrategyType.LIQUIDITY_VACUUM: getattr(config, "WEIGHT_LIQUIDITY_VACUUM", 0.9),
            StrategyType.COMPLETE_SET: getattr(config, "WEIGHT_COMPLETE_SET", 1.4),
        }

        # market_id별 시그널 버퍼 {market_id: list[Signal]}
        self._signal_buffer: dict[str, list[Signal]] = {}

        # Omega 이상 감지 기록 {market_id: (event_id, timestamp)}
        self._omega_anomalies: dict[str, tuple[str, float]] = {}

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def notify_omega_anomaly(self, market_id: str, event_id: str) -> None:
        """Omega가 이상을 감지했음을 기록한다 (Golden Cross 판정용).

        이 정보는 Golden Cross 판정에만 사용되며, Omega의 실행을 지연시키지 않는다.
        """
        self._omega_anomalies[market_id] = (event_id, time.time())
        logger.info(
            "Omega anomaly recorded: market=%s event=%s", market_id, event_id,
        )

    async def consume(self, signal: Signal) -> TradeDecision | None:
        """시그널을 소비하고 TradeDecision을 생성한다.

        1. 시그널을 버퍼에 추가한다.
        2. 윈도우 내 시그널을 수집한다.
        3. Golden Cross를 판정한다.
        4. 전략별 가중치로 가중 평균 confidence를 산출한다.
        5. TradeDecision을 생성한다.
        """
        market_id = signal.condition_id
        now = time.time()

        # 버퍼에 추가
        if market_id not in self._signal_buffer:
            self._signal_buffer[market_id] = []
        self._signal_buffer[market_id].append(signal)

        # 윈도우 외 시그널 제거
        self._clean_buffer(market_id, now)

        # 현재 윈도우 내 시그널
        buffered = self._signal_buffer.get(market_id, [])
        if not buffered:
            return None

        # Golden Cross 판정 (AC-21)
        golden_cross = self._check_golden_cross(market_id, now)

        # 전략별 가중치 적용 → 가중 평균 confidence (AC-22)
        weighted_confidence, convergence_bonus = self._compute_weighted_confidence(
            buffered
        )

        # Golden Cross 보너스
        final_confidence = weighted_confidence + convergence_bonus
        if golden_cross:
            final_confidence += self.golden_cross_bonus

        final_confidence = min(1.0, final_confidence)

        # 가장 높은 urgency 채택
        best_urgency = min(buffered, key=lambda s: int(s.urgency)).urgency

        # Executor 모드 결정
        if best_urgency in (SignalUrgency.CRITICAL, SignalUrgency.HIGH):
            executor_mode = ExecutorMode.SNIPER
        else:
            executor_mode = ExecutorMode.PATIENT

        # TradeDecision 생성
        decision = TradeDecision(
            id=str(uuid.uuid4()),
            condition_id=market_id,
            token_id=signal.token_id,
            side=signal.side,
            confidence=final_confidence,
            urgency=best_urgency,
            contributing_signals=[s.id for s in buffered],
            convergence_count=len(buffered),
            weighted_confidence=weighted_confidence,
            convergence_bonus=convergence_bonus,
            price_at_decision=signal.price_at_signal,
            executor_mode=executor_mode,
            reactor_source=signal.reactor_source,
            golden_cross=golden_cross,
            holding_cost=0.0,  # Risk Sentinel에서 계산
        )

        logger.info(
            "TradeDecision: market=%s conf=%.3f golden_cross=%s signals=%d urgency=%s",
            market_id, final_confidence, golden_cross, len(buffered), best_urgency.name,
        )

        return decision

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------

    def _clean_buffer(self, market_id: str, now: float) -> None:
        """윈도우 외 시그널을 버퍼에서 제거한다."""
        if market_id not in self._signal_buffer:
            return

        cutoff = now - self.signal_window_sec
        self._signal_buffer[market_id] = [
            s for s in self._signal_buffer[market_id]
            if s.created_at.timestamp() > cutoff and not s.is_expired
        ]

    def _check_golden_cross(self, market_id: str, now: float) -> bool:
        """Alpha Hit List 마켓에서 Omega도 이상 감지 → Golden Cross.

        Alpha 시그널이 있고, Omega도 해당 마켓에서 이상을 감지한 경우.
        """
        # Alpha 시그널 존재 여부
        buffered = self._signal_buffer.get(market_id, [])
        has_alpha = any(
            s.reactor_source == ReactorType.ALPHA for s in buffered
        )

        if not has_alpha:
            return False

        # Omega 이상 감지 기록 확인
        omega_record = self._omega_anomalies.get(market_id)
        if omega_record is None:
            return False

        _, omega_timestamp = omega_record
        # 윈도우 내인지 확인
        if now - omega_timestamp > self.signal_window_sec:
            return False

        logger.info("Golden Cross detected for market %s", market_id)
        return True

    def _compute_weighted_confidence(
        self, signals: list[Signal]
    ) -> tuple[float, float]:
        """전략별 가중치로 가중 평균 confidence를 산출한다.

        Returns:
            (weighted_confidence, convergence_bonus) 튜플.
        """
        if not signals:
            return 0.0, 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for s in signals:
            weight = self.weights.get(s.strategy, 1.0)
            weighted_sum += s.confidence * weight
            total_weight += weight

        weighted_confidence = weighted_sum / total_weight if total_weight > 0 else 0.0

        # 중첩 보너스: 2개 이상 전략이 수렴하면 보너스
        unique_strategies = set(s.strategy for s in signals)
        if len(unique_strategies) >= 3:
            convergence_bonus = 0.10
        elif len(unique_strategies) >= 2:
            convergence_bonus = 0.05
        else:
            convergence_bonus = 0.0

        return round(weighted_confidence, 4), convergence_bonus

    def clean_stale(self) -> None:
        """오래된 버퍼와 anomaly 기록을 정리한다."""
        now = time.time()
        cutoff = now - self.signal_window_sec * 2

        # 시그널 버퍼 정리
        stale_markets = [
            mid for mid, signals in self._signal_buffer.items()
            if not signals or all(s.created_at.timestamp() < cutoff for s in signals)
        ]
        for mid in stale_markets:
            del self._signal_buffer[mid]

        # Omega anomaly 정리
        stale_anomalies = [
            mid for mid, (_, ts) in self._omega_anomalies.items()
            if ts < cutoff
        ]
        for mid in stale_anomalies:
            del self._omega_anomalies[mid]

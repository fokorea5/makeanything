"""
BaseStrategy -- 모든 전략의 추상 기반 클래스 (DESIGN.md 3.12절).

모든 전략은 이 클래스를 상속하고 analyze()를 구현해야 한다.
WebSocket 기반 전략(Stage 3 / Omega)은 on_ws_event()도 오버라이드한다.
"""

from __future__ import annotations

import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

from src.shared.types import (
    MarketData,
    Signal,
    StrategyType,
    ReactorType,
    SignalUrgency,
    OrderSide,
)

logger = logging.getLogger("reaper.strategy.base")


class BaseStrategy(ABC):
    """전략 추상 기반 클래스.

    Attributes:
        name: 사람이 읽을 수 있는 전략 이름.
        strategy_type: StrategyType enum 값.
        reactor: ALPHA 또는 OMEGA.
        stage: 1, 2, 3 (Alpha) 또는 0 (Omega).
        requires_ws: True이면 WebSocket 이벤트를 수신한다.
        enabled: False이면 engine이 이 전략을 건너뛴다.
    """

    name: str
    strategy_type: StrategyType
    reactor: ReactorType
    stage: int
    requires_ws: bool = False
    enabled: bool = True

    def __init__(
        self,
        name: str,
        strategy_type: StrategyType,
        reactor: ReactorType,
        stage: int,
        requires_ws: bool = False,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.strategy_type = strategy_type
        self.reactor = reactor
        self.stage = stage
        self.requires_ws = requires_ws
        self.enabled = enabled

    # ------------------------------------------------------------------
    # 추상 메서드
    # ------------------------------------------------------------------

    @abstractmethod
    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """마켓 목록을 분석하여 0개 이상의 시그널을 반환한다.

        - Stage 1: 전체 활성 마켓 입력.
        - Stage 2: Target List 입력.
        - Stage 3: Hit List 입력 (WS 이벤트 기반).
        """
        ...

    # ------------------------------------------------------------------
    # WS 이벤트 수신 (Stage 3 / Omega 전략만 오버라이드)
    # ------------------------------------------------------------------

    async def on_ws_event(self, event: dict[str, Any]) -> list[Signal]:
        """WebSocket 이벤트를 처리하여 시그널을 반환한다.

        기본 구현은 빈 리스트를 반환한다.
        requires_ws=True인 전략만 오버라이드해야 한다.
        """
        return []

    # ------------------------------------------------------------------
    # 시그널 생성 헬퍼
    # ------------------------------------------------------------------

    def _create_signal(
        self,
        condition_id: str,
        token_id: str,
        side: OrderSide,
        confidence: float,
        urgency: SignalUrgency,
        price_at_signal: float,
        metadata: dict[str, Any] | None = None,
        expires_seconds: int = 600,
    ) -> Signal:
        """Signal 인스턴스를 생성하는 헬퍼.

        reactor_source는 self.reactor에서 자동으로 설정된다.

        Args:
            condition_id: 마켓 condition ID.
            token_id: 대상 토큰 ID.
            side: BUY 또는 SELL.
            confidence: 0.0 ~ 1.0.
            urgency: SignalUrgency enum.
            price_at_signal: 시그널 생성 시 해당 토큰 가격.
            metadata: 전략별 추가 데이터.
            expires_seconds: 만료까지 초 (기본 600초).

        Returns:
            Signal 인스턴스.
        """
        now = datetime.utcnow()
        signal_id = str(uuid.uuid4())
        return Signal(
            sort_key=(int(urgency), now.timestamp()),
            id=signal_id,
            strategy=self.strategy_type,
            reactor_source=self.reactor,
            condition_id=condition_id,
            token_id=token_id,
            side=side,
            confidence=confidence,
            urgency=urgency,
            price_at_signal=price_at_signal,
            metadata=metadata or {},
            expires_at=now + timedelta(seconds=expires_seconds),
            created_at=now,
        )

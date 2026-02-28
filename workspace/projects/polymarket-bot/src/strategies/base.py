"""
BaseStrategy — 모든 전략이 구현하는 추상 기반 클래스.
DESIGN.md 섹션 4.0 기반.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List

from src.shared.types import EnrichedMarket, Signal, StrategyConfig

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    모든 전략이 구현하는 추상 기반 클래스.

    서브클래스 규칙:
    - name: 전략 이름 (소문자_언더스코어). DESIGN.md 8.2의 STRATEGY_INTERVALS 키와 일치.
    - analyze(): 빈 리스트 반환이면 시그널 없음 (절대 None 반환 금지).
    """

    name: str = "base"

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config
        self._log = logging.getLogger(f"strategy.{self.name}")

    @abstractmethod
    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """
        입력: EnrichedMarket 리스트 (Gamma 메타데이터 + CLOB 가격).
        출력: Signal 리스트. 빈 리스트이면 시그널 없음.
        예외를 발생시키지 마세요 — 내부에서 처리하고 빈 리스트 반환.
        """
        raise NotImplementedError

    def safe_analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """
        analyze()를 호출하되, 예외 발생 시 로그 + 빈 리스트 반환.
        TradingEngine에서 이 메서드를 호출합니다.
        """
        try:
            signals = self.analyze(markets)
            self._log.info(
                "%s: %d개 시그널 생성 (마켓 %d개 분석)",
                self.name, len(signals), len(markets)
            )
            return signals
        except Exception as exc:
            self._log.error("%s analyze 예외 발생: %s", self.name, exc, exc_info=True)
            return []

    @property
    def is_enabled(self) -> bool:
        """전략 활성화 여부."""
        return self.config.enabled

    def get_param(self, key: str, default=None):
        """전략 파라미터 조회."""
        return self.config.params.get(key, default)

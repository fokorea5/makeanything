"""
전략5: 유동성 진공 사냥 (Liquidity Vacuum Hunting).
DESIGN.md 섹션 4.5 기반.

핵심 아이디어:
스프레드가 크고 오더북 한쪽 깊이가 비대칭일 때
스프레드 중간에 리밋 오더를 놓아 마켓메이킹 이익을 노린다.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.shared.types import (
    Direction,
    EnrichedMarket,
    LIQUIDITY_VACUUM_DEFAULTS,
    OrderBook,
    OrderType,
    Signal,
    StrategyConfig,
    TokenSide,
)
from src.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class LiquidityVacuumStrategy(BaseStrategy):
    """
    전략5: 유동성 진공 사냥.
    spread > 0.05 AND depth_ratio > 2.0 이면 리밋 오더 시그널.
    확신도 낮음 (0.5) — 단기적 기회이므로 메타봇 가중치도 낮음(0.6).
    """

    name = "liquidity_vacuum"

    def __init__(self, config: Optional[StrategyConfig] = None) -> None:
        if config is None:
            config = StrategyConfig(
                name=self.name,
                interval_seconds=30,
                params=LIQUIDITY_VACUUM_DEFAULTS.copy(),
            )
        super().__init__(config)

    def analyze(self, markets: List[EnrichedMarket]) -> List[Signal]:
        """오더북 분석 → 유동성 진공 시그널 생성."""
        signals: List[Signal] = []
        min_spread: float = self.get_param("min_spread", 0.05)
        min_depth_ratio: float = self.get_param("min_depth_ratio", 2.0)
        spread_offset_ratio: float = self.get_param("spread_offset_ratio", 0.4)
        depth_levels: int = self.get_param("depth_levels", 5)

        for market in markets:
            try:
                signal = self._analyze_one(
                    market, min_spread, min_depth_ratio,
                    spread_offset_ratio, depth_levels
                )
                if signal:
                    signals.append(signal)
            except Exception as exc:
                logger.warning(
                    "liquidity_vacuum: 마켓 %s 분석 오류: %s",
                    market.gamma.condition_id[:8], exc
                )
        return signals

    def _analyze_one(
        self,
        market: EnrichedMarket,
        min_spread: float,
        min_depth_ratio: float,
        spread_offset_ratio: float,
        depth_levels: int,
    ) -> Optional[Signal]:
        """단일 마켓 오더북 유동성 진공 분석."""
        order_book = market.order_book
        if not order_book:
            return None

        gamma = market.gamma

        # --- 스프레드 계산 ---
        best_bid = order_book.best_bid   # bids 없으면 0.0
        best_ask = order_book.best_ask   # asks 없으면 1.0
        spread = best_ask - best_bid

        if spread <= min_spread:
            return None

        # --- 깊이 비율 계산 ---
        bid_depth = order_book.bid_depth(depth_levels)
        ask_depth = order_book.ask_depth(depth_levels)

        # 0으로 나누기 방지
        min_depth = max(min(bid_depth, ask_depth), 0.01)
        max_depth = max(bid_depth, ask_depth)
        depth_ratio = max_depth / min_depth

        if depth_ratio <= min_depth_ratio:
            return None

        # --- 방향 결정 ---
        if bid_depth > ask_depth:
            # 매수 압력 → BUY 리밋
            direction = Direction.BUY
            token_side = TokenSide.YES
            suggested_price = best_bid + spread * spread_offset_ratio
            token_id = self._get_yes_token_id(gamma)
            dominant = "bid"
        else:
            # 매도 압력 → SELL → NO 매수로 전환
            direction = Direction.BUY
            token_side = TokenSide.NO
            suggested_price = best_ask - spread * spread_offset_ratio
            token_id = self._get_no_token_id(gamma)
            dominant = "ask"

        if not token_id:
            token_id = gamma.condition_id

        # 가격 클램핑 (0.01 ~ 0.99)
        suggested_price = max(0.01, min(0.99, suggested_price))

        strength = min(spread / 0.15, 1.0) * min(depth_ratio / 5.0, 1.0)

        reason = (
            f"spread={spread:.3f}, depth_ratio={depth_ratio:.1f}, "
            f"방향={dominant} 우세 (bid={bid_depth:.1f}, ask={ask_depth:.1f})"
        )

        return Signal(
            strategy_name=self.name,
            condition_id=gamma.condition_id,
            token_id=token_id,
            market_question=gamma.question,
            direction=direction,
            token_side=token_side,
            strength=strength,
            confidence=0.5,
            reason=reason,
            suggested_price=suggested_price,
            order_type=OrderType.GTC,  # 리밋 오더 GTC
            raw_data={
                "spread": spread,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "bid_depth": bid_depth,
                "ask_depth": ask_depth,
                "depth_ratio": depth_ratio,
                "suggested_price": suggested_price,
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

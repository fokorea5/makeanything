"""
RiskManager — 리스크 관리.
DESIGN.md 섹션 7 기반.

거래 결정이 리스크 파라미터를 초과하는지 검사하고 주문 크기를 조정합니다.
"""

from __future__ import annotations

import logging
from typing import List

from src.db.database import Database
from src.shared.types import (
    Position,
    RiskCheckResult,
    RiskConfig,
    TradeDecision,
)

logger = logging.getLogger(__name__)


class RiskManager:
    """
    리스크 검사기.
    check()는 TradeDecision을 받아 승인/거부 + 조정된 크기를 반환합니다.
    """

    def __init__(self, config: RiskConfig, db: Database, dry_run: bool = True) -> None:
        self.config = config
        self.db = db
        self.dry_run = dry_run

    def check(
        self,
        decision: TradeDecision,
        current_positions: List[Position],
    ) -> RiskCheckResult:
        """
        거래 결정 리스크 검사.
        순서:
          1. 일일 손실 한도
          2. 오픈 주문 수 한도
          3. 포트폴리오 노출 한도
          4. 단일 시장 집중도 한도
          5. 주문 크기 (최대/최소) 조정
        """
        cfg = self.config

        # 기본 제안 크기: composite_score에 비례 (max_position_size_usd의 50%~100%)
        base_size = cfg.max_position_size_usd * max(decision.composite_score, 0.5)
        adjusted_size = base_size

        # 1. 일일 손실 한도
        try:
            today_pnl = self.db.get_today_pnl(dry_run=self.dry_run)
            if today_pnl < -cfg.max_daily_loss_usd:
                return RiskCheckResult(
                    approved=False,
                    adjusted_size=0.0,
                    reason=(
                        f"일일 손실 한도 초과: {today_pnl:.2f} USD "
                        f"(한도: -{cfg.max_daily_loss_usd:.2f} USD). 거래 중단."
                    ),
                    original_size=adjusted_size,
                )
        except Exception as exc:
            logger.warning("일일 P&L 조회 실패: %s", exc)

        # 2. 오픈 주문 수 한도
        try:
            open_orders = self.db.get_open_order_count()
            if open_orders >= cfg.max_open_orders:
                return RiskCheckResult(
                    approved=False,
                    adjusted_size=0.0,
                    reason=(
                        f"오픈 주문 수 한도 초과: {open_orders}/{cfg.max_open_orders}"
                    ),
                    original_size=adjusted_size,
                )
        except Exception as exc:
            logger.warning("오픈 주문 수 조회 실패: %s", exc)

        # 3. 포트폴리오 노출 한도
        total_exposure = sum(p.size * p.current_price for p in current_positions)
        if total_exposure + adjusted_size > cfg.max_portfolio_exposure_usd:
            remaining = cfg.max_portfolio_exposure_usd - total_exposure
            if remaining < cfg.min_order_size_usd:
                return RiskCheckResult(
                    approved=False,
                    adjusted_size=0.0,
                    reason=(
                        f"포트폴리오 노출 한도 초과: 현재 {total_exposure:.2f} USD, "
                        f"한도 {cfg.max_portfolio_exposure_usd:.2f} USD."
                    ),
                    original_size=adjusted_size,
                )
            adjusted_size = remaining
            logger.info(
                "포트폴리오 한도로 주문 크기 축소: %.2f → %.2f USD",
                base_size, adjusted_size
            )

        # 4. 단일 시장 집중도 한도
        if total_exposure > 0:
            market_exposure = sum(
                p.size * p.current_price
                for p in current_positions
                if p.condition_id == decision.condition_id
            )
            portfolio_value = total_exposure + adjusted_size
            concentration = (market_exposure + adjusted_size) / portfolio_value
            if concentration > cfg.max_single_market_pct:
                max_market_usd = portfolio_value * cfg.max_single_market_pct - market_exposure
                if max_market_usd < cfg.min_order_size_usd:
                    return RiskCheckResult(
                        approved=False,
                        adjusted_size=0.0,
                        reason=(
                            f"단일 시장 집중도 초과: {concentration:.1%} > "
                            f"{cfg.max_single_market_pct:.1%}."
                        ),
                        original_size=adjusted_size,
                    )
                adjusted_size = min(adjusted_size, max_market_usd)
                logger.info(
                    "집중도 한도로 주문 크기 축소: %.2f → %.2f USD",
                    base_size, adjusted_size
                )

        # 5. 주문 크기 클램핑
        if adjusted_size > cfg.max_position_size_usd:
            adjusted_size = cfg.max_position_size_usd
            logger.info("최대 포지션 크기로 축소: %.2f USD", adjusted_size)

        if adjusted_size < cfg.min_order_size_usd:
            return RiskCheckResult(
                approved=False,
                adjusted_size=0.0,
                reason=(
                    f"주문 크기 {adjusted_size:.2f} USD < "
                    f"최소 {cfg.min_order_size_usd:.2f} USD."
                ),
                original_size=adjusted_size,
            )

        logger.info(
            "RiskManager 승인: %s | 크기=%.2f USD | 점수=%.2f",
            decision.market_question[:40], adjusted_size, decision.composite_score
        )
        return RiskCheckResult(
            approved=True,
            adjusted_size=adjusted_size,
            reason="리스크 검사 통과",
            original_size=base_size,
        )

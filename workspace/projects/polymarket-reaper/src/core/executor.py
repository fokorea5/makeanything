"""
Dual Executor (DESIGN.md 3.10절, AC-31, AC-32, AC-33).

Sniper: FOK, slippage tolerance. CRITICAL/HIGH urgency.
Patient: GTC + postOnly. MEDIUM/LOW urgency.
DRY_RUN 모드에서는 가상 체결 기록.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any

from config import Config
from src.shared.types import (
    TradeDecision,
    RiskApproval,
    TradeResult,
    TradeStatus,
    OrderType,
    ExecutorMode,
    SignalUrgency,
)

logger = logging.getLogger("reaper.core.executor")


class Executor:
    """Dual Executor: Sniper(FOK) + Patient(GTC/postOnly).

    Risk Sentinel을 통과한 TradeDecision을 실제 주문으로 변환한다.
    """

    def __init__(
        self,
        config: Config,
        clob_client: Any = None,
        db_manager: Any = None,
        portfolio_tracker: Any = None,
    ) -> None:
        self.config = config
        self.clob_client = clob_client
        self.db_manager = db_manager
        self.portfolio_tracker = portfolio_tracker
        self.dry_run: bool = getattr(config, "DRY_RUN", True)
        self.slippage_tolerance: float = getattr(config, "SLIPPAGE_TOLERANCE", 0.02)
        self.sniper_max_retry: int = getattr(config, "SNIPER_MAX_RETRY", 1)
        self.patient_post_only: bool = getattr(config, "PATIENT_POST_ONLY", True)

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def execute(
        self, decision: TradeDecision, approval: RiskApproval,
    ) -> TradeResult:
        """거래 결정을 실행한다.

        urgency에 따라 Sniper 또는 Patient 모드로 라우팅한다.
        """
        if decision.urgency in (SignalUrgency.CRITICAL, SignalUrgency.HIGH):
            result = await self._sniper_execute(decision, approval)
        else:
            result = await self._patient_execute(decision, approval)

        # DB 기록
        await self._record_trade(result)

        # DRY_RUN 가상 포지션 기록
        if result.is_dry_run and self.portfolio_tracker is not None:
            try:
                await self.portfolio_tracker.record_virtual_trade(result)
            except Exception as e:
                logger.warning("Virtual trade recording failed: %s", e)

        return result

    # ------------------------------------------------------------------
    # Sniper Executor (AC-31)
    # ------------------------------------------------------------------

    async def _sniper_execute(
        self, decision: TradeDecision, approval: RiskApproval,
    ) -> TradeResult:
        """FOK (Fill-Or-Kill) 주문.

        가격: midpoint +/- slippage_tolerance.
        DRY_RUN: 현재 midpoint 기준 가상 체결.
        """
        target_price = approval.target_price

        # slippage 적용
        if decision.side.value == "BUY":
            limit_price = round(target_price + self.slippage_tolerance, 4)
        else:
            limit_price = round(max(0.01, target_price - self.slippage_tolerance), 4)

        if self.dry_run:
            return self._create_dry_run_result(
                decision, approval, limit_price, ExecutorMode.SNIPER, OrderType.FOK,
            )

        # 실제 주문 (최대 1회 재시도)
        order_id = None
        status = TradeStatus.REJECTED
        executed_price = limit_price

        for attempt in range(1 + self.sniper_max_retry):
            try:
                if self.clob_client is not None:
                    order_result = await self.clob_client.post_order(
                        token_id=decision.token_id,
                        side=decision.side.value,
                        price=limit_price,
                        size=approval.final_size_tokens,
                        order_type=OrderType.FOK.value,
                    )
                    if order_result and order_result.get("orderID"):
                        order_id = order_result["orderID"]
                        status = TradeStatus.FILLED
                        executed_price = float(order_result.get("price", limit_price))
                        break
            except Exception as e:
                logger.warning(
                    "Sniper attempt %d failed: %s", attempt + 1, e,
                )
                if attempt >= self.sniper_max_retry:
                    logger.error("Sniper execution failed after retries")

        return self._build_result(
            decision, approval, executed_price, ExecutorMode.SNIPER,
            OrderType.FOK, order_id, status,
        )

    # ------------------------------------------------------------------
    # Patient Executor (AC-32)
    # ------------------------------------------------------------------

    async def _patient_execute(
        self, decision: TradeDecision, approval: RiskApproval,
    ) -> TradeResult:
        """GTC + postOnly (메이커 전용) 주문.

        가격: best_bid + tick (BUY) 또는 best_ask - tick (SELL).
        """
        target_price = approval.target_price

        if self.dry_run:
            order_type = OrderType.POST_ONLY if self.patient_post_only else OrderType.GTC
            return self._create_dry_run_result(
                decision, approval, target_price, ExecutorMode.PATIENT, order_type,
            )

        # 실제 주문
        order_type = OrderType.POST_ONLY if self.patient_post_only else OrderType.GTC
        order_id = None
        status = TradeStatus.REJECTED
        executed_price = target_price

        try:
            if self.clob_client is not None:
                order_result = await self.clob_client.post_order(
                    token_id=decision.token_id,
                    side=decision.side.value,
                    price=target_price,
                    size=approval.final_size_tokens,
                    order_type=order_type.value,
                )
                if order_result and order_result.get("orderID"):
                    order_id = order_result["orderID"]
                    status = TradeStatus.FILLED
                    executed_price = float(order_result.get("price", target_price))
        except Exception as e:
            logger.error("Patient execution failed: %s", e)

        return self._build_result(
            decision, approval, executed_price, ExecutorMode.PATIENT,
            order_type, order_id, status,
        )

    # ------------------------------------------------------------------
    # DRY_RUN 가상 체결 (AC-33)
    # ------------------------------------------------------------------

    def _create_dry_run_result(
        self,
        decision: TradeDecision,
        approval: RiskApproval,
        price: float,
        executor_mode: ExecutorMode,
        order_type: OrderType,
    ) -> TradeResult:
        """DRY_RUN 모드 가상 체결 기록."""
        logger.info(
            "[DRY_RUN] %s %s: market=%s tokens=%.4f price=%.4f cost=$%.2f",
            executor_mode.value, decision.side.value,
            decision.condition_id, approval.final_size_tokens,
            price, approval.final_size_usdc,
        )
        return self._build_result(
            decision, approval, price, executor_mode, order_type,
            order_id=None, status=TradeStatus.DRY_RUN,
        )

    # ------------------------------------------------------------------
    # 결과 빌더
    # ------------------------------------------------------------------

    def _build_result(
        self,
        decision: TradeDecision,
        approval: RiskApproval,
        price: float,
        executor_mode: ExecutorMode,
        order_type: OrderType,
        order_id: str | None,
        status: TradeStatus,
    ) -> TradeResult:
        """TradeResult를 조립한다."""
        fee_cost = 0.0
        for lr in approval.layer_results:
            if lr.name == "Kelly Sizer" and lr.adjusted_size:
                break  # fee_cost는 별도 계산

        return TradeResult(
            id=str(uuid.uuid4()),
            decision_id=decision.id,
            condition_id=decision.condition_id,
            token_id=decision.token_id,
            side=decision.side,
            price=round(price, 4),
            size_tokens=round(approval.final_size_tokens, 4),
            cost_usdc=round(approval.final_size_usdc, 2),
            order_type=order_type,
            executor_mode=executor_mode,
            reactor_source=decision.reactor_source,
            order_id=order_id,
            status=status,
            confidence=decision.confidence,
            convergence_count=decision.convergence_count,
            signals_used=decision.contributing_signals,
            risk_layers=approval.layer_results,
            golden_cross=decision.golden_cross,
            holding_cost=decision.holding_cost,
            fee_cost=fee_cost,
            is_dry_run=self.dry_run,
        )

    # ------------------------------------------------------------------
    # DB 기록
    # ------------------------------------------------------------------

    async def _record_trade(self, result: TradeResult) -> None:
        """거래 결과를 DB에 기록한다."""
        if self.db_manager is not None:
            try:
                await self.db_manager.record_trade(result)
            except Exception as e:
                logger.error("Failed to record trade to DB: %s", e)

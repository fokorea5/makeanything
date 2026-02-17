"""
OrderExecutor — 주문 실행 (드라이런/실거래).
DESIGN.md 섹션 6.2 기반.

드라이런: 로그 기록 + 가상 포지션 삽입만.
실거래: PolymarketClient를 통해 실제 주문 제출.

# @risk: 금융거래 — execute() 실거래 경로는 실제 USDC를 소비합니다.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from src.api.polymarket_client import PolymarketClient
from src.db.database import Database
from src.shared.types import (
    Direction,
    OrderResult,
    OrderStatus,
    OrderType,
    TokenSide,
    TradeDecision,
)

logger = logging.getLogger(__name__)


class OrderExecutor:
    """
    주문 실행기.
    dry_run=True: 가상 실행 (API 호출 없음).
    dry_run=False: PolymarketClient로 실제 주문.

    # @risk: 금융거래 — dry_run=False 경로에서 실제 자금이 사용됩니다.
    """

    def __init__(
        self,
        client: PolymarketClient,
        db: Database,
        dry_run: bool = True,
    ) -> None:
        self.client = client
        self.db = db
        self.dry_run = dry_run

        if not dry_run:
            logger.warning(
                "OrderExecutor: 실거래 모드 활성화. "
                "모든 주문은 실제 USDC를 소비합니다."
            )

    def execute(self, decision: TradeDecision) -> OrderResult:
        """
        거래 결정 실행.
        드라이런 → 가상 결과 반환 + DB 기록.
        실거래 → PolymarketClient 호출 + DB 기록.
        """
        if self.dry_run:
            return self._execute_dry(decision)
        else:
            return self._execute_live(decision)  # @risk: 금융거래

    # ----------------------------------------------------------------
    # 드라이런 실행
    # ----------------------------------------------------------------

    def _execute_dry(self, decision: TradeDecision) -> OrderResult:
        """가상 주문 — API 호출 없이 로그 및 DB만 기록."""
        dry_order_id = f"DRY-{uuid4().hex[:8].upper()}"

        # 현재 가격: suggested_price가 없으면 0.5 (미드포인트 근사)
        entry_price = decision.suggested_price or 0.5

        contributing = [s.strategy_name for s in decision.contributing_signals]

        result = OrderResult(
            success=True,
            order_id=dry_order_id,
            condition_id=decision.condition_id,
            token_id=decision.token_id,
            direction=decision.direction,
            token_side=decision.token_side,
            price=entry_price,
            size=decision.size,
            order_type=decision.order_type,
            status=OrderStatus.FILLED,   # 드라이런은 즉시 체결로 가정
            composite_score=decision.composite_score,
            contributing_strategies=contributing,
            dry_run=True,
        )

        # 가상 포지션 DB 기록
        try:
            self.db.insert_virtual_position(decision, entry_price)
        except Exception as exc:
            logger.error("가상 포지션 DB 기록 실패: %s", exc)

        # 거래 로그 DB 기록
        try:
            self.db.insert_trade_log(result)
        except Exception as exc:
            logger.error("드라이런 거래 로그 DB 기록 실패: %s", exc)

        logger.info(
            "[DRY-RUN] %s | %s %s @ %.3f | 크기=%.2f USD | 점수=%.2f | id=%s",
            decision.market_question[:40],
            decision.direction.value,
            decision.token_side.value,
            entry_price,
            decision.size,
            decision.composite_score,
            dry_order_id,
        )
        return result

    # ----------------------------------------------------------------
    # 실거래 실행
    # ----------------------------------------------------------------

    def _execute_live(self, decision: TradeDecision) -> OrderResult:
        """
        실제 주문 실행.
        # @risk: 금융거래 — PolymarketClient.place_limit_order() 호출.
        """
        price = decision.suggested_price
        if price is None:
            # 시장가 근사: midpoint 가져오기
            try:
                price = self.client.get_midpoint(decision.token_id)
            except Exception:
                price = 0.5

        # 가격 유효성 검사
        if not (0.01 <= price <= 0.99):
            logger.warning(
                "비정상 가격 %.3f → 주문 거부 (market=%s)",
                price, decision.condition_id[:8]
            )
            return self._failed_result(decision, price, "비정상 가격")

        contributing = [s.strategy_name for s in decision.contributing_signals]

        try:
            # @risk: 금융거래 — 실제 주문 제출
            result = self.client.place_limit_order(
                token_id=decision.token_id,
                side=decision.direction,
                price=price,
                size=decision.size,
                order_type=decision.order_type,
            )

            # 메타데이터 보강
            result.condition_id = decision.condition_id
            result.composite_score = decision.composite_score
            result.contributing_strategies = contributing
            result.token_side = decision.token_side

            # DB 기록
            try:
                self.db.insert_trade_log(result)
            except Exception as exc:
                logger.error("실거래 로그 DB 기록 실패: %s", exc)

            if result.success:
                logger.info(
                    "[LIVE] %s | %s %s @ %.3f | 크기=%.2f USD | 점수=%.2f | id=%s",
                    decision.market_question[:40],
                    decision.direction.value,
                    decision.token_side.value,
                    price,
                    decision.size,
                    decision.composite_score,
                    result.order_id,
                )
            else:
                logger.error(
                    "[LIVE] 주문 실패: %s | 오류=%s",
                    decision.market_question[:40], result.error_message
                )

            return result

        except Exception as exc:
            logger.error("_execute_live 예외: %s", exc, exc_info=True)
            return self._failed_result(decision, price, str(exc))

    def _failed_result(
        self, decision: TradeDecision, price: float, error: str
    ) -> OrderResult:
        contributing = [s.strategy_name for s in decision.contributing_signals]
        result = OrderResult(
            success=False,
            order_id="",
            condition_id=decision.condition_id,
            token_id=decision.token_id,
            direction=decision.direction,
            token_side=decision.token_side,
            price=price,
            size=decision.size,
            order_type=decision.order_type,
            status=OrderStatus.FAILED,
            composite_score=decision.composite_score,
            contributing_strategies=contributing,
            dry_run=self.dry_run,
            error_message=error,
        )
        try:
            self.db.insert_trade_log(result)
        except Exception as exc:
            logger.error("실패 로그 DB 기록 실패: %s", exc)
        return result

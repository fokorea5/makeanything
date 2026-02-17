"""
Risk Sentinel -- 5층 방어 (DESIGN.md 3.9절, 6절, AC-23~27, AC-41, AC-42).

Layer 1: Kelly Sizer (Fractional Kelly 0.4 x Governor배수 x GoldenCross - 유지비용 - 실행비용)
Layer 2: Single Market Cap (15%)
Layer 3: Total Exposure Cap (60%)
Layer 4: Circuit Breaker (8% 일일 손실)
Layer 5: DD Throttle (5%/10%/15%)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from config import Config
from src.shared.types import (
    TradeDecision,
    RiskApproval,
    RiskLayerResult,
    RiskRejectReason,
    RiskCheck,
    HoldingCost,
    ExecutionFilter,
    OrderType,
    SignalUrgency,
    ExecutorMode,
)

logger = logging.getLogger("reaper.core.risk_sentinel")


class RiskSentinel:
    """Risk Sentinel: 5층 리스크 방어.

    TradeDecision이 5개의 레이어를 순서대로 통과해야 한다.
    하나라도 거부하면 거래가 차단된다.
    """

    def __init__(
        self,
        config: Config,
        frequency_governor: Any = None,
        portfolio_tracker: Any = None,
        clob_client: Any = None,
    ) -> None:
        self.config = config
        self.frequency_governor = frequency_governor
        self.portfolio_tracker = portfolio_tracker
        self.clob_client = clob_client

        # Risk 파라미터
        self.kelly_fraction: float = getattr(config, "KELLY_FRACTION", 0.4)
        self.max_single_market: float = getattr(config, "MAX_SINGLE_MARKET", 0.15)
        self.max_total_exposure: float = getattr(config, "MAX_TOTAL_EXPOSURE", 0.60)
        self.daily_loss_limit: float = getattr(config, "DAILY_LOSS_LIMIT", 0.08)
        self.dd_throttle_5: float = getattr(config, "DD_THROTTLE_5", 0.05)
        self.dd_throttle_10: float = getattr(config, "DD_THROTTLE_10", 0.10)
        self.dd_halt_15: float = getattr(config, "DD_HALT_15", 0.15)

        # 유지비용 파라미터 (AC-41)
        self.risk_free_rate: float = getattr(config, "RISK_FREE_RATE", 0.05)

        # 실행 비용 파라미터 (AC-42)
        self.min_profit_threshold: float = getattr(config, "MIN_PROFIT_THRESHOLD", 0.50)

        # Golden Cross 배수
        self.golden_cross_kelly_mult: float = getattr(
            config, "META_GOLDEN_CROSS_KELLY_MULT", 1.5
        )

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        decision: TradeDecision,
        risk_check: RiskCheck,
        market_end_date: str | None = None,
        market_fee_bps: float = 0.0,
        market_min_order: float = 5.0,
        market_min_tick: float = 0.01,
    ) -> RiskApproval:
        """TradeDecision을 5층 리스크 레이어로 평가한다.

        Args:
            decision: Meta Brain이 생성한 거래 결정.
            risk_check: 현재 리스크 상태 스냅샷.
            market_end_date: 마켓 결제일 (ISO 8601 문자열).
            market_fee_bps: 마켓 수수료율 (basis points).
            market_min_order: 최소 주문 크기 (USDC).
            market_min_tick: 최소 틱 사이즈.

        Returns:
            RiskApproval 결과.
        """
        layer_results: list[RiskLayerResult] = []
        bankroll = risk_check.bankroll

        if bankroll <= 0:
            return self._reject(
                decision, layer_results, RiskRejectReason.KELLY_ZERO,
                "Zero bankroll",
            )

        # ── Layer 4: Circuit Breaker (먼저 체크, 전면 중단 조건) ──
        l4_result = self._layer4_circuit_breaker(risk_check, bankroll)
        layer_results.append(l4_result)
        if not l4_result.passed:
            return self._reject(
                decision, layer_results, RiskRejectReason.CIRCUIT_BREAKER,
                l4_result.detail,
            )

        # ── Layer 1: Kelly Sizer + 유지비용 + 실행비용 ──
        l1_result, size_usdc, holding_cost_obj, exec_filter = await self._layer1_kelly_sizer(
            decision, risk_check, bankroll, market_end_date, market_fee_bps, market_min_order,
        )
        layer_results.append(l1_result)
        if not l1_result.passed:
            reason = RiskRejectReason.KELLY_ZERO
            if holding_cost_obj and not holding_cost_obj.edge_sufficient:
                reason = RiskRejectReason.HOLDING_COST
            elif exec_filter and not exec_filter.passes:
                reason = RiskRejectReason.EXECUTION_COST
            return self._reject(decision, layer_results, reason, l1_result.detail)

        # ── Layer 5: DD Throttle (사이즈 조정) ──
        l5_result, size_usdc = self._layer5_dd_throttle(
            risk_check, size_usdc,
        )
        layer_results.append(l5_result)
        if not l5_result.passed:
            return self._reject(
                decision, layer_results, RiskRejectReason.DRAWDOWN_HALT,
                l5_result.detail,
            )

        # ── Layer 2: Single Market Cap ──
        l2_result, size_usdc = self._layer2_single_market(
            decision, risk_check, bankroll, size_usdc,
        )
        layer_results.append(l2_result)
        if not l2_result.passed:
            return self._reject(
                decision, layer_results, RiskRejectReason.SINGLE_MARKET_LIMIT,
                l2_result.detail,
            )

        # ── Layer 3: Total Exposure Cap ──
        l3_result, size_usdc = self._layer3_total_exposure(
            risk_check, bankroll, size_usdc,
        )
        layer_results.append(l3_result)
        if not l3_result.passed:
            return self._reject(
                decision, layer_results, RiskRejectReason.TOTAL_EXPOSURE_LIMIT,
                l3_result.detail,
            )

        # 최소 주문 크기 체크
        if size_usdc < market_min_order:
            return self._reject(
                decision, layer_results, RiskRejectReason.KELLY_ZERO,
                f"Size {size_usdc:.2f} below minimum {market_min_order:.2f}",
            )

        # 주문 유형 결정
        if decision.executor_mode == ExecutorMode.SNIPER:
            order_type = OrderType.FOK
        else:
            order_type = OrderType.GTC

        # 토큰 수량 계산
        target_price = decision.price_at_decision
        if target_price <= 0:
            target_price = 0.50
        size_tokens = size_usdc / target_price

        # 유지비용 기록
        holding_cost_value = holding_cost_obj.holding_cost_rate if holding_cost_obj else 0.0
        decision.holding_cost = holding_cost_value

        logger.info(
            "Risk APPROVED: market=%s size=$%.2f tokens=%.2f layers=%d",
            decision.condition_id, size_usdc, size_tokens, len(layer_results),
        )

        return RiskApproval(
            approved=True,
            decision_id=decision.id,
            final_size_usdc=round(size_usdc, 2),
            final_size_tokens=round(size_tokens, 4),
            target_price=round(target_price, 4),
            order_type=order_type,
            layer_results=layer_results,
            reject_reason=None,
        )

    # ------------------------------------------------------------------
    # Layer 1: Kelly Sizer + 유지비용(AC-41) + 실행비용(AC-42)
    # ------------------------------------------------------------------

    async def _layer1_kelly_sizer(
        self,
        decision: TradeDecision,
        risk_check: RiskCheck,
        bankroll: float,
        market_end_date: str | None,
        market_fee_bps: float,
        market_min_order: float,
    ) -> tuple[RiskLayerResult, float, HoldingCost | None, ExecutionFilter | None]:
        """Layer 1: Kelly Sizer.

        Fractional Kelly 0.4 x Governor배수 x Golden Cross배수 - 유지비용.
        """
        confidence = decision.confidence
        price = decision.price_at_decision
        if price <= 0 or price >= 1.0:
            price = 0.50

        # 기본 edge 계산
        edge = confidence - (1 - confidence)  # = 2*confidence - 1
        odds = (1.0 / price) - 1.0

        if odds <= 0:
            return (
                RiskLayerResult(layer=1, name="Kelly Sizer", passed=False, detail="Invalid odds"),
                0.0, None, None,
            )

        # Kelly 공식
        kelly_pct = self.kelly_fraction * (edge * odds - (1 - edge)) / odds

        # Governor 배수 적용 (AC-23)
        governor_mult = 0.7  # NORMAL 기본값
        if self.frequency_governor is not None:
            governor_mult = self.frequency_governor.get_kelly_multiplier()
        kelly_pct *= governor_mult

        # Golden Cross 증폭 (AC-21)
        if decision.golden_cross:
            kelly_pct *= self.golden_cross_kelly_mult

        # 유지비용 차감 (AC-41)
        holding_cost_obj: HoldingCost | None = None
        if market_end_date:
            holding_cost_obj = self._compute_holding_cost(edge, market_end_date)
            if not holding_cost_obj.edge_sufficient:
                return (
                    RiskLayerResult(
                        layer=1, name="Kelly Sizer", passed=False,
                        detail=f"Holding cost ({holding_cost_obj.holding_cost_rate:.4f}) exceeds edge ({edge:.4f})",
                    ),
                    0.0, holding_cost_obj, None,
                )
            # adjusted_edge로 Kelly 재계산
            adjusted_edge = holding_cost_obj.adjusted_edge
            kelly_pct = self.kelly_fraction * (adjusted_edge * odds - (1 - adjusted_edge)) / odds
            kelly_pct *= governor_mult
            if decision.golden_cross:
                kelly_pct *= self.golden_cross_kelly_mult

        if kelly_pct <= 0:
            return (
                RiskLayerResult(layer=1, name="Kelly Sizer", passed=False, detail="Kelly <= 0"),
                0.0, holding_cost_obj, None,
            )

        # 포지션 크기 산출
        size_usdc = max(0.0, kelly_pct) * bankroll
        size_usdc = max(size_usdc, market_min_order)

        # 실행 비용 필터 (AC-42)
        adjusted_edge_final = holding_cost_obj.adjusted_edge if holding_cost_obj else edge
        exec_filter = self._compute_execution_filter(
            size_usdc, adjusted_edge_final, market_fee_bps, price,
        )

        if not exec_filter.passes:
            return (
                RiskLayerResult(
                    layer=1, name="Kelly Sizer", passed=False,
                    detail=f"Execution cost filter: net profit ${exec_filter.net_profit:.2f} < ${self.min_profit_threshold:.2f}",
                ),
                0.0, holding_cost_obj, exec_filter,
            )

        return (
            RiskLayerResult(
                layer=1, name="Kelly Sizer", passed=True,
                detail=f"Kelly={kelly_pct:.4f} size=${size_usdc:.2f} gov_mult={governor_mult}",
                adjusted_size=size_usdc,
            ),
            size_usdc, holding_cost_obj, exec_filter,
        )

    def _compute_holding_cost(self, raw_edge: float, end_date_str: str) -> HoldingCost:
        """유지비용을 계산한다 (AC-41)."""
        try:
            # ISO 8601 파싱 (다양한 형식 대응)
            end_date_str_clean = end_date_str.replace("Z", "+00:00")
            if "T" in end_date_str_clean:
                end_date = datetime.fromisoformat(end_date_str_clean)
            else:
                end_date = datetime.fromisoformat(end_date_str_clean + "T00:00:00+00:00")
            now = datetime.utcnow()
            days_to_settlement = max(0, (end_date.replace(tzinfo=None) - now).days)
        except (ValueError, TypeError):
            days_to_settlement = 30  # 파싱 실패 시 보수적 추정

        holding_cost_rate = days_to_settlement / 365.0 * self.risk_free_rate
        adjusted_edge = raw_edge - holding_cost_rate
        edge_sufficient = adjusted_edge > 0

        return HoldingCost(
            days_to_settlement=days_to_settlement,
            risk_free_rate=self.risk_free_rate,
            holding_cost_rate=round(holding_cost_rate, 6),
            raw_edge=round(raw_edge, 6),
            adjusted_edge=round(adjusted_edge, 6),
            edge_sufficient=edge_sufficient,
        )

    def _compute_execution_filter(
        self,
        size_usdc: float,
        adjusted_edge: float,
        fee_rate_bps: float,
        price: float,
    ) -> ExecutionFilter:
        """실행 비용 필터를 계산한다 (AC-42)."""
        expected_profit = size_usdc * adjusted_edge
        fee_cost = fee_rate_bps / 10000.0 * min(price, 1.0 - price) * size_usdc
        net_profit = expected_profit - fee_cost
        passes = net_profit >= self.min_profit_threshold

        return ExecutionFilter(
            size_usdc=round(size_usdc, 2),
            adjusted_edge=round(adjusted_edge, 6),
            expected_profit=round(expected_profit, 4),
            fee_rate_bps=fee_rate_bps,
            fee_cost=round(fee_cost, 4),
            net_profit=round(net_profit, 4),
            min_profit_threshold=self.min_profit_threshold,
            passes=passes,
        )

    # ------------------------------------------------------------------
    # Layer 2: Single Market Cap (AC-24)
    # ------------------------------------------------------------------

    def _layer2_single_market(
        self,
        decision: TradeDecision,
        risk_check: RiskCheck,
        bankroll: float,
        size_usdc: float,
    ) -> tuple[RiskLayerResult, float]:
        """단일 마켓 <= bankroll x 0.15."""
        max_size = bankroll * self.max_single_market
        existing_exposure = risk_check.market_exposures.get(decision.condition_id, 0.0)
        total_market = existing_exposure + size_usdc

        if total_market > max_size:
            allowed = max(0.0, max_size - existing_exposure)
            if allowed <= 0:
                return (
                    RiskLayerResult(
                        layer=2, name="Single Market Cap", passed=False,
                        detail=f"Market exposure ${total_market:.2f} > cap ${max_size:.2f}",
                    ),
                    0.0,
                )
            size_usdc = allowed

        return (
            RiskLayerResult(
                layer=2, name="Single Market Cap", passed=True,
                detail=f"Market exposure ${existing_exposure + size_usdc:.2f} / ${max_size:.2f}",
                adjusted_size=size_usdc,
            ),
            size_usdc,
        )

    # ------------------------------------------------------------------
    # Layer 3: Total Exposure Cap (AC-25)
    # ------------------------------------------------------------------

    def _layer3_total_exposure(
        self,
        risk_check: RiskCheck,
        bankroll: float,
        size_usdc: float,
    ) -> tuple[RiskLayerResult, float]:
        """전체 <= bankroll x 0.60."""
        max_exposure = bankroll * self.max_total_exposure
        total_after = risk_check.total_exposure + size_usdc

        if total_after > max_exposure:
            allowed = max(0.0, max_exposure - risk_check.total_exposure)
            if allowed <= 0:
                return (
                    RiskLayerResult(
                        layer=3, name="Total Exposure Cap", passed=False,
                        detail=f"Total exposure ${total_after:.2f} > cap ${max_exposure:.2f}",
                    ),
                    0.0,
                )
            size_usdc = allowed

        return (
            RiskLayerResult(
                layer=3, name="Total Exposure Cap", passed=True,
                detail=f"Total exposure ${risk_check.total_exposure + size_usdc:.2f} / ${max_exposure:.2f}",
                adjusted_size=size_usdc,
            ),
            size_usdc,
        )

    # ------------------------------------------------------------------
    # Layer 4: Circuit Breaker (AC-26)
    # ------------------------------------------------------------------

    def _layer4_circuit_breaker(
        self, risk_check: RiskCheck, bankroll: float,
    ) -> RiskLayerResult:
        """일일 손실 >= bankroll x 0.08 → 당일 거래 전면 중단."""
        if risk_check.circuit_breaker_active:
            return RiskLayerResult(
                layer=4, name="Circuit Breaker", passed=False,
                detail="Circuit breaker already active",
            )

        loss_limit = bankroll * self.daily_loss_limit
        daily_loss = abs(risk_check.daily_pnl) if risk_check.daily_pnl < 0 else 0.0

        if daily_loss >= loss_limit:
            logger.warning(
                "CIRCUIT BREAKER: daily loss $%.2f >= limit $%.2f",
                daily_loss, loss_limit,
            )
            return RiskLayerResult(
                layer=4, name="Circuit Breaker", passed=False,
                detail=f"Daily loss ${daily_loss:.2f} >= limit ${loss_limit:.2f}",
            )

        return RiskLayerResult(
            layer=4, name="Circuit Breaker", passed=True,
            detail=f"Daily loss ${daily_loss:.2f} / limit ${loss_limit:.2f}",
        )

    # ------------------------------------------------------------------
    # Layer 5: DD Throttle (AC-27)
    # ------------------------------------------------------------------

    def _layer5_dd_throttle(
        self, risk_check: RiskCheck, size_usdc: float,
    ) -> tuple[RiskLayerResult, float]:
        """DD >5%: x0.5, >10%: x0.25, >15%: 전면 중단.

        Governor의 DD 임계값과 독립 작동, 곱셈 중첩.
        """
        dd = risk_check.current_drawdown

        if dd >= self.dd_halt_15:
            logger.warning("DD HALT: drawdown %.2f%% >= 15%%", dd * 100)
            return (
                RiskLayerResult(
                    layer=5, name="DD Throttle", passed=False,
                    detail=f"DD {dd:.2%} >= halt threshold {self.dd_halt_15:.2%}",
                ),
                0.0,
            )

        multiplier = 1.0
        if dd >= self.dd_throttle_10:
            multiplier = 0.25
        elif dd >= self.dd_throttle_5:
            multiplier = 0.5

        adjusted_size = size_usdc * multiplier

        return (
            RiskLayerResult(
                layer=5, name="DD Throttle", passed=True,
                detail=f"DD {dd:.2%} → multiplier {multiplier} → size ${adjusted_size:.2f}",
                adjusted_size=adjusted_size,
            ),
            adjusted_size,
        )

    # ------------------------------------------------------------------
    # 헬퍼
    # ------------------------------------------------------------------

    def _reject(
        self,
        decision: TradeDecision,
        layer_results: list[RiskLayerResult],
        reason: RiskRejectReason,
        detail: str,
    ) -> RiskApproval:
        """거부 RiskApproval을 생성한다."""
        logger.info(
            "Risk REJECTED: market=%s reason=%s detail=%s",
            decision.condition_id, reason.value, detail,
        )
        return RiskApproval(
            approved=False,
            decision_id=decision.id,
            final_size_usdc=0.0,
            final_size_tokens=0.0,
            target_price=decision.price_at_decision,
            order_type=OrderType.GTC,
            layer_results=layer_results,
            reject_reason=reason,
        )

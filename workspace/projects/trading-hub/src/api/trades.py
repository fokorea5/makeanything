"""
Trading Hub — 거래 라우터

POST /api/trades — 거래 기록 저장
GET  /api/trades — 거래 목록 (필터, 페이지네이션)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.db import database as db
from src.shared.types import (
    TradeCreateRequest,
    TradeListResponse,
    TradeResponse,
    TradeSide,
    ExchangeType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trades", tags=["trades"])


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post("", response_model=TradeResponse, status_code=201)
async def create_trade(request: TradeCreateRequest) -> TradeResponse:
    """거래 기록을 저장한다."""
    # 입력 검증: 봇 존재 확인
    bot = await db.get_bot(request.bot_id)
    if bot is None:
        raise HTTPException(
            status_code=404,
            detail=f"봇 {request.bot_id}을(를) 찾을 수 없습니다.",
        )

    # 입력 검증: 가격, 수량, 총액 관계 확인
    expected_total = round(request.price * request.quantity, 2)
    if abs(request.total - expected_total) > expected_total * 0.01:
        # 1% 이상 차이나면 경고 (슬리피지 허용)
        logger.warning(
            "Trade total mismatch: expected %.2f, got %.2f",
            expected_total,
            request.total,
        )

    timestamp_str = None
    if request.timestamp:
        timestamp_str = request.timestamp.isoformat()

    row = await db.create_trade(
        bot_id=request.bot_id,
        exchange=request.exchange.value,
        symbol=request.symbol,
        side=request.side.value,
        price=request.price,
        quantity=request.quantity,
        total=request.total,
        fee=request.fee,
        timestamp=timestamp_str,
    )

    resp = TradeResponse(
        id=row["id"],
        bot_id=row["bot_id"],
        exchange=ExchangeType(row["exchange"]),
        symbol=row["symbol"],
        side=TradeSide(row["side"]),
        price=row["price"],
        quantity=row["quantity"],
        total=row["total"],
        fee=row["fee"],
        timestamp=row["timestamp"],
    )

    logger.info(
        "Trade recorded: bot=%d %s %s %.8f @ %.2f",
        resp.bot_id,
        resp.side.value,
        resp.symbol,
        resp.quantity,
        resp.price,
    )
    return resp


@router.get("", response_model=TradeListResponse)
async def list_trades(
    bot_id: Optional[int] = Query(default=None, description="봇 ID로 필터"),
    symbol: Optional[str] = Query(default=None, description="심볼로 필터"),
    side: Optional[str] = Query(default=None, description="buy 또는 sell"),
    start_date: Optional[str] = Query(default=None, description="시작일 (ISO 형식)"),
    end_date: Optional[str] = Query(default=None, description="종료일 (ISO 형식)"),
    page: int = Query(default=1, ge=1, description="페이지 번호 (1-based)"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
) -> TradeListResponse:
    """거래 목록을 조회한다. 필터와 페이지네이션 지원."""
    # side 검증
    if side is not None and side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side는 'buy' 또는 'sell'이어야 합니다.")

    result = await db.get_trades(
        bot_id=bot_id,
        symbol=symbol,
        side=side,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
    )

    items = []
    for row in result["items"]:
        items.append(
            TradeResponse(
                id=row["id"],
                bot_id=row["bot_id"],
                exchange=ExchangeType(row["exchange"]),
                symbol=row["symbol"],
                side=TradeSide(row["side"]),
                price=row["price"],
                quantity=row["quantity"],
                total=row["total"],
                fee=row["fee"],
                timestamp=row["timestamp"],
            )
        )

    return TradeListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        pages=result["pages"],
    )

"""
Trading Hub — 공유 타입 정의

모든 API 요청/응답 스키마와 공유 enum/모델을 정의한다.
개발자는 이 파일을 import하여 사용하되, 수정은 설계자만 한다.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class BotStatus(str, Enum):
    """봇 상태"""
    idle = "idle"
    running = "running"
    stopped = "stopped"
    error = "error"


class ExchangeType(str, Enum):
    """지원 거래소"""
    upbit = "upbit"
    binance = "binance"
    simulation = "simulation"


class TradeSide(str, Enum):
    """거래 방향"""
    buy = "buy"
    sell = "sell"


class AlertType(str, Enum):
    """알림 유형"""
    error = "error"
    large_trade = "large_trade"
    daily_profit = "daily_profit"


# ──────────────────────────────────────────────
# Bot 관련 스키마
# ──────────────────────────────────────────────

class BotConfig(BaseModel):
    """봇 설정 (JSON으로 DB에 저장)"""
    symbol: str = Field(default="BTC/KRW", description="거래 심볼")
    strategy: str = Field(default="simple_ma", description="전략 이름")
    interval: int = Field(default=10, description="tick 간격 (초)")
    params: Dict[str, Any] = Field(default_factory=dict, description="전략별 추가 파라미터")


class BotCreateRequest(BaseModel):
    """POST /api/bots 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="봇 이름")
    exchange: ExchangeType = Field(..., description="거래소")
    type: str = Field(default="custom", max_length=30, description="봇 유형 (grid, dca, custom 등)")
    config: BotConfig = Field(default_factory=BotConfig, description="봇 설정")
    api_key: Optional[str] = Field(default=None, description="거래소 API Key (암호화 전)")
    api_secret: Optional[str] = Field(default=None, description="거래소 API Secret (암호화 전)")


class BotResponse(BaseModel):
    """봇 정보 응답 (API 키는 절대 포함하지 않음)"""
    id: int
    name: str
    exchange: ExchangeType
    type: str
    status: BotStatus
    config: BotConfig
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BotStatusResponse(BaseModel):
    """봇 상태 상세 응답"""
    id: int
    name: str
    status: BotStatus
    exchange: ExchangeType
    uptime_seconds: Optional[float] = Field(default=None, description="실행 시간 (초)")
    last_tick_at: Optional[datetime] = Field(default=None, description="마지막 tick 시각")
    error_message: Optional[str] = Field(default=None, description="에러 메시지 (status가 error일 때)")


# ──────────────────────────────────────────────
# Asset 관련 스키마
# ──────────────────────────────────────────────

class AssetResponse(BaseModel):
    """개별 자산 항목"""
    id: int
    bot_id: int
    bot_name: Optional[str] = None
    currency: str
    balance: float
    locked: float
    value_usd: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetSummaryResponse(BaseModel):
    """전체 자산 요약"""
    total_value_usd: float = Field(description="전체 자산 USD 환산 합계")
    bot_count: int = Field(description="등록된 봇 수")
    assets_by_currency: Dict[str, float] = Field(
        default_factory=dict,
        description="통화별 합산 가치 (USD)"
    )
    assets_by_bot: List[BotAssetSummary] = Field(
        default_factory=list,
        description="봇별 자산 요약"
    )


class BotAssetSummary(BaseModel):
    """봇별 자산 요약 (AssetSummaryResponse 내부)"""
    bot_id: int
    bot_name: str
    total_value_usd: float
    currencies: List[str]


# AssetSummaryResponse의 forward reference 해소
AssetSummaryResponse.model_rebuild()


# ──────────────────────────────────────────────
# Trade 관련 스키마
# ──────────────────────────────────────────────

class TradeCreateRequest(BaseModel):
    """POST /api/trades 요청"""
    bot_id: int = Field(..., description="봇 ID")
    exchange: ExchangeType = Field(..., description="거래소")
    symbol: str = Field(..., description="거래 심볼")
    side: TradeSide = Field(..., description="buy 또는 sell")
    price: float = Field(..., gt=0, description="체결 가격")
    quantity: float = Field(..., gt=0, description="수량")
    total: float = Field(..., gt=0, description="총액")
    fee: float = Field(default=0.0, ge=0, description="수수료")
    timestamp: Optional[datetime] = Field(default=None, description="체결 시각 (없으면 현재)")


class TradeResponse(BaseModel):
    """거래 기록 응답"""
    id: int
    bot_id: int
    exchange: ExchangeType
    symbol: str
    side: TradeSide
    price: float
    quantity: float
    total: float
    fee: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class TradeListResponse(BaseModel):
    """거래 목록 (페이지네이션 포함)"""
    items: List[TradeResponse]
    total: int = Field(description="전체 거래 수")
    page: int = Field(description="현재 페이지 (1-based)")
    size: int = Field(description="페이지 크기")
    pages: int = Field(description="전체 페이지 수")


# ──────────────────────────────────────────────
# Alert 관련 스키마
# ──────────────────────────────────────────────

class AlertTestRequest(BaseModel):
    """POST /api/alerts/test 요청"""
    message: Optional[str] = Field(
        default="Trading Hub 알림 테스트",
        description="테스트 메시지"
    )


class AlertResponse(BaseModel):
    """알림 항목 응답"""
    id: int
    bot_id: Optional[int]
    type: AlertType
    message: str
    sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """알림 목록 (페이지네이션 포함)"""
    items: List[AlertResponse]
    total: int
    page: int
    size: int
    pages: int


# ──────────────────────────────────────────────
# WebSocket 스키마
# ──────────────────────────────────────────────

class WsBotStatus(BaseModel):
    """WebSocket 메시지 내 개별 봇 상태"""
    bot_id: int
    name: str
    status: BotStatus
    exchange: ExchangeType
    last_tick_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WsStatusMessage(BaseModel):
    """WebSocket /ws/status 메시지"""
    type: str = Field(default="status_update", description="메시지 타입")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    bots: List[WsBotStatus]


# ──────────────────────────────────────────────
# Bot Framework 내부 타입
# (ExchangeAdapter가 반환하는 값)
# ──────────────────────────────────────────────

class AssetInfo(BaseModel):
    """거래소 잔고 항목 (ExchangeAdapter 반환용)"""
    currency: str
    balance: float
    locked: float


class TickerInfo(BaseModel):
    """시세 정보 (ExchangeAdapter 반환용)"""
    symbol: str
    price: float
    volume_24h: Optional[float] = None
    change_24h: Optional[float] = None


class OrderResult(BaseModel):
    """주문 결과 (ExchangeAdapter 반환용)"""
    order_id: str
    symbol: str
    side: TradeSide
    price: float
    quantity: float
    total: float
    fee: float
    status: str = Field(default="filled", description="filled, pending, cancelled")


# ──────────────────────────────────────────────
# 공통 응답
# ──────────────────────────────────────────────

class OkResponse(BaseModel):
    """성공 응답"""
    ok: bool = True
    message: str = "success"


class ErrorResponse(BaseModel):
    """에러 응답"""
    ok: bool = False
    error: str
    detail: Optional[str] = None

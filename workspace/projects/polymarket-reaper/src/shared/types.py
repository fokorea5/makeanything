"""
Polymarket Reaper Bot v1.0 — Shared Types

이 파일은 모든 모듈이 공유하는 데이터 타입을 정의합니다.
설계자(Architect)만 수정 가능. 개발자는 읽기 전용.

Signal Flow: Signal → TradeDecision → RiskApproval → TradeResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Any


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class StrategyType(str, Enum):
    """10개 전략 식별자. DB 저장 시 .value(문자열) 사용."""
    AMBIGUITY = "ambiguity"
    ORACLE_FEAR = "oracle_fear"
    CONTRARIAN = "contrarian"
    CORRELATED = "correlated"
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    META_BRAIN = "meta_brain"
    SETTLEMENT_DECAY = "settlement_decay"
    EVENT_CASCADE = "event_cascade"
    MAKER_REBATE = "maker_rebate"
    WHALE_SHADOW = "whale_shadow"


class SignalUrgency(IntEnum):
    """시그널 우선순위. 낮을수록 Priority Queue에서 먼저 처리."""
    CRITICAL = 1   # 즉시 체결 필요 (Whale Shadow, Liquidity Vacuum)
    HIGH = 2       # 높은 확신 시그널
    MEDIUM = 3     # 표준 시그널
    LOW = 4        # 낮은 확신, 리베이트 수확 등


class ExecutorMode(str, Enum):
    """Dual Executor 모드."""
    SNIPER = "SNIPER"     # FOK/FAK — 즉시 체결
    PATIENT = "PATIENT"   # GTC/postOnly — 오더북 대기


class OrderSide(str, Enum):
    """주문 방향."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Polymarket 주문 유형."""
    GTC = "GTC"           # Good-Til-Cancelled
    GTD = "GTD"           # Good-Til-Date
    FOK = "FOK"           # Fill-Or-Kill
    FAK = "FAK"           # Fill-And-Kill
    POST_ONLY = "postOnly"  # Maker 전용


class TradeStatus(str, Enum):
    """거래 체결 상태."""
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    DRY_RUN = "DRY_RUN"


class RiskRejectReason(str, Enum):
    """Risk Sentinel 거부 사유."""
    KELLY_ZERO = "kelly_zero"                    # Kelly 사이징 결과 0
    SINGLE_MARKET_LIMIT = "single_market_limit"  # 단일 마켓 15% 초과
    TOTAL_EXPOSURE_LIMIT = "total_exposure_limit" # 총 노출 60% 초과
    CIRCUIT_BREAKER = "circuit_breaker"          # 일일 손실 8% 서킷브레이커
    DRAWDOWN_HALT = "drawdown_halt"              # DD > 15% 전면 중단
    CORRELATION_LIMIT = "correlation_limit"      # 상관 그룹 한도 초과


# ─────────────────────────────────────────────
# Market Data Types
# ─────────────────────────────────────────────

@dataclass
class PricePoint:
    """가격 히스토리 단일 포인트."""
    timestamp: int     # Unix timestamp
    price: float


@dataclass
class OrderBookLevel:
    """오더북 단일 호가 단계."""
    price: float
    size: float


@dataclass
class OrderBookSnapshot:
    """오더북 스냅샷."""
    market: str                   # condition_id
    asset_id: str                 # token_id
    bids: list[OrderBookLevel]    # 매수 호가 (높은 가격 순)
    asks: list[OrderBookLevel]    # 매도 호가 (낮은 가격 순)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None

    @property
    def mid(self) -> float | None:
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None


@dataclass
class TokenInfo:
    """마켓 내 아웃컴 토큰 정보."""
    token_id: str
    outcome: str       # "Yes" | "No"


@dataclass
class TagInfo:
    """마켓 태그 정보."""
    id: int
    label: str


@dataclass
class MarketData:
    """통합 마켓 데이터 (Gamma + CLOB 정보 합산).

    Market Data Cache에 저장되며, 모든 전략이 이 타입을 입력으로 받음.
    """
    # 식별자
    condition_id: str              # Polymarket condition ID
    question_id: str               # question ID (CLOB)
    tokens: list[TokenInfo]        # YES/NO 토큰 정보

    # Gamma 메타데이터
    question: str                  # 마켓 질문 텍스트
    description: str               # 마켓 설명
    slug: str                      # URL slug
    resolution_source: str         # 해결 기준 소스 URL
    end_date: str                  # 결제일 ISO 8601
    start_date: str                # 시작일
    category: str                  # 카테고리
    tags: list[TagInfo]            # 태그 목록
    active: bool
    closed: bool

    # Gamma 이벤트 정보
    event_id: str | None = None    # 소속 이벤트 ID (있으면)

    # 가격 정보 (CLOB에서 갱신)
    yes_price: float = 0.0         # YES 토큰 mid price
    no_price: float = 0.0          # NO 토큰 mid price
    volume: float = 0.0            # 총 거래량 (USDC)
    liquidity: float = 0.0         # 유동성

    # 수수료
    fee_rate_bps: float = 0.0      # 수수료율 (basis points)
    minimum_order_size: float = 5.0
    minimum_tick_size: float = 0.01

    # 오더북 (실시간 업데이트)
    orderbook: OrderBookSnapshot | None = None

    # 가격 히스토리 (전략 analyze 시 로드)
    prices_history: list[PricePoint] = field(default_factory=list)

    # negRisk (Gamma)
    neg_risk: bool = False
    neg_risk_market_id: str = ""

    # 캐시 메타
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def yes_token_id(self) -> str | None:
        for t in self.tokens:
            if t.outcome == "Yes":
                return t.token_id
        return None

    @property
    def no_token_id(self) -> str | None:
        for t in self.tokens:
            if t.outcome == "No":
                return t.token_id
        return None


@dataclass
class GammaMarket:
    """Gamma API 마켓 응답을 그대로 매핑한 타입."""
    id: int
    question: str
    condition_id: str
    slug: str
    resolution_source: str
    end_date: str
    start_date: str
    description: str
    outcomes: str                   # JSON 문자열: '["Yes","No"]'
    outcome_prices: str             # JSON 문자열: '["0.55","0.45"]'
    volume: str
    liquidity: str
    active: bool
    closed: bool
    tags: list[TagInfo]
    neg_risk: bool = False
    neg_risk_market_id: str = ""
    image: str = ""
    icon: str = ""


@dataclass
class GammaEvent:
    """Gamma API 이벤트 응답."""
    id: int | str
    title: str
    markets: list[str]              # condition_id 리스트


@dataclass
class GammaTag:
    """Gamma API 태그 응답."""
    id: int
    label: str
    slug: str = ""


@dataclass
class PositionData:
    """Data API 포지션 응답."""
    condition_id: str
    asset: str                      # token_id
    outcome: str                    # "Yes" | "No"
    size: float                     # 보유 수량
    avg_price: float                # 평균 매입가
    current_price: float            # 현재 가격
    initial_value: float
    current_value: float
    unrealized_pnl: float
    realized_pnl: float
    title: str                      # 마켓 질문


# ─────────────────────────────────────────────
# Signal Flow Types
# ─────────────────────────────────────────────

@dataclass(order=True)
class Signal:
    """전략이 생산하는 시그널.

    PriorityQueue에 넣기 위해 order=True이며,
    urgency(IntEnum)를 첫 번째 비교 기준으로 사용.
    sort_key 필드가 비교에 사용되고, 나머지 필드는 compare=False.
    """
    # 정렬 키: (urgency, timestamp) — PriorityQueue용
    sort_key: tuple[int, float] = field(compare=True, repr=False)

    # 실제 데이터 (비교 제외)
    id: str = field(default="", compare=False)                  # UUID
    strategy: StrategyType = field(default=StrategyType.AMBIGUITY, compare=False)
    condition_id: str = field(default="", compare=False)        # 마켓 ID
    token_id: str = field(default="", compare=False)            # 대상 토큰 ID
    side: OrderSide = field(default=OrderSide.BUY, compare=False)
    confidence: float = field(default=0.0, compare=False)       # 0.0 ~ 1.0
    urgency: SignalUrgency = field(default=SignalUrgency.MEDIUM, compare=False)
    price_at_signal: float = field(default=0.0, compare=False)  # 시그널 생성 시 가격
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
    expires_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


@dataclass
class TradeDecision:
    """Meta Brain이 생성하는 거래 결정.

    복수 시그널의 수렴 결과.
    """
    id: str                           # UUID
    condition_id: str                 # 마켓 ID
    token_id: str                     # 대상 토큰 ID
    side: OrderSide                   # BUY | SELL
    confidence: float                 # Meta Brain 최종 confidence (0.0~1.0)
    urgency: SignalUrgency            # 가장 높은 urgency 채택
    contributing_signals: list[str]   # Signal ID 리스트
    convergence_count: int            # 수렴 시그널 수
    weighted_confidence: float        # 가중 평균 confidence (보너스 전)
    convergence_bonus: float          # 중첩 보너스
    price_at_decision: float          # 결정 시점 가격
    executor_mode: ExecutorMode       # SNIPER | PATIENT
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskLayerResult:
    """Risk Sentinel 개별 층 평가 결과."""
    layer: int                        # 1~6
    name: str                         # 층 이름
    passed: bool                      # 통과 여부
    detail: str                       # 상세 설명
    adjusted_size: float | None = None  # 크기 조정 (Layer 1, 5에서 사용)


@dataclass
class RiskApproval:
    """Risk Sentinel 최종 승인/거부 결과."""
    approved: bool
    decision_id: str                  # TradeDecision.id
    final_size_usdc: float            # 최종 주문 크기 (USDC)
    final_size_tokens: float          # 최종 주문 크기 (토큰 수량)
    target_price: float               # 목표 가격
    order_type: OrderType             # GTC, FOK, postOnly 등
    layer_results: list[RiskLayerResult]
    reject_reason: RiskRejectReason | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskCheck:
    """Risk Sentinel이 참조하는 현재 리스크 상태 스냅샷."""
    bankroll: float                   # 사용 가능 잔고 (USDC)
    total_exposure: float             # 총 노출 (USDC)
    daily_pnl: float                  # 오늘 실현 P&L
    peak_bankroll: float              # 역대 최고 잔고
    current_drawdown: float           # 현재 DD 비율 (0.0~1.0)
    market_exposures: dict[str, float]  # condition_id → 노출 USDC
    correlation_groups: dict[str, list[str]]  # group_key → [condition_id, ...]
    circuit_breaker_active: bool      # 서킷브레이커 활성 여부


@dataclass
class TradeResult:
    """Executor가 반환하는 거래 결과."""
    id: str                           # UUID
    decision_id: str                  # TradeDecision.id
    condition_id: str
    token_id: str
    side: OrderSide
    price: float                      # 실제/가상 체결 가격
    size_tokens: float                # 체결 수량 (토큰)
    cost_usdc: float                  # 소요 USDC
    order_type: OrderType
    executor_mode: ExecutorMode
    order_id: str | None              # Polymarket order ID (DRY_RUN 시 None)
    status: TradeStatus
    confidence: float                 # Meta Brain 최종 confidence
    convergence_count: int
    signals_used: list[str]           # Signal ID 리스트
    risk_layers: list[RiskLayerResult]
    is_dry_run: bool
    created_at: datetime = field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Portfolio Types
# ─────────────────────────────────────────────

@dataclass
class Position:
    """현재 보유 포지션."""
    condition_id: str
    token_id: str
    outcome: str                      # "Yes" | "No"
    size: float                       # 보유 수량
    avg_price: float                  # 평균 매입가
    current_price: float              # 현재 가격
    unrealized_pnl: float             # 미실현 P&L
    market_question: str              # 마켓 질문
    is_dry_run: bool = False


@dataclass
class DailyStats:
    """일별 거래 통계."""
    date: str                         # "YYYY-MM-DD"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_bankroll: float = 0.0
    signals_generated: int = 0
    signals_converted: int = 0
    circuit_breaker_hit: int = 0
    is_dry_run: bool = False


# ─────────────────────────────────────────────
# WebSocket Event Types
# ─────────────────────────────────────────────

@dataclass
class WSTradeEvent:
    """WebSocket last_trade_price 이벤트 파싱 결과."""
    asset_id: str
    price: float
    side: str
    size: float
    timestamp: str


@dataclass
class WSPriceChangeEvent:
    """WebSocket price_change 이벤트 파싱 결과."""
    asset_id: str
    market: str                       # condition_id
    changes: list[dict[str, Any]]     # 변경 내역
    timestamp: str


@dataclass
class WSBookEvent:
    """WebSocket book 이벤트 파싱 결과."""
    market: str                       # condition_id
    asset_id: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: str

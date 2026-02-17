"""
공유 타입 정의 — 설계자 소유 파일.
모든 모듈이 이 파일의 타입을 import하여 사용합니다.
개발자는 이 파일을 읽기 전용으로 취급하세요.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ============================================================
# Enums
# ============================================================

class Direction(str, Enum):
    """주문 방향."""
    BUY = "BUY"
    SELL = "SELL"


class TokenSide(str, Enum):
    """아웃컴 토큰 종류."""
    YES = "YES"
    NO = "NO"


class OrderType(str, Enum):
    """주문 유형."""
    GTC = "GTC"        # Good-Til-Cancelled
    GTD = "GTD"        # Good-Til-Date
    FOK = "FOK"        # Fill-Or-Kill
    FAK = "FAK"        # Fill-And-Kill


class OrderStatus(str, Enum):
    """주문 상태."""
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PositionStatus(str, Enum):
    """포지션 상태 (드라이런 가상 포지션)."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# ============================================================
# 가격 / 오더북 관련
# ============================================================

@dataclass
class PricePoint:
    """가격 히스토리의 단일 데이터 포인트."""
    timestamp: int      # Unix timestamp
    price: float        # 0.0 ~ 1.0


@dataclass
class OrderBookEntry:
    """오더북의 단일 호가."""
    price: float        # 0.0 ~ 1.0
    size: float         # 토큰 수량


@dataclass
class OrderBook:
    """특정 토큰의 오더북."""
    token_id: str
    bids: List[OrderBookEntry]     # 가격 내림차순
    asks: List[OrderBookEntry]     # 가격 오름차순

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 1.0

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid

    def bid_depth(self, levels: int = 5) -> float:
        """상위 N레벨의 매수 물량 합."""
        return sum(b.size for b in self.bids[:levels])

    def ask_depth(self, levels: int = 5) -> float:
        """상위 N레벨의 매도 물량 합."""
        return sum(a.size for a in self.asks[:levels])


# ============================================================
# 시장 데이터
# ============================================================

@dataclass
class MarketToken:
    """시장 내 개별 아웃컴 토큰."""
    token_id: str
    outcome: str         # "Yes" or "No"


@dataclass
class GammaMarket:
    """Gamma API에서 가져온 시장 메타데이터."""
    id: int
    question: str
    condition_id: str
    slug: str
    description: str
    resolution_source: str
    end_date: str                       # ISO 날짜 문자열
    outcomes: List[str]                 # ["Yes", "No"]
    outcome_prices: List[float]         # [0.55, 0.45]
    volume: float
    liquidity: float
    active: bool
    closed: bool
    tags: List[str]                     # 태그 라벨 리스트
    neg_risk: bool
    tokens: List[MarketToken]           # CLOB 토큰 정보 (있으면)
    event_id: Optional[str] = None      # 이벤트 그룹 ID


@dataclass
class EnrichedMarket:
    """Gamma + CLOB 데이터가 결합된 시장 정보.
    전략에 전달되는 단위 데이터."""
    gamma: GammaMarket
    yes_price: float                    # CLOB midpoint (YES)
    no_price: float                     # 1.0 - yes_price
    order_book: Optional[OrderBook] = None
    price_history: Optional[List[PricePoint]] = None


# ============================================================
# 전략 시그널
# ============================================================

@dataclass
class Signal:
    """개별 전략이 생성하는 시그널.
    BaseStrategy.analyze()의 반환 단위."""
    strategy_name: str                  # 예: "resolution_arb"
    condition_id: str                   # 시장 condition_id
    token_id: str                       # 대상 토큰 ID
    market_question: str                # 시장 질문 (로깅용)
    direction: Direction                # BUY or SELL
    token_side: TokenSide               # YES or NO
    strength: float                     # 0.0 ~ 1.0 (시그널 강도)
    confidence: float                   # 0.0 ~ 1.0 (확신도)
    reason: str                         # 시그널 생성 이유 (로깅용)
    suggested_price: Optional[float] = None   # 리밋 가격 (유동성 전략)
    order_type: OrderType = OrderType.GTC     # 기본 GTC
    raw_data: Optional[Dict] = None     # 전략별 분석 상세 (JSON 직렬화 가능)


# ============================================================
# 메타봇 거래 결정
# ============================================================

@dataclass
class TradeDecision:
    """메타봇이 최종 결정한 거래.
    RiskManager 검사 후 OrderExecutor로 전달."""
    condition_id: str
    token_id: str
    market_question: str
    direction: Direction
    token_side: TokenSide
    composite_score: float              # 메타봇 복합 스코어 (0.0 ~ 1.0)
    contributing_signals: List[Signal]  # 기여한 시그널 목록
    suggested_price: Optional[float] = None
    order_type: OrderType = OrderType.GTC
    size: float = 0.0                   # RiskManager가 최종 설정


# ============================================================
# 주문 결과
# ============================================================

@dataclass
class OrderResult:
    """주문 실행 결과."""
    success: bool
    order_id: str                       # 실거래: CLOB order_id, 드라이런: "DRY-xxxx"
    condition_id: str
    token_id: str
    direction: Direction
    token_side: TokenSide
    price: float
    size: float
    order_type: OrderType
    status: OrderStatus
    composite_score: float
    contributing_strategies: List[str]  # 전략 이름 리스트
    dry_run: bool = False
    error_message: str = ""
    transaction_hash: Optional[str] = None


# ============================================================
# 포지션
# ============================================================

@dataclass
class Position:
    """현재 보유 포지션 (실거래: Data API, 드라이런: DB)."""
    condition_id: str
    token_id: str
    market_question: str
    outcome: str                        # "Yes" or "No"
    size: float                         # 보유 수량
    avg_price: float                    # 평균 진입가
    current_price: float                # 현재가
    unrealized_pnl: float               # 미실현 손익
    realized_pnl: float                 # 실현 손익


# ============================================================
# 리스크 관리
# ============================================================

@dataclass
class RiskCheckResult:
    """리스크 검사 결과."""
    approved: bool                      # 거래 승인 여부
    adjusted_size: float                # 조정된 주문 크기 (USDC)
    reason: str                         # 승인/거부 이유
    original_size: float = 0.0          # 원래 요청 크기


# ============================================================
# 설정 타입 (Config에서 사용)
# ============================================================

@dataclass
class RiskConfig:
    """리스크 관리 설정."""
    max_position_size_usd: float = 50.0
    max_portfolio_exposure_usd: float = 500.0
    max_single_market_pct: float = 0.20
    max_daily_loss_usd: float = 100.0
    max_open_orders: int = 10
    min_order_size_usd: float = 5.0


@dataclass
class MetaBotConfig:
    """메타봇 설정."""
    strategy_weights: Dict[str, float] = field(default_factory=lambda: {
        "resolution_arb": 1.0,
        "oracle_fear": 1.0,
        "contrarian": 0.8,
        "correlated": 1.2,
        "liquidity_vacuum": 0.6,
    })
    overlap_bonus_per_signal: float = 0.15
    min_composite_score: float = 0.4
    max_overlap_bonus: float = 0.60


@dataclass
class StrategyConfig:
    """개별 전략 설정. 전략마다 params 딕셔너리에 고유 파라미터 저장."""
    name: str                           # 전략 이름
    enabled: bool = True                # 활성화 여부
    interval_seconds: int = 60          # polling 주기 (초)
    params: Dict = field(default_factory=dict)  # 전략별 파라미터


# ============================================================
# 전략별 기본 파라미터 상수
# ============================================================

RESOLUTION_ARB_DEFAULTS: Dict = {
    "ambiguity_threshold": 0.5,
    "max_no_price": 0.60,
    "min_yes_price": 0.40,
    "keywords": [
        "significant", "substantially", "meaningful", "notable",
        "major", "considerable", "largely", "mostly", "effectively",
        "controversial", "disputed", "unclear", "ambiguous", "debatable",
    ],
}

ORACLE_FEAR_DEFAULTS: Dict = {
    "dispute_threshold": 0.4,
    "min_discount": 0.05,
    "min_yes_price": 0.30,
    "max_yes_price": 0.85,
    "dispute_keywords": [
        "dispute", "controversial", "appeal", "challenge",
        "contest", "recount", "audit", "investigate", "allegation",
        "manipulation", "fraud", "rigged",
    ],
    "dispute_categories": ["Politics", "Crypto", "Legal"],
}

CONTRARIAN_DEFAULTS: Dict = {
    "zscore_threshold": 2.0,
    "zscore_with_pattern_threshold": 1.5,
    "weekend_drift_pct": 0.05,
    "settlement_days": 3,
    "settlement_change_pct": 0.10,
    "rapid_move_hours": 6,
    "rapid_move_pct": 0.08,
    "history_interval": "1w",
}

CORRELATED_DEFAULTS: Dict = {
    "sum_tolerance": 0.05,
    "implied_conditional_threshold": 1.5,
    "min_group_size": 2,
    "min_common_tags": 2,
}

LIQUIDITY_VACUUM_DEFAULTS: Dict = {
    "min_spread": 0.05,
    "min_depth_ratio": 2.0,
    "spread_offset_ratio": 0.4,
    "depth_levels": 5,
}

# 전략 이름 → 기본 파라미터 매핑
STRATEGY_DEFAULT_PARAMS: Dict[str, Dict] = {
    "resolution_arb": RESOLUTION_ARB_DEFAULTS,
    "oracle_fear": ORACLE_FEAR_DEFAULTS,
    "contrarian": CONTRARIAN_DEFAULTS,
    "correlated": CORRELATED_DEFAULTS,
    "liquidity_vacuum": LIQUIDITY_VACUUM_DEFAULTS,
}

# 전략별 기본 polling 간격 (초)
STRATEGY_DEFAULT_INTERVALS: Dict[str, int] = {
    "resolution_arb": 300,     # 5분
    "oracle_fear": 300,        # 5분
    "contrarian": 60,          # 1분
    "correlated": 120,         # 2분
    "liquidity_vacuum": 30,    # 30초
}

# API 기본 URL 상수
CLOB_HOST: str = "https://clob.polymarket.com"
GAMMA_BASE_URL: str = "https://gamma-api.polymarket.com"
DATA_BASE_URL: str = "https://data-api.polymarket.com"
CHAIN_ID: int = 137  # Polygon

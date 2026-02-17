# DESIGN.md — Polymarket Reaper Bot v1.0

**작성일**: 2026-02-17
**작성자**: Architect Agent
**기반**: .plan.md, oracle_report.md

---

## 1. 아키텍처 개요

Signal Marketplace 아키텍처: 10개 독립 전략이 시그널을 생산하고, Priority Queue를 통해 Meta Brain이 수렴 탐지 후 Dual Executor로 라우팅한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Trading Engine (asyncio)                     │
│                                                                 │
│  ┌──────────┐  ┌──────────┐                                     │
│  │ REST     │  │WebSocket │    Data Sources                     │
│  │ Poller   │  │ Manager  │                                     │
│  └────┬─────┘  └────┬─────┘                                     │
│       │              │                                           │
│       ▼              ▼                                           │
│  ┌─────────────────────────┐                                     │
│  │   Market Data Cache     │                                     │
│  └────────────┬────────────┘                                     │
│               │                                                  │
│    ┌──────────┼──────────────────────────┐                       │
│    ▼          ▼          ▼               ▼                       │
│ ┌──────┐ ┌──────┐ ┌──────┐  ... ┌──────────┐                   │
│ │Strat1│ │Strat2│ │Strat3│      │Strat10   │  10 Strategies    │
│ └──┬───┘ └──┬───┘ └──┬───┘      └──┬───────┘                   │
│    │        │        │              │                            │
│    ▼        ▼        ▼              ▼                            │
│  ┌──────────────────────────────────────┐                        │
│  │   Priority Signal Queue              │                        │
│  │   (asyncio.PriorityQueue)            │                        │
│  └──────────────────┬───────────────────┘                        │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────┐                        │
│  │   Meta Brain (수렴 탐지기)            │                        │
│  │   → TradeDecision 생성               │                        │
│  └──────────────────┬───────────────────┘                        │
│                     │                                            │
│                     ▼                                            │
│  ┌──────────────────────────────────────┐                        │
│  │   Risk Sentinel (6층 방어)            │                        │
│  └──────────────────┬───────────────────┘                        │
│                     │                                            │
│           ┌─────────┴─────────┐                                  │
│           ▼                   ▼                                  │
│  ┌────────────────┐  ┌────────────────┐                          │
│  │ Sniper Executor│  │Patient Executor│  Dual Executor           │
│  │ (FOK/FAK)      │  │ (GTC/postOnly) │                          │
│  └────────────────┘  └────────────────┘                          │
│                                                                 │
│  ┌──────────────────────────────────────┐                        │
│  │   Portfolio Tracker + DB Logger      │                        │
│  └──────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 디렉토리 구조

```
polymarket-reaper/
├── DESIGN.md                          # 이 문서
├── .plan.md                           # 프로젝트 계획
├── .env.example                       # 환경변수 템플릿
├── requirements.txt                   # Python 의존성
├── start.sh                           # Linux/Mac 실행 스크립트
├── start.bat                          # Windows 실행 스크립트
├── config.py                          # 통합 설정 관리
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # asyncio 메인 엔트리포인트
│   │
│   ├── shared/
│   │   ├── __init__.py
│   │   └── types.py                   # 공유 타입 정의 (Enum, dataclass)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── clob_client.py             # CLOB API async 래퍼
│   │   ├── gamma_client.py            # Gamma API async 래퍼
│   │   ├── data_client.py             # Data API async 래퍼
│   │   └── ws_manager.py              # WebSocket 매니저
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py                  # Trading Engine (메인 루프)
│   │   ├── signal_queue.py            # Priority Signal Queue
│   │   ├── meta_brain.py             # Meta Brain 수렴 탐지기
│   │   ├── risk_sentinel.py           # Risk Sentinel 6층 방어
│   │   └── executor.py               # Dual Executor (Sniper + Patient)
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseStrategy 추상 클래스
│   │   ├── ambiguity.py               # 전략1: Ambiguity Scoring
│   │   ├── oracle_fear.py             # 전략2: Oracle Fear Premium
│   │   ├── contrarian.py              # 전략3: Contrarian Detector
│   │   ├── correlated.py              # 전략4: Correlated Markets
│   │   ├── liquidity_vacuum.py        # 전략5: Liquidity Vacuum (WS)
│   │   ├── settlement_decay.py        # 전략7: Settlement Decay
│   │   ├── event_cascade.py           # 전략8: Event Cascade Lag
│   │   ├── maker_rebate.py            # 전략9: Maker Rebate Harvesting
│   │   └── whale_shadow.py            # 전략10: Whale Shadow (WS)
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── market_cache.py            # 시장 데이터 인메모리 캐시
│   │   └── db.py                      # aiosqlite DB 매니저
│   │
│   └── portfolio/
│       ├── __init__.py
│       └── tracker.py                 # 포지션/포트폴리오 추적
│
├── data/
│   └── reaper.db                      # SQLite DB 파일 (런타임 생성)
│
└── tests/
    ├── __init__.py
    ├── test_strategies.py             # 전략 단위 테스트
    ├── test_risk.py                   # Risk Sentinel 테스트
    ├── test_meta_brain.py             # Meta Brain 테스트
    └── test_executor.py               # Executor 테스트
```

**참고**: 전략6(Meta Brain)은 `src/core/meta_brain.py`에 위치한다. 전략이 아니라 시그널 소비자이므로 core에 배치.

---

## 3. 모듈 역할 상세

### 3.1 `config.py` — 통합 설정

환경변수(.env)를 읽고 전략 파라미터를 통합 관리한다. 모든 모듈은 config를 import하여 설정값을 얻는다.

**역할**:
- `.env` 파일 로드 (dotenv 사용하지 않음, `os.environ` 직접 사용)
- API 키, 지갑 주소 등 시크릿 관리
- 전략별 파라미터 기본값 정의
- 리스크 파라미터 중앙 관리
- DRY_RUN 모드 플래그

**핵심 설정 구조**:
```python
# 모든 설정은 클래스 변수로 정의, 환경변수로 오버라이드 가능
class Config:
    # API
    CLOB_HOST: str           # 기본 "https://clob.polymarket.com"
    GAMMA_HOST: str          # 기본 "https://gamma-api.polymarket.com"
    DATA_HOST: str           # 기본 "https://data-api.polymarket.com"
    WS_MARKET_URL: str       # 기본 "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    WS_USER_URL: str         # 기본 "wss://ws-subscriptions-clob.polymarket.com/ws/user"

    # Auth
    PRIVATE_KEY: str
    POLY_API_KEY: str
    POLY_API_SECRET: str
    POLY_API_PASSPHRASE: str
    WALLET_ADDRESS: str
    SIGNATURE_TYPE: int      # 기본 0 (EOA)
    FUNDER_ADDRESS: str      # POLY_PROXY일 때만 사용

    # Risk
    KELLY_FRACTION: float    # 0.4
    MAX_SINGLE_MARKET: float # 0.15
    MAX_TOTAL_EXPOSURE: float # 0.60
    DAILY_LOSS_LIMIT: float  # 0.08
    DRAWDOWN_THROTTLE_PCT: float  # 0.05
    CORRELATION_GUARD_THRESHOLD: float  # 0.7

    # Engine
    DRY_RUN: bool            # True면 주문 미전송
    POLLING_INTERVAL_SEC: float  # REST 폴링 기본 주기 (60초)
    DB_PATH: str             # "data/reaper.db"
    LOG_LEVEL: str           # "INFO"

    # Strategy-specific (각 전략 모듈에서 참조)
    AMBIGUITY_KEYWORDS: list[str]
    CONTRARIAN_Z_THRESHOLD: float  # 2.0
    WHALE_MIN_SIZE_USDC: float     # 500.0
    LIQUIDITY_SPREAD_THRESHOLD: float  # 0.05
    SETTLEMENT_DECAY_DAYS: int     # 7
    CASCADE_LAG_WINDOW_SEC: int    # 300
    MAKER_REBATE_MIN_SPREAD: float # 0.02
    ORACLE_FEAR_DISCOUNT: float    # 0.05
    META_BRAIN_MIN_CONVERGENCE: int  # 3
```

### 3.2 `src/api/clob_client.py` — CLOB API Async 래퍼

py-clob-client는 동기(sync) 라이브러리다. `asyncio.get_event_loop().run_in_executor(None, ...)` 로 async 래핑한다.

**역할**:
- py-clob-client의 ClobClient 인스턴스를 내부에 보유
- 모든 메서드를 async로 노출
- 지수 백오프 재시도 (HTTP 429 대응)
- Rate limit 추적: 내부 카운터로 요청 수 관리

**주요 메서드**:
```
async get_markets(next_cursor: str) -> dict
async get_order_book(token_id: str) -> OrderBookSnapshot
async get_midpoint(token_id: str) -> float
async get_price(token_id: str, side: str) -> float
async get_last_trade_price(token_id: str) -> float
async get_prices_history(token_id: str, interval: str) -> list[PricePoint]
async get_spread(token_id: str) -> float
async get_fee_rate(token_id: str) -> float
async post_order(order: SignedOrder, order_type: str) -> OrderResult
async cancel_order(order_id: str) -> bool
async cancel_all() -> bool
async get_open_orders(market: str | None) -> list[dict]
async get_trades(market: str | None) -> list[dict]
```

**Rate Limit 관리**:
- 내부 `asyncio.Semaphore(50)` + 슬라이딩 윈도우 카운터
- 공개 API: 100 req/분 → 1.5초 간격 보장
- 주문 API: 60 orders/분 → 별도 세마포어
- 429 응답 시 2^n 초 백오프 (최대 3회)

### 3.3 `src/api/gamma_client.py` — Gamma API Async 래퍼

마켓 메타데이터, 태그, 이벤트 정보를 비동기로 조회한다. aiohttp 직접 사용.

**주요 메서드**:
```
async get_markets(active: bool, limit: int, offset: int, tag_id: int | None, order: str) -> list[GammaMarket]
async get_market_by_slug(slug: str) -> GammaMarket
async get_events(limit: int, offset: int) -> list[GammaEvent]
async get_tags() -> list[GammaTag]
async get_related_tags(tag_id: int) -> list[GammaTag]
```

**GammaMarket 주요 필드** (API 응답에서 추출):
- id, question, conditionId, slug, resolutionSource, endDate
- liquidity, volume, outcomes, outcomePrices
- active, closed, tags, negRisk, description

### 3.4 `src/api/data_client.py` — Data API Async 래퍼

포지션, 포트폴리오 가치, 거래내역을 비동기로 조회한다. aiohttp 직접 사용.

**주요 메서드**:
```
async get_positions(wallet: str, market: str | None) -> list[PositionData]
async get_portfolio_value(wallet: str) -> float
async get_activity(wallet: str) -> list[dict]
async get_holders(token_id: str) -> list[dict]
```

### 3.5 `src/api/ws_manager.py` — WebSocket 매니저

Market 채널과 User 채널의 WebSocket 연결을 관리한다.

**역할**:
- Market 채널: 가격 변화, 체결, 오더북 이벤트 수신
- User 채널: 주문 상태 변경 수신 (L2 인증)
- 자동 재연결 (지수 백오프)
- 이벤트를 콜백 함수로 디스패치

**주요 메서드**:
```
async connect_market(asset_ids: list[str], on_event: Callable) -> None
async connect_user(on_event: Callable) -> None
async subscribe_assets(asset_ids: list[str]) -> None  # 추가 구독
async close() -> None
```

**이벤트 디스패치 구조**:
- `last_trade_price` 이벤트 → Whale Shadow, Liquidity Vacuum 전략에 전달
- `price_change` 이벤트 → Market Data Cache 업데이트
- `book` 이벤트 → Liquidity Vacuum 전략에 전달

**재연결 로직**:
1. 연결 끊김 감지
2. 1초 → 2초 → 4초 → 8초 → 최대 30초 백오프
3. 재연결 후 기존 구독 목록 자동 재구독

### 3.6 `src/core/engine.py` — Trading Engine

전체 시스템의 메인 루프. asyncio.gather로 모든 비동기 태스크를 관리한다.

**역할**:
- 전략 스케줄러: 각 전략의 polling 주기 관리
- WebSocket + REST 하이브리드 데이터 수집
- Signal Queue 소비 → Meta Brain → Risk Sentinel → Executor 파이프라인 구동
- Graceful shutdown (SIGINT/SIGTERM 핸들링)

**실행 흐름**:
```
async def run():
    1. config 로드, DB 초기화
    2. API 클라이언트 초기화 (clob, gamma, data)
    3. Market Data Cache 초기화 (Gamma API로 활성 마켓 로드)
    4. WebSocket 연결 (market 채널)
    5. 전략 인스턴스 생성 (enabled 전략만)
    6. asyncio.gather(
         _run_rest_strategies(),    # REST 기반 전략 polling
         _run_ws_strategies(),      # WS 기반 전략 (실시간)
         _consume_signals(),        # Signal Queue → Meta Brain → Executor
         _portfolio_sync(),         # 주기적 포지션 동기화
         _health_check(),           # 시스템 헬스체크
       )
```

**전략 스케줄러 polling 주기**:
| 전략 | 주기 | 이유 |
|------|------|------|
| Ambiguity | 300초 | 마켓 메타데이터 변경 느림 |
| Oracle Fear | 300초 | 분쟁 키워드 변경 느림 |
| Contrarian | 120초 | 가격 Z-score 중간 빈도 |
| Correlated | 180초 | 다수 마켓 비교 연산 비용 |
| Settlement Decay | 600초 | 시간가치 변화 완만 |
| Event Cascade | 120초 | 이벤트 전파 감지 |
| Maker Rebate | 60초 | 스프레드 변화 빈번 |
| Liquidity Vacuum | 실시간 | WebSocket 오더북 이벤트 |
| Whale Shadow | 실시간 | WebSocket 체결 이벤트 |
| Meta Brain | 이벤트 | Signal Queue에서 소비 시 |

**Rate Limit 배분** (100 req/분 공개 API):
- 전략 polling 합계: ~40 req/분 (여유 확보)
- Market Data Cache 갱신: ~20 req/분
- 포지션 동기화: ~5 req/분
- 예비: ~35 req/분

### 3.7 `src/core/signal_queue.py` — Priority Signal Queue

asyncio.PriorityQueue 기반. 시그널의 urgency에 따라 우선순위를 부여한다.

**우선순위 (낮을수록 먼저 처리)**:
```
CRITICAL = 1   # 즉시 체결 필요 (Whale Shadow, Liquidity Vacuum)
HIGH     = 2   # 높은 확신 시그널
MEDIUM   = 3   # 표준 시그널
LOW      = 4   # 낮은 확신, 리베이트 수확 등
```

**주요 메서드**:
```
async put(signal: Signal) -> None           # 전략이 시그널 투입
async get() -> Signal                        # Meta Brain이 소비
def qsize() -> int                           # 대기 시그널 수
async drain_expired() -> int                 # 만료 시그널 제거
```

**시그널 만료**: 각 시그널에 `expires_at` 필드가 있으며, drain_expired()가 30초마다 실행되어 만료된 시그널을 제거.

### 3.8 `src/core/meta_brain.py` — Meta Brain 수렴 탐지기 (전략6)

Signal Queue에서 시그널을 소비하고, 같은 마켓에 대한 복수 시그널이 수렴하면 TradeDecision을 생성한다.

**역할**:
- 시그널 버퍼링: market_id별로 최근 시그널 수집 (시간 윈도우: 600초)
- 수렴 탐지: 동일 마켓에 `META_BRAIN_MIN_CONVERGENCE`개 이상의 시그널이 같은 방향이면 수렴
- 가중 평균 confidence 산출: 전략별 가중치 적용
- 중첩 보너스: 수렴 시그널 수에 비례하는 confidence 보너스
- TradeDecision 생성 → Risk Sentinel로 전달

**수렴 로직**:
```
1. 새 시그널 도착
2. 해당 market_id의 시그널 버퍼 조회
3. 같은 side(BUY/SELL)의 활성 시그널 카운트
4. count >= META_BRAIN_MIN_CONVERGENCE 이면:
   a. 가중 평균 confidence = Σ(signal.confidence * strategy_weight) / Σ(strategy_weight)
   b. 중첩 보너스 = min(0.15, (count - MIN_CONVERGENCE) * 0.05)
   c. final_confidence = min(0.95, weighted_avg + bonus)
   d. urgency = 가장 높은 urgency의 시그널 채택
   e. TradeDecision 생성
```

**전략별 가중치**:
| 전략 | 가중치 | 이유 |
|------|--------|------|
| Ambiguity | 1.2 | 구조적 미스프라이싱 |
| Oracle Fear | 1.0 | 이벤트 기반 |
| Contrarian | 1.1 | 통계적 근거 |
| Correlated | 1.3 | 차익 기회 높음 |
| Liquidity Vacuum | 0.8 | 단기 신호, 노이즈 가능 |
| Settlement Decay | 0.9 | 시간가치 수확 |
| Event Cascade | 1.1 | 전파 지연 차익 |
| Maker Rebate | 0.6 | 리베이트 위주, 방향성 약함 |
| Whale Shadow | 0.9 | 추종 전략 |

### 3.9 `src/core/risk_sentinel.py` — Risk Sentinel 6층 방어

TradeDecision이 6개의 리스크 레이어를 통과해야 Executor에 도달한다. 하나라도 거부하면 거래가 차단된다.

**6층 구조**:

```
TradeDecision
    │
    ▼
┌───────────────────────┐
│ Layer 1: Kelly Sizer  │  Fractional Kelly 0.4로 포지션 크기 산출
│ (포지션 사이징)        │  입력: confidence, bankroll, odds
│                       │  출력: 최적 size (USDC)
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Layer 2: Single Market│  단일 마켓 노출 15% 제한
│ (집중도 검사)          │  현재 해당 마켓 포지션 + 신규 size <= bankroll * 0.15
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Layer 3: Total        │  총 노출 60% 제한
│ Exposure (총 노출)     │  모든 활성 포지션 합계 + 신규 size <= bankroll * 0.60
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Layer 4: Circuit      │  일일 손실 8% 서킷브레이커
│ Breaker (일일 손실)    │  오늘 실현 손실 >= bankroll * 0.08 → 당일 거래 전면 중단
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Layer 5: Drawdown     │  최고점 대비 하락률 기반 거래량 축소
│ Throttle (DD 감속)     │  DD > 5%: size * 0.5, DD > 10%: size * 0.25, DD > 15%: 중단
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│ Layer 6: Correlation  │  상관 마켓 과잉 노출 방지
│ Guard (상관 방어)      │  같은 태그/이벤트 마켓 총 노출 제한
└───────────┴───────────┘
            │
            ▼
       Executor에 전달 (RiskApproval 포함)
```

**Layer 1 — Kelly Sizer 상세**:
```
kelly_fraction = 0.4
edge = confidence - (1 - confidence)  # 기대 엣지
odds = (1 / price) - 1                # 배당률 근사
kelly_pct = kelly_fraction * (edge * odds - (1 - edge)) / odds
size = max(0, kelly_pct) * bankroll
size = max(size, 5.0)  # 최소 주문 크기 (Polymarket 제약)
```

**Layer 4 — Circuit Breaker 상세**:
- daily_loss는 UTC 00:00 기준 리셋
- 서킷브레이커 작동 시 모든 신규 주문 차단, 기존 GTC 주문도 취소
- 로그 기록 + DB 저장

**Layer 6 — Correlation Guard 상세**:
- 같은 `event_id`를 공유하는 마켓들은 상관 그룹으로 취급
- 같은 `tag`를 가진 마켓도 약한 상관으로 간주 (가중치 0.5)
- 상관 그룹 내 총 노출: bankroll * 0.30 제한

### 3.10 `src/core/executor.py` — Dual Executor

Risk Sentinel을 통과한 TradeDecision을 실제 주문으로 변환한다.

**Sniper Executor** (urgency: CRITICAL, HIGH):
- FOK(Fill-Or-Kill) 주문: 즉시 전량 체결 또는 취소
- 가격: midpoint 기준 +-slippage_tolerance (기본 0.02)
- 목적: 빠르게 사라지는 기회 포착 (고래 추적, 유동성 진공)

**Patient Executor** (urgency: MEDIUM, LOW):
- GTC + postOnly 주문: 메이커로 오더북에 대기
- 가격: 유리한 가격에 지정가 (bid/ask 스프레드 내)
- 목적: 리베이트 수취, 시간가치 수확
- 주의: postOnly와 FOK/FAK 동시 설정 불가 (Oracle 보고서 제약)

**공통**:
- DRY_RUN=true일 때: 실제 주문 전송하지 않고 가상 체결 기록
- 주문 결과를 DB에 기록
- 체결 실패 시 1회 재시도 후 포기 (과도한 재시도 방지)

**주요 메서드**:
```
async execute(decision: TradeDecision, approval: RiskApproval) -> TradeResult
async _sniper_execute(decision, approval) -> TradeResult
async _patient_execute(decision, approval) -> TradeResult
```

**Executor 라우팅**:
```
if decision.urgency in (CRITICAL, HIGH):
    result = await _sniper_execute(decision, approval)
else:
    result = await _patient_execute(decision, approval)
```

### 3.11 `src/strategies/base.py` — BaseStrategy

모든 전략의 추상 기반 클래스.

```python
class BaseStrategy(ABC):
    name: str                          # 전략 이름
    strategy_type: StrategyType        # Enum 값
    requires_ws: bool = False          # WebSocket 필요 여부
    polling_interval: float            # REST polling 주기 (초)
    enabled: bool = True               # 활성화 여부

    @abstractmethod
    async def analyze(self, market: MarketData) -> list[Signal]:
        """단일 마켓 분석 → 0개 이상의 시그널 반환"""

    async def on_ws_event(self, event: dict) -> list[Signal]:
        """WebSocket 이벤트 수신 시 (WS 전략만 오버라이드)"""
        return []

    def _create_signal(self, ...) -> Signal:
        """Signal 생성 헬퍼"""
```

### 3.12 전략 1~5, 7~10 (strategies/ 디렉토리)

각 전략 모듈은 BaseStrategy를 상속하고 `analyze()` 또는 `on_ws_event()`를 구현한다.

### 3.13 `src/data/market_cache.py` — Market Data Cache

API 호출을 줄이기 위한 인메모리 캐시. Gamma + CLOB 데이터를 통합 보관.

**역할**:
- 활성 마켓 목록 캐시 (5분 TTL)
- 마켓별 가격/오더북 캐시 (전략 polling 시 갱신)
- WebSocket 이벤트로 실시간 업데이트
- 전략들이 API를 직접 호출하지 않고 캐시에서 읽음

**주요 메서드**:
```
async refresh_markets() -> None              # Gamma API로 활성 마켓 새로고침
async get_market(condition_id: str) -> MarketData | None
async get_all_active_markets() -> list[MarketData]
async update_price(token_id: str, price: float) -> None     # WS 이벤트용
async update_orderbook(token_id: str, book: OrderBookSnapshot) -> None
```

### 3.14 `src/data/db.py` — DB 매니저

aiosqlite를 사용한 비동기 SQLite DB 관리.

**역할**:
- 테이블 초기화 (CREATE IF NOT EXISTS)
- 시그널, 거래, 포트폴리오 상태 기록
- 드라이런 모드에서도 동일하게 기록 (is_dry_run 플래그)

### 3.15 `src/portfolio/tracker.py` — Portfolio Tracker

현재 포지션과 포트폴리오 상태를 추적한다.

**역할**:
- Data API로 실제 포지션 동기화 (주기적)
- DRY_RUN 모드: 가상 포지션 인메모리 관리
- Risk Sentinel에 포지션 정보 제공
- 일일 P&L 계산, 총 노출 계산

**주요 메서드**:
```
async sync_positions() -> None                    # Data API에서 동기화
async get_position(condition_id: str) -> Position | None
async get_all_positions() -> list[Position]
async get_total_exposure() -> float               # 총 노출 USDC
async get_daily_pnl() -> float                    # 오늘 실현 P&L
async get_bankroll() -> float                     # 사용 가능 잔고
async record_virtual_trade(trade: TradeResult) -> None  # DRY_RUN용
```

---

## 4. DB 스키마

### 4.1 `signals` 테이블

전략이 생산한 모든 시그널을 기록한다.

```sql
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,                -- ISO 8601
    strategy        TEXT NOT NULL,                -- StrategyType enum value
    condition_id    TEXT NOT NULL,                -- 마켓 condition_id
    token_id        TEXT NOT NULL,                -- 아웃컴 토큰 ID
    side            TEXT NOT NULL,                -- "BUY" | "SELL"
    confidence      REAL NOT NULL,                -- 0.0 ~ 1.0
    urgency         TEXT NOT NULL,                -- SignalUrgency enum value
    price_at_signal REAL NOT NULL,                -- 시그널 생성 시 가격
    metadata        TEXT,                         -- JSON: 전략별 추가 데이터
    expires_at      TEXT NOT NULL,                -- ISO 8601 만료 시각
    consumed        INTEGER NOT NULL DEFAULT 0,   -- Meta Brain 소비 여부
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_signals_market ON signals(condition_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals(strategy, timestamp);
```

### 4.2 `trades` 테이블

실행된 거래(또는 드라이런 가상 거래)를 기록한다.

```sql
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,                -- ISO 8601
    condition_id    TEXT NOT NULL,                -- 마켓 condition_id
    token_id        TEXT NOT NULL,                -- 아웃컴 토큰 ID
    side            TEXT NOT NULL,                -- "BUY" | "SELL"
    price           REAL NOT NULL,                -- 체결 가격
    size            REAL NOT NULL,                -- 체결 수량 (토큰)
    cost_usdc       REAL NOT NULL,                -- 소요 USDC
    order_type      TEXT NOT NULL,                -- "GTC" | "FOK" | "postOnly" 등
    executor_mode   TEXT NOT NULL,                -- "SNIPER" | "PATIENT"
    order_id        TEXT,                         -- Polymarket order ID (드라이런 시 NULL)
    status          TEXT NOT NULL,                -- "FILLED" | "PARTIAL" | "REJECTED" | "DRY_RUN"
    confidence      REAL NOT NULL,                -- Meta Brain 최종 confidence
    convergence     INTEGER NOT NULL,             -- 수렴 시그널 수
    signals_used    TEXT NOT NULL,                -- JSON: 사용된 signal ID 리스트
    risk_layers     TEXT NOT NULL,                -- JSON: 각 층 통과 결과
    is_dry_run      INTEGER NOT NULL DEFAULT 0,   -- 1이면 가상 거래
    pnl             REAL,                         -- 실현 P&L (정산 후 업데이트)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(condition_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(timestamp);
```

### 4.3 `portfolio` 테이블

현재 포지션 스냅샷을 기록한다 (주기적 동기화).

```sql
CREATE TABLE IF NOT EXISTS portfolio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,                -- ISO 8601
    condition_id    TEXT NOT NULL,                -- 마켓 condition_id
    token_id        TEXT NOT NULL,                -- 아웃컴 토큰 ID
    outcome         TEXT NOT NULL,                -- "Yes" | "No"
    size            REAL NOT NULL,                -- 보유 수량
    avg_price       REAL NOT NULL,                -- 평균 매입가
    current_price   REAL NOT NULL,                -- 현재 가격
    unrealized_pnl  REAL NOT NULL,                -- 미실현 P&L
    market_question TEXT NOT NULL,                -- 마켓 질문 텍스트
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_portfolio_market ON portfolio(condition_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_time ON portfolio(timestamp);
```

### 4.4 `daily_stats` 테이블

일별 통계를 기록한다.

```sql
CREATE TABLE IF NOT EXISTS daily_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL UNIQUE,          -- "YYYY-MM-DD"
    total_trades    INTEGER NOT NULL DEFAULT 0,
    winning_trades  INTEGER NOT NULL DEFAULT 0,
    losing_trades   INTEGER NOT NULL DEFAULT 0,
    total_pnl       REAL NOT NULL DEFAULT 0.0,
    max_drawdown    REAL NOT NULL DEFAULT 0.0,
    peak_bankroll   REAL NOT NULL DEFAULT 0.0,
    signals_generated INTEGER NOT NULL DEFAULT 0,
    signals_converted INTEGER NOT NULL DEFAULT 0,  -- TradeDecision으로 전환된 수
    circuit_breaker_hit INTEGER NOT NULL DEFAULT 0,
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 5. 전략별 입출력 명세

### 5.1 전략1: Ambiguity Scoring (해결 기준 아비트라지)

**파일**: `src/strategies/ambiguity.py`
**데이터 소스**: Gamma API (마켓 메타데이터)
**polling 주기**: 300초

**입력**:
- `MarketData.question`: 마켓 질문 텍스트
- `MarketData.description`: 마켓 설명
- `MarketData.resolution_source`: 해결 소스 URL
- `MarketData.end_date`: 결제일
- `MarketData.yes_price`, `MarketData.no_price`: 현재 가격

**로직**:
1. 질문/설명에서 모호 키워드 추출 (TF-IDF 가중 스코어링)
2. 모호 키워드: "might", "could", "possibly", "approximately", "around", "unclear", "ambiguous", "depending on", "subject to" 등
3. resolution_source 유무 확인: 없으면 모호성 +0.2
4. ambiguity_score = keyword_score + source_penalty
5. ambiguity_score > 0.6이면 NO 포지션 시그널 (모호한 마켓은 NO가 유리)
6. confidence = min(0.8, 0.5 + ambiguity_score * 0.3)

**출력 Signal**:
- side: "BUY" (NO 토큰)
- confidence: 0.5 ~ 0.8
- urgency: MEDIUM
- metadata: `{"ambiguity_score": float, "keywords_found": list[str], "has_resolution_source": bool}`
- expires_at: now + 600초

### 5.2 전략2: Oracle Fear Premium (오라클 공포 프리미엄)

**파일**: `src/strategies/oracle_fear.py`
**데이터 소스**: Gamma API + CLOB API (가격)
**polling 주기**: 300초

**입력**:
- `MarketData.description`, `MarketData.question`
- `MarketData.tags`: 마켓 태그
- `MarketData.yes_price`: 현재 YES 가격

**로직**:
1. 분쟁 키워드 감지: "oracle", "UMA", "dispute", "resolution", "challenged", "appealed"
2. 카테고리 감지: 고분쟁 카테고리 (예: 규제, 법적 분쟁)
3. YES 가격이 0.05~0.10 할인인 마켓 탐색 (fair value 추정치 대비)
4. fair value 추정: 유사 마켓 평균 또는 히스토리 기반
5. discount = estimated_fair - current_price
6. discount >= ORACLE_FEAR_DISCOUNT(0.05)이면 매수 시그널

**출력 Signal**:
- side: "BUY" (YES 토큰)
- confidence: 0.5 ~ 0.75
- urgency: MEDIUM
- metadata: `{"fear_keywords": list[str], "discount": float, "estimated_fair": float}`
- expires_at: now + 600초

### 5.3 전략3: Contrarian Detector (군중 반대 지표)

**파일**: `src/strategies/contrarian.py`
**데이터 소스**: CLOB API (가격 히스토리)
**polling 주기**: 120초

**입력**:
- `MarketData.prices_history`: 최근 가격 히스토리 (1d~1w)
- `MarketData.yes_price`: 현재 가격
- `MarketData.end_date`: 결제일

**로직**:
1. 가격 히스토리에서 Z-score 계산: `z = (current - mean) / stdev` (statistics 모듈)
2. 주말 드리프트 감지: 금요일~일요일 가격 편차 > 평일의 2배면 과잉반응
3. 결제일 과열: 결제일 7일 이내에 급격한 가격 이동 (>0.15) 감지
4. Z-score 절댓값 > CONTRARIAN_Z_THRESHOLD(2.0)이면 반대 포지션 시그널
5. z > 2.0: SELL (과매수) → BUY NO
6. z < -2.0: BUY (과매도) → BUY YES

**출력 Signal**:
- side: Z-score 방향의 반대
- confidence: min(0.8, 0.5 + |z-score| * 0.1)
- urgency: HIGH (|z| > 3.0), MEDIUM (otherwise)
- metadata: `{"z_score": float, "mean": float, "stdev": float, "is_weekend_drift": bool, "near_settlement": bool}`
- expires_at: now + 300초

### 5.4 전략4: Correlated Markets (연관 시장 비효율)

**파일**: `src/strategies/correlated.py`
**데이터 소스**: Gamma API (태그), CLOB API (가격)
**polling 주기**: 180초

**입력**:
- 전체 활성 마켓 리스트 (MarketData 목록)
- 각 마켓의 tags, event_id, yes_price, no_price

**로직**:
1. 태그 기반 군집화: 같은 tag를 가진 마켓 그룹핑
2. 같은 event_id의 마켓들은 강한 상관
3. implied conditional 계산: P(A∩B) 추정 vs P(A)*P(B)
4. implied conditional > 1.5이면 미스프라이싱
5. Complete Set 아비트라지: 같은 이벤트의 모든 아웃컴 가격 합 != 1.0 → 차익
6. 합 > 1.05: 모든 아웃컴 매도 시그널
7. 합 < 0.95: 저평가된 아웃컴 매수 시그널

**출력 Signal**:
- side: "BUY" 또는 "SELL"
- confidence: 0.6 ~ 0.85
- urgency: HIGH (Complete Set 차익), MEDIUM (conditional 미스프라이싱)
- metadata: `{"correlated_markets": list[str], "implied_conditional": float, "complete_set_sum": float | null}`
- expires_at: now + 300초

### 5.5 전략5: Liquidity Vacuum (유동성 진공 사냥)

**파일**: `src/strategies/liquidity_vacuum.py`
**데이터 소스**: WebSocket (오더북 이벤트) + CLOB API (book 조회)
**requires_ws**: True

**입력**:
- `OrderBookSnapshot`: 실시간 오더북 (bids, asks)
- WebSocket `book` 및 `price_change` 이벤트

**로직**:
1. 스프레드 계산: best_ask - best_bid
2. 깊이 비대칭 계산: total_bid_size vs total_ask_size (상위 5단계)
3. 스프레드 > LIQUIDITY_SPREAD_THRESHOLD(0.05)이면 진공 감지
4. 깊이 비대칭 > 3:1이면 한쪽 유동성 고갈
5. 빈 쪽에 GTC 리밋 주문 시그널

**출력 Signal**:
- side: 유동성이 부족한 쪽의 반대 (매수벽 없으면 BUY)
- confidence: 0.4 ~ 0.7
- urgency: CRITICAL (스프레드 > 0.10), HIGH (0.05~0.10)
- metadata: `{"spread": float, "bid_depth": float, "ask_depth": float, "asymmetry_ratio": float}`
- expires_at: now + 120초 (유동성 상황은 빠르게 변함)

### 5.6 전략7: Settlement Decay (시간가치 감소)

**파일**: `src/strategies/settlement_decay.py`
**데이터 소스**: Gamma API (end_date), CLOB API (가격)
**polling 주기**: 600초

**입력**:
- `MarketData.end_date`: 결제일
- `MarketData.yes_price`: 현재 YES 가격

**로직**:
1. 잔여 시간 계산: days_to_settlement = (end_date - now).days
2. theta-like decay: 가격이 극단(>0.85 or <0.15)인 마켓에서 결제일 접근 시 수렴 가속
3. 결제일 SETTLEMENT_DECAY_DAYS(7일) 이내:
   - price > 0.85: YES 매수 (1.0으로 수렴 예상)
   - price < 0.15: NO 매수 (=YES 매도, 0.0으로 수렴 예상)
4. decay_rate = 1 / max(1, days_to_settlement)
5. confidence = 0.5 + decay_rate * 0.2 * distance_from_extreme

**출력 Signal**:
- side: 수렴 방향
- confidence: 0.5 ~ 0.7
- urgency: LOW
- metadata: `{"days_to_settlement": int, "decay_rate": float, "price_extreme": str}`
- expires_at: now + 900초

### 5.7 전략8: Event Cascade Lag (이벤트 전파 지연)

**파일**: `src/strategies/event_cascade.py`
**데이터 소스**: Gamma API (이벤트), CLOB API (가격 히스토리)
**polling 주기**: 120초

**입력**:
- 같은 event_id를 가진 마켓 그룹
- 각 마켓의 최근 가격 변동

**로직**:
1. 같은 이벤트의 마켓들 중 하나가 급격한 가격 변동 (>0.05)을 보이면:
2. 나머지 마켓들이 아직 반응하지 않았는지 확인 (CASCADE_LAG_WINDOW_SEC 이내)
3. 반응 지연 마켓에서 같은 방향 시그널 생성
4. lag_score = price_change_of_leader - price_change_of_lagger
5. lag_score > 0.03이면 시그널

**출력 Signal**:
- side: 리더 마켓과 같은 방향
- confidence: 0.5 ~ 0.75
- urgency: HIGH (lag_score > 0.07), MEDIUM (0.03~0.07)
- metadata: `{"leader_market": str, "leader_change": float, "lag_score": float, "lag_window_sec": int}`
- expires_at: now + 180초

### 5.8 전략9: Maker Rebate Harvesting (메이커 리베이트)

**파일**: `src/strategies/maker_rebate.py`
**데이터 소스**: CLOB API (스프레드, 수수료)
**polling 주기**: 60초

**입력**:
- `OrderBookSnapshot`: 오더북 (bid/ask)
- `MarketData.fee_rate_bps`: 수수료율

**로직**:
1. 스프레드 계산: best_ask - best_bid
2. 수수료율 확인: fee_rate_bps > 0인 마켓만 대상 (수수료 0 마켓은 리베이트 없음)
3. 스프레드 > MAKER_REBATE_MIN_SPREAD(0.02)이면:
4. best_bid + 0.01 (또는 minimum_tick_size)에 postOnly BUY 주문
5. 체결 시 리베이트 수취, 불리한 가격 이동 시 취소

**출력 Signal**:
- side: "BUY" (mid 아래) 또는 "SELL" (mid 위)
- confidence: 0.4 ~ 0.6
- urgency: LOW
- metadata: `{"spread": float, "rebate_bps": float, "post_price": float}`
- expires_at: now + 120초

### 5.9 전략10: Whale Shadow (고래 추적)

**파일**: `src/strategies/whale_shadow.py`
**데이터 소스**: WebSocket (체결 이벤트)
**requires_ws**: True

**입력**:
- WebSocket `last_trade_price` 이벤트: asset_id, price, side, size, timestamp

**로직**:
1. 체결 이벤트 모니터링
2. size >= WHALE_MIN_SIZE_USDC(500)이면 고래 주문으로 판단
3. 고래 주문 방향(side) 추종 시그널 생성
4. 고래 크기에 비례하여 confidence 조정
5. 같은 마켓에서 최근 30초 내 복수 고래 주문이 같은 방향이면 confidence 상향

**출력 Signal**:
- side: 고래와 같은 방향
- confidence: 0.45 ~ 0.7
- urgency: CRITICAL (size > 2000 USDC), HIGH (500~2000)
- metadata: `{"whale_size": float, "whale_side": str, "whale_count_30s": int}`
- expires_at: now + 60초 (고래 효과는 단기)

---

## 6. 통합 계약

> 이 섹션은 2명 이상의 에이전트(또는 모듈)가 공유하는 연결점을 정의한다.
> 모든 개발자는 여기 명시된 이름을 **그대로** 사용해야 한다. 임의 변경 금지.

### 6.1 환경변수 (.env)

```env
# === API 접속 ===
POLY_PRIVATE_KEY=0x...                          # Polygon 지갑 개인키
POLY_API_KEY=                                    # CLOB L2 API Key
POLY_API_SECRET=                                 # CLOB L2 Secret
POLY_API_PASSPHRASE=                             # CLOB L2 Passphrase
POLY_WALLET_ADDRESS=0x...                        # 지갑 주소
POLY_SIGNATURE_TYPE=0                            # 0=EOA, 1=POLY_PROXY
POLY_FUNDER_ADDRESS=                             # POLY_PROXY일 때만

# === 실행 모드 ===
DRY_RUN=true                                     # true: 드라이런, false: 실거래
LOG_LEVEL=INFO                                   # DEBUG, INFO, WARNING, ERROR

# === 전략 토글 (1=활성, 0=비활성) ===
STRATEGY_AMBIGUITY=1
STRATEGY_ORACLE_FEAR=1
STRATEGY_CONTRARIAN=1
STRATEGY_CORRELATED=1
STRATEGY_LIQUIDITY_VACUUM=1
STRATEGY_SETTLEMENT_DECAY=1
STRATEGY_EVENT_CASCADE=1
STRATEGY_MAKER_REBATE=1
STRATEGY_WHALE_SHADOW=1
```

### 6.2 파일 경로

| 용도 | 경로 | 소유 |
|------|------|------|
| 엔트리포인트 | `src/main.py` | backend |
| 공유 타입 | `src/shared/types.py` | architect (읽기전용 for 개발자) |
| 설정 | `config.py` | backend |
| DB 파일 | `data/reaper.db` | 런타임 자동 생성 |
| 환경변수 템플릿 | `.env.example` | backend |

### 6.3 API 엔드포인트 URL (상수)

```python
# config.py에 정의, 모든 모듈이 참조
CLOB_HOST     = "https://clob.polymarket.com"
GAMMA_HOST    = "https://gamma-api.polymarket.com"
DATA_HOST     = "https://data-api.polymarket.com"
WS_MARKET_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
WS_USER_URL   = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
```

### 6.4 WebSocket 메시지 형식

**구독 요청** (ws_manager.py가 전송):
```json
{
  "auth": {},
  "assets_ids": ["<token_id_1>", "<token_id_2>"],
  "type": "market"
}
```

**수신 이벤트** (ws_manager.py가 파싱 후 콜백 호출):
- `last_trade_price`: `{"event_type": "last_trade_price", "asset_id": str, "price": str, "side": str, "size": str, "timestamp": str}`
- `price_change`: `{"event_type": "price_change", "asset_id": str, "market": str, "changes": [...], "timestamp": str}`
- `book`: 오더북 전체 스냅샷

### 6.5 Signal 흐름 인터페이스

```
Strategy.analyze() → Signal → SignalQueue.put()
                                    ↓
                              MetaBrain.consume()
                                    ↓
                              TradeDecision
                                    ↓
                              RiskSentinel.evaluate()
                                    ↓
                              RiskApproval
                                    ↓
                              Executor.execute()
                                    ↓
                              TradeResult → DB.record_trade()
```

**데이터 타입 흐름**: `Signal → TradeDecision → RiskApproval → TradeResult`
이 4개 타입은 `src/shared/types.py`에 정의되어 있다.

### 6.6 DB 테이블명

| 테이블 | 용도 |
|--------|------|
| `signals` | 전략 시그널 기록 |
| `trades` | 체결 거래 기록 |
| `portfolio` | 포지션 스냅샷 |
| `daily_stats` | 일별 통계 |

### 6.7 모듈 간 의존성

```
config.py ← 모든 모듈
src/shared/types.py ← 모든 모듈
src/api/* ← src/core/engine.py, src/data/market_cache.py
src/data/market_cache.py ← src/strategies/*, src/core/meta_brain.py
src/data/db.py ← src/core/engine.py, src/portfolio/tracker.py
src/strategies/* → src/core/signal_queue.py (Signal 생산)
src/core/signal_queue.py → src/core/meta_brain.py (Signal 소비)
src/core/meta_brain.py → src/core/risk_sentinel.py (TradeDecision)
src/core/risk_sentinel.py → src/core/executor.py (RiskApproval)
src/core/executor.py → src/api/clob_client.py (주문 실행)
src/portfolio/tracker.py ← src/core/risk_sentinel.py (포지션 조회)
```

### 6.8 Rate Limit 계약

| 대상 | 제한 | 우리 목표 |
|------|------|-----------|
| 공개 API (Gamma/CLOB 공개) | 100 req/분 | 최대 65 req/분 |
| CLOB 주문 | 60 orders/분 | 최대 20 orders/분 |
| CLOB 전체 | 3,000 req/10분 | 최대 1,500 req/10분 |
| 배치 주문 | 15개/콜 | 미사용 (단건 위주) |

---

## 7. 설계 결정 근거

### 7.1 왜 py-clob-client를 run_in_executor로 래핑하는가?

py-clob-client는 동기 라이브러리(requests 기반)이다. asyncio 이벤트 루프를 블로킹하지 않기 위해 `loop.run_in_executor(None, sync_call)`로 스레드풀에 위임한다. aiohttp 직접 구현보다 SDK의 서명/인증 로직을 재사용하는 것이 안전하다.

### 7.2 왜 Gamma/Data API는 aiohttp 직접 사용하는가?

Gamma/Data API는 인증이 불필요하거나 단순 GET 요청이다. aiohttp로 직접 호출하면 run_in_executor 오버헤드 없이 네이티브 async 성능을 얻는다.

### 7.3 왜 Meta Brain이 strategies/ 밖에 있는가?

Meta Brain은 시그널 소비자이지 생산자가 아니다. 다른 9개 전략과 달리 마켓 데이터를 직접 분석하지 않고 시그널을 합성한다. core에 배치하여 signal_queue와 executor 사이의 파이프라인 역할을 명확히 한다.

### 7.4 왜 DB에 aiosqlite를 쓰는가?

요구사항에 SQLite가 명시되어 있고, asyncio 환경에서 블로킹 없이 사용하려면 aiosqlite가 필수다. 외부 DB 서버 의존성을 없앤다.

### 7.5 왜 수수료 0인 마켓에서 Maker Rebate를 제외하는가?

Oracle 보고서에 따르면 "대부분의 마켓은 수수료 0%"이다. 수수료가 0이면 리베이트도 0이다. Maker Rebate 전략은 fee_rate_bps > 0인 마켓에서만 동작해야 한다.

### 7.6 왜 postOnly와 FOK/FAK를 분리하는가?

Oracle 보고서에 "postOnly와 FOK/FAK 동시 설정 불가 (거부됨)"이 명시되어 있다. Sniper(FOK)와 Patient(postOnly/GTC)를 완전히 분리하여 이 제약을 준수한다.

### 7.7 왜 테스트넷이 없는가?

Oracle 보고서: "Polymarket은 별도의 공개 테스트넷 환경을 제공하지 않습니다." DRY_RUN 모드가 유일한 안전 테스트 방법이다. DRY_RUN에서는 주문 전송 없이 가상 체결을 기록한다.

---

## 8. 에러 처리 및 복구

### 8.1 API 에러

| HTTP 코드 | 대응 |
|-----------|------|
| 429 | 지수 백오프 (1s → 2s → 4s, 최대 3회) |
| 401/403 | 로그 경고, API 키 재발급 필요 알림 |
| 500+ | 1회 재시도 후 스킵, 다음 polling 주기에 재시도 |
| 타임아웃 | 10초 timeout, 1회 재시도 |

### 8.2 WebSocket 복구

1. 연결 끊김 → 자동 재연결 (지수 백오프, 최대 30초)
2. 재연결 후 기존 구독 목록 자동 재구독
3. 30초 이상 무메시지 → 연결 끊김으로 간주, 재연결
4. 5회 연속 재연결 실패 → REST 폴링 폴백 모드 전환

### 8.3 Graceful Shutdown

1. SIGINT/SIGTERM 수신
2. 신규 시그널 생성 중단
3. 진행 중인 주문 완료 대기 (최대 10초)
4. WebSocket 연결 종료
5. DB 커밋 및 종료
6. 로그 기록

---

## 9. 의존성

```
# requirements.txt
py-clob-client>=0.15.0        # Polymarket 공식 Python SDK
aiohttp>=3.9.0                 # 비동기 HTTP/WebSocket
aiosqlite>=0.19.0              # 비동기 SQLite
websockets>=12.0               # WebSocket 클라이언트 (ws_manager)
```

**표준 라이브러리 (별도 설치 불필요)**:
- asyncio, statistics, json, os, time, datetime, dataclasses, enum, logging, signal, hashlib, hmac, base64, math

---

## 10. 보안 고려사항

- 개인키(`POLY_PRIVATE_KEY`)는 .env에만 저장, 코드/로그에 절대 노출 금지
- .env는 .gitignore에 반드시 포함
- API 시크릿은 메모리에서 Config 인스턴스로만 접근
- DB 파일은 로컬 전용, 네트워크 공유 금지
- L2 서명은 30초 만료 (타임스탬프 동기화 필요)
- DRY_RUN=true 기본값으로 실수 방지

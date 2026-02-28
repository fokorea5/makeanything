# DESIGN.md — Polymarket Reaper Bot v1.1

**작성일**: 2026-02-17
**작성자**: Architect Agent
**기반**: .plan.md (v1.1, 42 AC), oracle_report.md, critique_report.md
**버전**: v1.1 — 듀얼 리액터 3단계 퍼널 재설계

---

## 1. 아키텍처 개요

### 듀얼 리액터 3단계 퍼널 + Meta Brain Golden Cross

v1.0의 "10전략 독립 병렬 → Priority Queue → Meta Brain" 구조를 폐기한다.
v1.1은 두 개의 독립 리액터(Alpha/Omega)가 각자의 실행 경로를 가지며, Meta Brain이 교차 시그널을 감지하여 증폭하는 구조다.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Trading Engine (asyncio)                            │
│                                                                         │
│  ┌────────────┐  ┌────────────┐                                         │
│  │ REST Poller│  │ WS Manager │   Data Sources (CLOB / Gamma / Data)   │
│  └─────┬──────┘  └─────┬──────┘                                         │
│        │               │                                                │
│        ▼               ▼                                                │
│  ┌──────────────────────────────┐                                       │
│  │     Market Data Cache        │                                       │
│  └──────┬──────────────┬────────┘                                       │
│         │              │                                                │
│    ┌────┴────┐    ┌────┴────┐                                           │
│    │         │    │         │                                           │
│    ▼         │    ▼         │                                           │
│ ┌──────────────────────┐  ┌─────────────────────┐                       │
│ │  REACTOR α            │  │  REACTOR Ω           │                     │
│ │  (Slow Brain)         │  │  (Fast Brain)        │                     │
│ │                       │  │                      │                     │
│ │  Stage 1 (5min REST)  │  │  Complete Set WS     │                     │
│ │  ┌─────────────────┐  │  │  실시간 차익 탐지     │                     │
│ │  │Ambiguity        │  │  │  합 > 1.03 | < 0.97 │                     │
│ │  │Oracle Fear      │  │  │                      │                     │
│ │  │Market Age★      │  │  │  ┌─────────┐        │                     │
│ │  └────────┬────────┘  │  │  │Sniper   │        │                     │
│ │           ▼            │  │  │Executor │        │                     │
│ │  Target List (~50)    │  │  │(FOK)    │        │                     │
│ │           │            │  │  └────┬────┘        │                     │
│ │  Stage 2 (60s REST)   │  │       │              │                     │
│ │  ┌─────────────────┐  │  └───────┼──────────────┘                     │
│ │  │Contrarian+주말   │  │         │                                    │
│ │  │Correlated(분석)  │  │    ┌────┴─────────────────────┐              │
│ │  │Crowding★        │  │    │  Signal Queue             │              │
│ │  └────────┬────────┘  │    │  (asyncio.PriorityQueue)  │              │
│ │           ▼            │    └────┬──────────────────────┘              │
│ │  Hit List (~10)       │         │                                     │
│ │  + WS 구독 등록       │         ▼                                     │
│ │           │            │  ┌─────────────────────┐                     │
│ │  Stage 3 (실시간 WS)  │  │  Meta Brain          │                    │
│ │  ┌─────────────────┐  │  │  Golden Cross 탐지   │                    │
│ │  │Liquidity Vacuum │  │  │  α Hit + Ω 이상     │                    │
│ │  │Vol-Price Div★   │  │  │  → Kelly 1.5x 증폭  │                    │
│ │  └────────┬────────┘  │  └──────────┬──────────┘                     │
│ │           │            │             │                                │
│ │           ▼            │             ▼                                │
│ │  Signal Queue에 투입  │  ┌──────────────────────┐                    │
│ └───────────────────────┘  │  Frequency Governor   │                    │
│                             │  TURBO/NORMAL/STEALTH │                    │
│                             │  /AUTO                │                    │
│                             └──────────┬───────────┘                    │
│                                        │                                │
│                             ┌──────────▼───────────┐                    │
│                             │  Risk Sentinel (5층)  │                   │
│                             │  Kelly → Single →     │                   │
│                             │  Total → Circuit →    │                   │
│                             │  DD Throttle          │                   │
│                             └──────────┬───────────┘                    │
│                                        │                                │
│                             ┌──────────▼───────────┐                    │
│                             │  Dual Executor        │                   │
│                             │  ┌────────┐ ┌───────┐│                   │
│                             │  │Sniper  │ │Patient││                   │
│                             │  │FOK     │ │GTC    ││                   │
│                             │  └────────┘ └───────┘│                   │
│                             └──────────────────────┘                    │
│                                                                         │
│  ┌──────────────────────────────────────┐                               │
│  │  Portfolio Tracker + DB Logger       │                               │
│  └──────────────────────────────────────┘                               │
│                                                                         │
│  [중복 방지] Ω FOK 실행 시 → 해당 마켓 α 시그널 큐 소거 (AC-40)        │
│  [유지비용] Kelly Sizer에서 holding cost 차감 (AC-41)                   │
│  [실행비용] 기대이익 - 수수료 > $0.50 필터 (AC-42)                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 핵심 변경점 (v1.0 → v1.1)

| 항목 | v1.0 | v1.1 |
|------|------|------|
| 전략 수 | 10 독립 병렬 | 6 코어 + 3 보조, 3단계 퍼널 |
| 리액터 | 단일 파이프라인 | 듀얼 (Alpha + Omega) |
| Meta Brain | 수렴 탐지 전용 | Golden Cross (Alpha+Omega 교차) |
| Risk Sentinel | 6층 (Correlation Guard 포함) | 5층 (Correlation Guard → Correlated 전략 흡수) |
| Frequency Governor | 없음 | 4모드 (TURBO/NORMAL/STEALTH/AUTO) |
| 유지비용 | 미반영 | Kelly Sizer에서 기회비용 차감 |
| 중복 방지 | 없음 | 마켓별 주문 상태 추적 + Omega 우선 |
| 실행 비용 필터 | 없음 | 기대이익 > 수수료 + $0.50 |

---

## 2. 디렉토리 구조

```
polymarket-reaper/
├── DESIGN.md                          # 이 문서 (v1.1)
├── .plan.md                           # 프로젝트 계획 (v1.1)
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
│   │   └── types.py                   # 공유 타입 (Enum, dataclass) — 설계자 전용
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── clob_client.py             # CLOB API async 래퍼 (py-clob-client)
│   │   ├── gamma_client.py            # Gamma API async 래퍼 (aiohttp)
│   │   ├── data_client.py             # Data API async 래퍼 (aiohttp)
│   │   └── ws_manager.py             # WebSocket 매니저 (market + user 채널)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py                  # Trading Engine (듀얼 리액터 오케스트레이션)
│   │   ├── signal_queue.py            # Priority Signal Queue
│   │   ├── meta_brain.py              # Meta Brain (Golden Cross 탐지)
│   │   ├── risk_sentinel.py           # Risk Sentinel (5층 방어)
│   │   ├── executor.py                # Dual Executor (Sniper + Patient)
│   │   └── frequency_governor.py      # Frequency Governor (4모드)
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseStrategy 추상 클래스
│   │   ├── ambiguity.py               # Stage 1: Ambiguity Scoring
│   │   ├── oracle_fear.py             # Stage 1: Oracle Fear Premium
│   │   ├── contrarian.py              # Stage 2: Contrarian + 주말 드리프트
│   │   ├── correlated.py              # Stage 2: Correlated Markets (분석 전용)
│   │   ├── liquidity_vacuum.py        # Stage 3: Liquidity Vacuum (WS)
│   │   └── complete_set.py            # Reactor Omega: Complete Set Arbitrage (WS)
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
│   └── reaper.db                      # SQLite DB (런타임 생성)
│
└── tests/
    ├── __init__.py
    ├── test_strategies.py             # 전략 단위 테스트
    ├── test_risk.py                   # Risk Sentinel 테스트
    ├── test_meta_brain.py             # Meta Brain 테스트
    ├── test_executor.py               # Executor 테스트
    ├── test_frequency_governor.py     # Frequency Governor 테스트
    └── test_holding_cost.py           # 유지비용/실행비용 테스트
```

**v1.0 대비 제거된 파일**: `settlement_decay.py`, `event_cascade.py`, `maker_rebate.py`, `whale_shadow.py`
**v1.1 신규 파일**: `complete_set.py`, `frequency_governor.py`, `test_frequency_governor.py`, `test_holding_cost.py`

---

## 3. 모듈 역할 상세

### 3.1 `config.py` — 통합 설정

환경변수(.env)를 읽고 모든 파라미터를 통합 관리한다. 모든 모듈은 `from config import Config`로 설정에 접근한다.

**역할**:
- `.env` 파일을 `os.environ`으로 직접 읽기 (dotenv 미사용)
- API 키, 지갑 주소 등 시크릿 관리
- 전략별 파라미터 기본값 정의
- 리스크/Frequency 파라미터 중앙 관리
- DRY_RUN 모드 플래그

**핵심 설정 구조**:
```python
class Config:
    # === API 접속 ===
    CLOB_HOST: str            # "https://clob.polymarket.com"
    GAMMA_HOST: str           # "https://gamma-api.polymarket.com"
    DATA_HOST: str            # "https://data-api.polymarket.com"
    WS_MARKET_URL: str        # "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    WS_USER_URL: str          # "wss://ws-subscriptions-clob.polymarket.com/ws/user"

    # === 인증 ===
    PRIVATE_KEY: str
    POLY_API_KEY: str
    POLY_API_SECRET: str
    POLY_API_PASSPHRASE: str
    WALLET_ADDRESS: str
    SIGNATURE_TYPE: int       # 0=EOA, 1=POLY_PROXY
    FUNDER_ADDRESS: str       # POLY_PROXY일 때만

    # === Risk Sentinel ===
    KELLY_FRACTION: float     # 0.4
    MAX_SINGLE_MARKET: float  # 0.15
    MAX_TOTAL_EXPOSURE: float # 0.60
    DAILY_LOSS_LIMIT: float   # 0.08
    DD_THROTTLE_5: float      # 0.05  (x0.5)
    DD_THROTTLE_10: float     # 0.10  (x0.25)
    DD_HALT_15: float         # 0.15  (중단)

    # === Frequency Governor ===
    FREQUENCY_MODE: str       # "TURBO" | "NORMAL" | "STEALTH" | "AUTO"
    # TURBO:   Stage1 180s / Stage2 30s / Kelly x1.0
    # NORMAL:  Stage1 300s / Stage2 60s / Kelly x0.7
    # STEALTH: Stage1 600s / Stage2 120s / Kelly x0.4
    # AUTO:    DD 기반 자동 전환
    AUTO_DD_TURBO: float      # 0.03  (DD < 3% → TURBO)
    AUTO_DD_NORMAL: float     # 0.06  (3~6% → NORMAL)
    # DD > 6% → STEALTH

    # === 유지비용 (AC-41) ===
    RISK_FREE_RATE: float     # 0.05 (연 5%)

    # === 실행 비용 (AC-42) ===
    MIN_PROFIT_THRESHOLD: float  # 0.50 (USDC)

    # === 엔진 ===
    DRY_RUN: bool             # True (기본값)
    DB_PATH: str              # "data/reaper.db"
    LOG_LEVEL: str            # "INFO"

    # === 전략 토글 ===
    STRATEGY_AMBIGUITY: bool
    STRATEGY_ORACLE_FEAR: bool
    STRATEGY_CONTRARIAN: bool
    STRATEGY_CORRELATED: bool
    STRATEGY_LIQUIDITY_VACUUM: bool
    STRATEGY_COMPLETE_SET: bool

    # === 전략 파라미터 ===
    AMBIGUITY_THRESHOLD: float              # 0.6
    AMBIGUITY_SOURCE_PENALTY: float         # 0.2
    AMBIGUITY_KEYWORDS: list[str]           # config.py에 리스트로 관리 (AC-07)
    ORACLE_FEAR_DISCOUNT: float             # 0.05
    ORACLE_FEAR_KEYWORDS: list[str]         # config.py에 리스트로 관리
    CONTRARIAN_Z_THRESHOLD: float           # 2.0
    CONTRARIAN_WEEKEND_STDEV_MULT: float    # 2.0 (주말 변동 > 평일 stdev x 2)
    CONTRARIAN_WEEKEND_BONUS: float         # 0.10
    CORRELATED_CONDITIONAL_THRESHOLD: float # 1.5
    CORRELATED_SUM_THRESHOLD: float         # 0.02 (합 > 1.02 or < 0.98)
    LIQUIDITY_SPREAD_THRESHOLD: float       # 0.05
    LIQUIDITY_DEPTH_RATIO: float            # 3.0
    COMPLETE_SET_THRESHOLD: float           # 0.03 (합 > 1.03 or < 0.97)
    MARKET_AGE_HOURS: int                   # 48
    MARKET_AGE_BONUS: float                 # 0.15
    CROWDING_THRESHOLD: float               # 0.80 (80%)
    CROWDING_BONUS: float                   # 0.10
    VOL_PRICE_VOLUME_SURGE: float           # 3.0 (3배)
    VOL_PRICE_VOLUME_DROUGHT: float         # 0.3 (30%)
    VOL_PRICE_PRICE_THRESHOLD: float        # 0.02 (흡수 괴리)
    VOL_PRICE_PRICE_VACUUM: float           # 0.05 (진공 괴리)

    # === Meta Brain ===
    META_SIGNAL_WINDOW_SEC: int             # 600
    META_GOLDEN_CROSS_KELLY_MULT: float     # 1.5

    # === 전략별 가중치 ===
    WEIGHT_AMBIGUITY: float                 # 1.2
    WEIGHT_ORACLE_FEAR: float               # 1.0
    WEIGHT_CONTRARIAN: float                # 1.1
    WEIGHT_CORRELATED: float                # 1.3
    WEIGHT_LIQUIDITY_VACUUM: float          # 0.9
    WEIGHT_COMPLETE_SET: float              # 1.4

    # === Executor ===
    SLIPPAGE_TOLERANCE: float               # 0.02
    SNIPER_MAX_RETRY: int                   # 1
    PATIENT_POST_ONLY: bool                 # True
```

### 3.2 `src/api/clob_client.py` — CLOB API Async 래퍼

py-clob-client(동기 라이브러리)를 `asyncio.get_event_loop().run_in_executor(None, ...)`로 async 래핑한다.
주문 생성/취소/서명 로직만 SDK를 사용하고, 공개 데이터 조회는 가능하면 aiohttp를 직접 사용한다.

**역할**:
- py-clob-client ClobClient 인스턴스를 내부에 보유
- 모든 메서드를 async로 노출
- 지수 백오프 재시도 (HTTP 429 대응, 최대 3회)
- Rate limit 내부 추적: asyncio.Semaphore + 슬라이딩 윈도우

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
async cancel_market_orders(condition_id: str) -> bool    # AC-40: 특정 마켓 주문 전체 취소
async get_open_orders(market: str | None) -> list[dict]
async get_trades(market: str | None) -> list[dict]
```

**Rate Limit 관리**:
- 공개 API: `asyncio.Semaphore(50)` + 슬라이딩 윈도우, 100 req/분 중 65 req/분 사용 목표
- 주문 API: 별도 `asyncio.Semaphore(15)`, 60 orders/분 중 20 orders/분 사용 목표
- HTTP 429 → 2^n초 백오프 (1s → 2s → 4s, 최대 3회)

### 3.3 `src/api/gamma_client.py` — Gamma API Async 래퍼

마켓 메타데이터, 태그, 이벤트 정보를 aiohttp로 직접 비동기 조회한다.

**주요 메서드**:
```
async get_markets(active: bool, limit: int, offset: int, order: str) -> list[GammaMarket]
async get_market_by_id(market_id: int) -> GammaMarket
async get_market_by_slug(slug: str) -> GammaMarket
async get_events(limit: int, offset: int) -> list[GammaEvent]
async get_event_by_id(event_id: int | str) -> GammaEvent
async get_tags() -> list[GammaTag]
```

**GammaMarket에서 추출하는 v1.1 핵심 필드**:
- `id`, `question`, `conditionId`, `slug`, `resolutionSource`, `endDate`, `startDate`
- `description`, `liquidity`, `volume`, `outcomes`, `outcomePrices`
- `active`, `closed`, `tags`, `negRisk`, `negRiskMarketID`

### 3.4 `src/api/data_client.py` — Data API Async 래퍼

포지션, 포트폴리오 가치, 거래내역, 마켓 홀더를 aiohttp로 직접 비동기 조회한다.

**주요 메서드**:
```
async get_positions(wallet: str, market: str | None) -> list[PositionData]
async get_portfolio_value(wallet: str) -> float
async get_activity(wallet: str) -> list[dict]
async get_holders(token_id: str) -> list[dict] | None
    # AC-13: /holders 엔드포인트. 404/실패 시 None 반환 (graceful degradation)
```

### 3.5 `src/api/ws_manager.py` — WebSocket 매니저

Market 채널과 User 채널의 WebSocket 연결을 관리한다.

**역할**:
- Market 채널: 가격 변화, 체결, 오더북 이벤트 수신 (인증 불필요)
- User 채널: 주문 상태 변경 수신 (L2 인증)
- 자동 재연결 (지수 백오프: 1s → 2s → 4s → 8s → 최대 30s)
- 재연결 후 기존 구독 목록 자동 재구독 (AC-04)
- 이벤트를 등록된 콜백 함수로 디스패치

**주요 메서드**:
```
async connect_market(asset_ids: list[str], on_event: Callable) -> None
async connect_user(on_event: Callable) -> None
async subscribe_assets(asset_ids: list[str]) -> None    # 추가 구독 (Stage 2 → 3 전환 시)
async unsubscribe_all_and_reconnect(new_ids: list[str]) -> None  # WS는 unsubscribe 미지원이므로 재연결
async close() -> None
```

**이벤트 디스패치**:
- `last_trade_price` → Liquidity Vacuum (거래량 추적), Complete Set (가격 갱신), Vol-Price Divergence 로직
- `price_change` → Market Data Cache 업데이트, Complete Set (합산 가격 재계산)
- `book` → Liquidity Vacuum (오더북 분석)

**재연결 로직** (AC-04):
1. 연결 끊김 감지 (30초 무메시지 = heartbeat 타임아웃)
2. 지수 백오프로 재연결 시도
3. 재연결 성공 시 `_subscribed_assets` 리스트로 자동 재구독
4. 5회 연속 실패 시 `on_ws_failure` 콜백 호출 → Engine이 REST 폴링 폴백

### 3.6 `src/core/engine.py` — Trading Engine

듀얼 리액터의 오케스트레이션을 담당하는 메인 루프.

**역할**:
- Reactor Alpha (Slow Brain) 3단계 퍼널 구동
- Reactor Omega (Fast Brain) 실시간 차익 탐지 구동
- Meta Brain 시그널 소비/Golden Cross 탐지
- Signal Queue → Frequency Governor → Risk Sentinel → Executor 파이프라인
- 중복 방지 로직 (AC-39, AC-40)
- Graceful shutdown (SIGINT/SIGTERM)

**실행 흐름** (AC-01):
```
async def run():
    1. Config 로드, DB 초기화
    2. API 클라이언트 초기화 (clob, gamma, data)
    3. Frequency Governor 초기화
    4. Market Data Cache 초기화 (Gamma API로 활성 마켓 로드)
    5. Portfolio Tracker 초기화 (포지션 동기화)
    6. WebSocket 연결 (market 채널)
    7. asyncio.gather(
         _run_reactor_alpha(),     # Slow Brain 3단계 퍼널
         _run_reactor_omega(),     # Fast Brain 실시간 차익
         _consume_signals(),       # Signal Queue → Meta Brain → Risk → Executor
         _portfolio_sync(),        # 주기적 포지션 동기화 (120초)
         _governor_auto_check(),   # AUTO 모드 DD 체크 (60초)
         _health_check(),          # 시스템 헬스체크 (60초)
       )
```

**Reactor Alpha 실행 흐름**:
```
async def _run_reactor_alpha():
    while running:
        # Stage 1 — 스캔 (Governor 주기에 따라)
        stage1_interval = frequency_governor.get_stage1_interval()
        await asyncio.sleep(stage1_interval)
        target_list = await _run_stage1(all_markets)  # Ambiguity + Oracle Fear + Market Age

        # Stage 2 — 정밀 분석 (Governor 주기에 따라)
        stage2_interval = frequency_governor.get_stage2_interval()
        await asyncio.sleep(stage2_interval)
        hit_list = await _run_stage2(target_list)     # Contrarian + Correlated + Crowding

        # Stage 3 — 실시간 모니터링 (WS 구독)
        await ws_manager.subscribe_assets([m.yes_token_id for m in hit_list])
        # Stage 3 전략(Liquidity Vacuum, Vol-Price Divergence)은 WS 이벤트 콜백으로 동작
        # 시그널 생성 시 Signal Queue에 투입
```

**Reactor Omega 실행 흐름**:
```
async def _run_reactor_omega():
    # Complete Set 전략이 WS 이벤트를 직접 수신
    # event_id별 마켓 가격 합을 실시간 모니터링
    # 차익 발견 시 → Sniper Executor 즉시 실행 (Signal Queue 우회)
    # 실행 후 → 해당 마켓의 Alpha 시그널 큐 소거 (AC-40)
    # 동시에 → Meta Brain에 Omega 이상 감지 알림 (Golden Cross 판단용)
```

**중복 방지 로직** (AC-39):
```
async def _check_duplicate(signal: Signal) -> bool:
    """동일 마켓 중복 주문 방지. True면 스킵."""
    market_id = signal.condition_id
    # 1. 미체결 GTC가 있으면 → 새 시그널 스킵
    open_orders = await clob_client.get_open_orders(market=market_id)
    if open_orders:
        return True
    # 2. 기존 포지션 확인
    position = await portfolio_tracker.get_position(market_id)
    if position:
        if _same_direction(position, signal):
            return True  # 같은 방향 → 스킵
        else:
            # 반대 방향 → 기존 포지션 청산 후 신규 진입
            await _close_position(position)
            return False
    return False
```

**Omega 우선 로직** (AC-40):
```
async def _on_omega_execution(market_id: str):
    """Omega FOK 실행 후 호출. Alpha 시그널 큐에서 해당 마켓 시그널 제거."""
    signal_queue.purge_market(market_id)
```

### 3.7 `src/core/signal_queue.py` — Priority Signal Queue

asyncio.PriorityQueue 기반. 시그널의 urgency에 따라 우선순위를 부여한다.

**우선순위** (낮을수록 먼저 처리):
```
CRITICAL = 1   # Liquidity Vacuum (극단적 스프레드)
HIGH     = 2   # Contrarian (|Z| > 3), Complete Set 이상 감지
MEDIUM   = 3   # 표준 시그널 (Ambiguity, Oracle Fear, Contrarian 일반)
LOW      = 4   # 약한 시그널
```

**주요 메서드**:
```
async put(signal: Signal) -> None            # 전략이 시그널 투입
async get() -> Signal                         # Meta Brain이 소비
def qsize() -> int                            # 대기 시그널 수
async drain_expired() -> int                  # 만료 시그널 제거 (30초 주기)
def purge_market(condition_id: str) -> int    # AC-40: 특정 마켓 시그널 전체 제거
```

**시그널 만료**: 각 시그널의 `expires_at` 필드로 판정. `drain_expired()`가 30초마다 실행.

### 3.8 `src/core/meta_brain.py` — Meta Brain (Golden Cross)

Signal Queue에서 시그널을 소비하고, Alpha와 Omega의 교차 시그널을 탐지하여 증폭한다.

**역할** (AC-20~22):
- 시그널 버퍼링: market_id별 최근 시그널 수집 (윈도우: `META_SIGNAL_WINDOW_SEC`, 기본 600초)
- Alpha 시그널 수집: Stage 1~3 전략의 시그널
- Omega 이상 감지 기록: Complete Set이 이상을 감지한 market_id를 추적
- **Golden Cross 판정**: Alpha Hit List 마켓에서 Omega도 이상 감지 → confidence 보너스 + Kelly 1.5x
- 전략별 가중치 적용 후 가중 평균 confidence 산출
- TradeDecision 생성 → Risk Sentinel로 전달

**Golden Cross 로직** (AC-21):
```
1. Alpha 시그널 도착
2. 해당 market_id에 대해 Omega도 이상 감지 기록이 있는지 확인
3. 둘 다 존재 → Golden Cross!
   a. confidence += 0.10 (보너스)
   b. golden_cross = True (Kelly 1.5x 플래그)
4. 전략별 가중치로 가중 평균 confidence 산출
5. TradeDecision 생성 (golden_cross 플래그 포함)
```

**Omega 시그널 처리**:
Omega는 차익 기회 발견 시 Sniper Executor로 직접 실행한다 (Signal Queue 우회).
다만 Omega가 이상을 감지하면 Meta Brain에 `notify_omega_anomaly(market_id, event_id)` 호출.
이 정보는 Golden Cross 판정에만 사용되며, Omega의 실행을 지연시키지 않는다.

**전략별 가중치** (config.py에서 관리, 런타임 변경 가능):
| 전략 | 가중치 | 이유 |
|------|--------|------|
| Ambiguity | 1.2 | 구조적 미스프라이싱, 장기 엣지 |
| Oracle Fear | 1.0 | 이벤트 기반, 중간 신뢰도 |
| Contrarian | 1.1 | 통계적 근거 |
| Correlated | 1.3 | 논리적 불일치, 높은 신뢰도 |
| Liquidity Vacuum | 0.9 | 단기 신호, 노이즈 가능 |
| Complete Set | 1.4 | 수학적 차익, 최고 신뢰도 |

### 3.9 `src/core/risk_sentinel.py` — Risk Sentinel (5층 방어)

TradeDecision이 5개의 리스크 레이어를 순서대로 통과해야 Executor에 도달한다. 하나라도 거부하면 거래가 차단된다.

**5층 구조** (AC-23~27):

```
TradeDecision
    │
    ▼
┌───────────────────────────────┐
│ Layer 1: Kelly Sizer          │  Fractional Kelly 0.4 × Governor 배수
│ (포지션 사이징 + 유지비용)     │  + 유지비용 차감 (AC-41)
│                               │  + 실행 비용 필터 (AC-42)
│                               │  + Golden Cross: Kelly × 1.5 (AC-21)
└───────────┬───────────────────┘
            ▼
┌───────────────────────────────┐
│ Layer 2: Single Market Cap    │  단일 마켓 <= bankroll × 0.15
│ (집중도 검사)                  │  기존 포지션 + 신규 size 합산 체크
└───────────┬───────────────────┘
            ▼
┌───────────────────────────────┐
│ Layer 3: Total Exposure Cap   │  전체 <= bankroll × 0.60
│ (총 노출)                      │
└───────────┬───────────────────┘
            ▼
┌───────────────────────────────┐
│ Layer 4: Circuit Breaker      │  일일 손실 >= bankroll × 0.08
│ (일일 손실 차단)               │  → 당일 거래 전면 중단 + 기존 GTC 취소
└───────────┬───────────────────┘
            ▼
┌───────────────────────────────┐
│ Layer 5: Drawdown Throttle    │  DD >5%: size × 0.5
│ (DD 감속)                      │  DD >10%: size × 0.25
│                               │  DD >15%: 전면 중단
└───────────┴───────────────────┘
            │
            ▼
       Executor에 전달 (RiskApproval 포함)
```

**Layer 1 — Kelly Sizer 상세** (AC-23, AC-41, AC-42):
```python
# 1. 기본 Kelly 계산
edge = confidence - (1 - confidence)
odds = (1 / price) - 1
kelly_pct = KELLY_FRACTION * (edge * odds - (1 - edge)) / odds

# 2. Frequency Governor 배수 적용
governor_mult = frequency_governor.get_kelly_multiplier()
# TURBO: 1.0, NORMAL: 0.7, STEALTH: 0.4
kelly_pct *= governor_mult

# 3. Golden Cross 증폭 (AC-21)
if decision.golden_cross:
    kelly_pct *= META_GOLDEN_CROSS_KELLY_MULT  # 1.5

# 4. 유지비용 차감 (AC-41)
days_to_settlement = (end_date - now).days
holding_cost = days_to_settlement / 365 * RISK_FREE_RATE
adjusted_edge = edge - holding_cost
# adjusted_edge로 Kelly 재계산 (adjusted_edge <= 0이면 size = 0)

# 5. 포지션 크기 산출
size = max(0, kelly_pct) * bankroll
size = max(size, minimum_order_size)  # 최소 주문 크기 (마켓별)

# 6. 실행 비용 필터 (AC-42)
fee_rate = await clob_client.get_fee_rate(token_id)
expected_profit = size * adjusted_edge
fee_cost = fee_rate * size / 10000  # bps → 절대값
if expected_profit - fee_cost < MIN_PROFIT_THRESHOLD:
    return RiskApproval(approved=False, reject_reason=EXECUTION_COST)
```

**Layer 4 — Circuit Breaker 상세** (AC-26):
- daily_loss는 UTC 00:00 기준 리셋
- 서킷브레이커 작동 시:
  1. 모든 신규 주문 차단
  2. 기존 GTC 주문 전체 취소 (`clob_client.cancel_all()`)
  3. 로그 기록 + DB 저장 (daily_stats.circuit_breaker_hit += 1)

**Layer 5 — Drawdown Throttle 상세** (AC-27):
- Frequency Governor의 DD 임계값(AC-29)과 **독립 작동**
- Governor는 스캔 빈도를, Sentinel은 포지션 크기를 조절
- **두 효과는 곱셈으로 중첩**: DD 6%일 때 Governor=STEALTH(Kelly x0.4) + Sentinel=x0.5 → 최종 Kelly x0.2

**v1.0의 Layer 6 (Correlation Guard) 제거 이유**:
Correlated Markets 전략(AC-12)이 Stage 2에서 상관 분석을 직접 수행하므로, Risk Sentinel의 별도 상관 방어 레이어가 불필요해졌다. 상관 마켓의 과잉 노출은 Correlated 전략이 시그널 단계에서 방지한다.

### 3.10 `src/core/executor.py` — Dual Executor

Risk Sentinel을 통과한 TradeDecision을 실제 주문으로 변환한다.

**Sniper Executor** (AC-31):
- urgency: CRITICAL, HIGH
- 주문: FOK (Fill-Or-Kill)
- 가격: midpoint +/- `SLIPPAGE_TOLERANCE` (기본 0.02)
- 목적: Liquidity Vacuum 순간 포착, Complete Set 차익
- DRY_RUN=true: 주문 미전송, 현재 midpoint 기준 가상 체결

**Patient Executor** (AC-32):
- urgency: MEDIUM, LOW
- 주문: GTC + postOnly (메이커 전용)
- 가격: best_bid + tick (BUY) 또는 best_ask - tick (SELL)
- 목적: 유리한 가격에 진입, 리베이트 수취 가능
- 주의: postOnly와 FOK/FAK 동시 설정 불가 (Oracle 보고서 제약)

**공통** (AC-33):
- DRY_RUN=true: 실제 주문 전송하지 않고 가상 체결 기록
- 주문 결과를 DB `trades` 테이블에 기록
- 체결 실패 시 1회 재시도 후 포기 (과도한 재시도 방지)

**주요 메서드**:
```
async execute(decision: TradeDecision, approval: RiskApproval) -> TradeResult
async _sniper_execute(decision, approval) -> TradeResult    # FOK
async _patient_execute(decision, approval) -> TradeResult   # GTC+postOnly
```

**라우팅**:
```python
if decision.urgency in (SignalUrgency.CRITICAL, SignalUrgency.HIGH):
    result = await _sniper_execute(decision, approval)
else:
    result = await _patient_execute(decision, approval)
```

### 3.11 `src/core/frequency_governor.py` — Frequency Governor

거래 빈도를 Drawdown 상황에 따라 동적으로 조절한다.

**역할** (AC-28~30):
- 4개 모드: TURBO, NORMAL, STEALTH, AUTO
- 각 모드별 Stage 1/2 스캔 주기, Kelly 배수 제공
- AUTO 모드: DD 기반 자동 전환
- 런타임 모드 변경: SIGHUP 시그널 또는 DB `frequency_mode` 플래그 (AC-30)

**모드별 파라미터 테이블** (AC-28):

| 파라미터 | TURBO | NORMAL | STEALTH |
|----------|-------|--------|---------|
| Stage 1 주기 | 180초 (3분) | 300초 (5분) | 600초 (10분) |
| Stage 2 주기 | 30초 | 60초 | 120초 |
| Kelly 배수 | x1.0 | x0.7 | x0.4 |
| Omega 활성 | Yes | Yes | Yes (감시만) |

**AUTO 모드 전환 규칙** (AC-29):

| 조건 | 전환 모드 |
|------|-----------|
| DD < 3% | TURBO |
| DD 3% ~ 6% | NORMAL |
| DD > 6% | STEALTH |

**DD와 Risk Sentinel 상호작용 (비판자 MINOR-06 해소)**:
Governor와 Risk Sentinel은 DD를 **독립적으로** 참조하며, 두 효과는 **곱셈으로 중첩**된다:
- DD 5.5%: Governor=NORMAL(Kelly x0.7) + Sentinel=Layer5(>5% → x0.5) → 최종 Kelly x0.35
- DD 7%: Governor=STEALTH(Kelly x0.4) + Sentinel=Layer5(>5% → x0.5) → 최종 Kelly x0.20
- DD 11%: Governor=STEALTH(Kelly x0.4) + Sentinel=Layer5(>10% → x0.25) → 최종 Kelly x0.10
- DD 15%: Governor=STEALTH + Sentinel=Layer5(>15% → 중단) → 거래 중단

이것은 의도된 설계다. Governor는 정보 수집 빈도를, Sentinel은 자본 배분을 조절한다. 두 시스템이 각자의 영역에서 보수적으로 작동하여 이중 안전망을 형성한다.

**주요 메서드**:
```
def get_current_mode() -> FrequencyMode
def get_stage1_interval() -> float        # 초
def get_stage2_interval() -> float        # 초
def get_kelly_multiplier() -> float       # 0.4 ~ 1.0
async def check_auto_transition(current_dd: float) -> FrequencyMode | None
def set_mode(mode: FrequencyMode) -> None  # 런타임 변경
```

### 3.12 `src/strategies/base.py` — BaseStrategy 추상 클래스

모든 전략의 기반 클래스.

```python
class BaseStrategy(ABC):
    name: str                          # 전략 이름
    strategy_type: StrategyType        # Enum 값
    reactor: ReactorType               # ALPHA 또는 OMEGA
    stage: int                         # 1, 2, 3 (Alpha) 또는 0 (Omega)
    requires_ws: bool = False          # WebSocket 필요 여부
    enabled: bool = True               # 활성화 여부

    @abstractmethod
    async def analyze(self, markets: list[MarketData]) -> list[Signal]:
        """마켓 목록 분석 → 0개 이상의 시그널 반환"""
        # Stage 1: 전체 활성 마켓 입력
        # Stage 2: Target List 입력
        # Stage 3: Hit List 입력 (WS 이벤트 기반)

    async def on_ws_event(self, event: dict) -> list[Signal]:
        """WebSocket 이벤트 수신 시 (Stage 3 / Omega 전략만 오버라이드)"""
        return []

    def _create_signal(self, ...) -> Signal:
        """Signal 생성 헬퍼. reactor_source 자동 설정."""
```

### 3.13 `src/data/market_cache.py` — Market Data Cache

API 호출을 줄이기 위한 인메모리 캐시. Gamma + CLOB 데이터를 통합 보관.

**역할**:
- 활성 마켓 목록 캐시 (5분 TTL)
- event_id별 마켓 그룹핑 (Complete Set / Correlated 전략용)
- 마켓별 가격/오더북 캐시 (전략 polling 시 갱신)
- WebSocket 이벤트로 실시간 업데이트
- 마켓 생성일(startDate) 추적 (Market Age 보조지표용)

**주요 메서드**:
```
async refresh_markets() -> None              # Gamma API로 활성 마켓 새로고침
async get_market(condition_id: str) -> MarketData | None
async get_all_active_markets() -> list[MarketData]
async get_markets_by_event(event_id: str) -> list[MarketData]  # Complete Set / Correlated용
async update_price(token_id: str, price: float) -> None        # WS 이벤트용
async update_orderbook(token_id: str, book: OrderBookSnapshot) -> None
def get_event_groups() -> dict[str, list[MarketData]]          # event_id → markets
```

### 3.14 `src/data/db.py` — DB 매니저

aiosqlite를 사용한 비동기 SQLite DB 관리.

**역할**:
- 테이블 초기화 (CREATE IF NOT EXISTS)
- 시그널, 거래, 포트폴리오 상태 기록
- 드라이런 모드에서도 동일하게 기록 (`is_dry_run` 플래그)
- Frequency Governor 모드 저장/복구 (AC-30)
- 일별 통계 자동 집계 (AC-35)

**주요 메서드**:
```
async init_db() -> None                      # 테이블 생성
async record_signal(signal: Signal) -> None
async record_trade(result: TradeResult) -> None
async record_portfolio_snapshot(positions: list[Position]) -> None
async update_daily_stats(date: str, stats: DailyStats) -> None
async get_frequency_mode() -> str | None     # AC-30: DB 플래그 조회
async set_frequency_mode(mode: str) -> None
async get_daily_stats(date: str) -> DailyStats | None
```

### 3.15 `src/portfolio/tracker.py` — Portfolio Tracker

현재 포지션과 포트폴리오 상태를 추적한다.

**역할** (AC-34):
- Data API로 실제 포지션 동기화 (120초 주기)
- DRY_RUN 모드: 가상 포지션 인메모리 관리
- Risk Sentinel에 포지션 정보 제공
- 일일 P&L 계산, 총 노출 계산
- Drawdown 계산 (Governor + Sentinel 공용)

**주요 메서드**:
```
async sync_positions() -> None                     # Data API에서 동기화
async get_position(condition_id: str) -> Position | None
async get_all_positions() -> list[Position]
async get_total_exposure() -> float                # 총 노출 USDC
async get_daily_pnl() -> float                     # 오늘 실현 P&L
async get_bankroll() -> float                      # 사용 가능 잔고
async get_peak_bankroll() -> float                 # 역대 최고
async get_current_drawdown() -> float              # 현재 DD 비율
async record_virtual_trade(trade: TradeResult) -> None  # DRY_RUN용
async has_open_orders(condition_id: str) -> bool   # AC-39: 미체결 주문 존재 여부
```

---

## 4. DB 스키마

### 4.1 `signals` 테이블

```sql
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,                -- ISO 8601
    strategy        TEXT NOT NULL,                -- StrategyType enum value
    reactor_source  TEXT NOT NULL,                -- "ALPHA" | "OMEGA"
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
CREATE INDEX IF NOT EXISTS idx_signals_reactor ON signals(reactor_source, timestamp);
```

### 4.2 `trades` 테이블

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
    order_type      TEXT NOT NULL,                -- "GTC" | "FOK" | "postOnly"
    executor_mode   TEXT NOT NULL,                -- "SNIPER" | "PATIENT"
    reactor_source  TEXT NOT NULL,                -- "ALPHA" | "OMEGA"
    order_id        TEXT,                         -- Polymarket order ID (DRY_RUN 시 NULL)
    status          TEXT NOT NULL,                -- "FILLED" | "PARTIAL" | "REJECTED" | "DRY_RUN"
    confidence      REAL NOT NULL,                -- Meta Brain 최종 confidence
    golden_cross    INTEGER NOT NULL DEFAULT 0,   -- 1이면 Golden Cross 적용
    convergence     INTEGER NOT NULL DEFAULT 0,   -- 수렴 시그널 수
    signals_used    TEXT NOT NULL,                -- JSON: 사용된 signal ID 리스트
    risk_layers     TEXT NOT NULL,                -- JSON: 각 층 통과 결과
    holding_cost    REAL NOT NULL DEFAULT 0.0,    -- 유지비용 (AC-41)
    fee_cost        REAL NOT NULL DEFAULT 0.0,    -- 수수료 비용 (AC-42)
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    pnl             REAL,                         -- 실현 P&L (정산 후 업데이트)
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(condition_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_reactor ON trades(reactor_source, timestamp);
```

### 4.3 `portfolio` 테이블

```sql
CREATE TABLE IF NOT EXISTS portfolio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,                -- ISO 8601
    condition_id    TEXT NOT NULL,
    token_id        TEXT NOT NULL,
    outcome         TEXT NOT NULL,                -- "Yes" | "No"
    size            REAL NOT NULL,
    avg_price       REAL NOT NULL,
    current_price   REAL NOT NULL,
    unrealized_pnl  REAL NOT NULL,
    market_question TEXT NOT NULL,
    is_dry_run      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_portfolio_market ON portfolio(condition_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_time ON portfolio(timestamp);
```

### 4.4 `daily_stats` 테이블

```sql
CREATE TABLE IF NOT EXISTS daily_stats (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT NOT NULL UNIQUE,          -- "YYYY-MM-DD"
    total_trades        INTEGER NOT NULL DEFAULT 0,
    winning_trades      INTEGER NOT NULL DEFAULT 0,
    losing_trades       INTEGER NOT NULL DEFAULT 0,
    total_pnl           REAL NOT NULL DEFAULT 0.0,
    max_drawdown        REAL NOT NULL DEFAULT 0.0,
    peak_bankroll       REAL NOT NULL DEFAULT 0.0,
    signals_generated   INTEGER NOT NULL DEFAULT 0,
    signals_converted   INTEGER NOT NULL DEFAULT 0,
    alpha_signals       INTEGER NOT NULL DEFAULT 0,    -- Reactor Alpha 시그널 수
    omega_signals       INTEGER NOT NULL DEFAULT 0,    -- Reactor Omega 시그널 수
    golden_crosses      INTEGER NOT NULL DEFAULT 0,    -- Golden Cross 발생 수
    circuit_breaker_hit INTEGER NOT NULL DEFAULT 0,
    frequency_mode      TEXT NOT NULL DEFAULT 'NORMAL', -- 당일 최종 모드
    is_dry_run          INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 5. 전략별 입출력 명세

### 5.0 전략 분류 체계

**코어 6 전략** (Signal을 직접 생산):
| # | 전략 | Reactor | Stage | 파일 |
|---|------|---------|-------|------|
| 1 | Ambiguity Scoring | Alpha | 1 | `ambiguity.py` |
| 2 | Oracle Fear Premium | Alpha | 1 | `oracle_fear.py` |
| 3 | Contrarian + 주말 드리프트 | Alpha | 2 | `contrarian.py` |
| 4 | Correlated Markets (분석 전용) | Alpha | 2 | `correlated.py` |
| 5 | Liquidity Vacuum | Alpha | 3 | `liquidity_vacuum.py` |
| 6 | Complete Set Arbitrage | Omega | - | `complete_set.py` |

**보조 3 지표** (코어 전략의 confidence를 보강, 독립 모듈 아님):
| # | 보조 지표 | 소속 전략/위치 | Stage |
|---|-----------|---------------|-------|
| 1 | Market Age Freshness | Stage 1 공통 (engine.py에서 적용) | 1 |
| 2 | Position Crowding Index | Contrarian 전략 내부 (contrarian.py) | 2 |
| 3 | Volume-Price Divergence | Liquidity Vacuum 전략 내부 (liquidity_vacuum.py) | 3 |

보조 지표는 별도 파일이 아닌, 해당 Stage의 전략 내부 또는 engine에서 공통 적용된다.

### 5.1 Stage 1: Ambiguity Scoring (AC-07)

**파일**: `src/strategies/ambiguity.py`
**Reactor**: Alpha, Stage 1
**데이터 소스**: Gamma API (마켓 메타데이터) — Market Data Cache 경유
**polling 주기**: Governor에 따라 (TURBO: 180초, NORMAL: 300초, STEALTH: 600초)

**입력**:
- `MarketData.question`: 마켓 질문 텍스트
- `MarketData.description`: 마켓 설명
- `MarketData.resolution_source`: 해결 소스 URL
- `MarketData.end_date`: 결제일
- `MarketData.yes_price`, `MarketData.no_price`: 현재 가격

**로직**:
1. 모호 키워드 TF-IDF 스코어링 (AC-07)
   - 키워드 사전: `Config.AMBIGUITY_KEYWORDS` (config.py 리스트로 관리)
   - 기본 키워드: "might", "could", "possibly", "approximately", "around", "unclear", "ambiguous", "depending on", "subject to", "estimated", "roughly", "if", "unless"
   - TF = 키워드 출현 횟수 / 전체 단어 수
   - IDF = log(전체 마켓 수 / 해당 키워드 포함 마켓 수) — 단순화
   - keyword_score = sum(TF * IDF for each found keyword) / max_possible_score (0~1 정규화)
2. resolution source 미명시 감지 (AC-07, 비판자 MINOR-10 반영):
   - `resolution_source`가 빈 문자열 또는 null → source_penalty = `AMBIGUITY_SOURCE_PENALTY` (0.2)
3. ambiguity_score = keyword_score + source_penalty
4. ambiguity_score > `AMBIGUITY_THRESHOLD` (0.6)이면 NO 매수 시그널 (모호한 마켓은 NO가 유리)
5. confidence = min(0.8, 0.5 + ambiguity_score * 0.3)

**출력 Signal**:
- strategy: `StrategyType.AMBIGUITY`
- reactor_source: `ReactorType.ALPHA`
- side: BUY (NO 토큰)
- confidence: 0.5 ~ 0.8
- urgency: MEDIUM
- metadata: `{"ambiguity_score": float, "keyword_score": float, "keywords_found": list[str], "has_resolution_source": bool, "source_penalty": float}`
- expires_at: now + 600초

### 5.2 Stage 1: Oracle Fear Premium (AC-08)

**파일**: `src/strategies/oracle_fear.py`
**Reactor**: Alpha, Stage 1
**데이터 소스**: Gamma API (메타데이터) + CLOB API (가격) — Market Data Cache 경유

**입력**:
- `MarketData.description`, `MarketData.question`
- `MarketData.tags`: 마켓 태그
- `MarketData.yes_price`: 현재 YES 가격

**로직**:
1. 분쟁 키워드 감지 (비판자 MINOR-02 반영):
   - 키워드 사전: `Config.ORACLE_FEAR_KEYWORDS`
   - 기본 키워드: "oracle", "UMA", "dispute", "resolution", "challenged", "appealed", "contested", "arbitration"
   - 텍스트 매칭 기반 (API 분쟁 이력 미제공, oracle_report.md 확인)
2. 분쟁 키워드 발견 수에 따라 fear_score 산출
3. YES 할인 감지: 분쟁 키워드가 있는 마켓에서 YES 가격이 비정상적으로 낮으면 공포 프리미엄
4. discount = (1.0 - yes_price) 수준에서 fear_score를 가중
5. discount >= `ORACLE_FEAR_DISCOUNT` (0.05) 이면 YES 매수 시그널

**출력 Signal**:
- strategy: `StrategyType.ORACLE_FEAR`
- reactor_source: `ReactorType.ALPHA`
- side: BUY (YES 토큰)
- confidence: 0.5 ~ 0.75
- urgency: MEDIUM
- metadata: `{"fear_keywords": list[str], "fear_score": float, "discount": float, "yes_price": float}`
- expires_at: now + 600초

### 5.3 Stage 1: Market Age Freshness (AC-09) — 보조지표

**위치**: `src/core/engine.py`의 `_run_stage1()` 내부에서 공통 적용
**별도 전략 파일 없음** — Stage 1 결과에 보너스 가중치를 추가하는 보조 로직

**로직**:
1. 마켓 생성일(`MarketData.start_date`)에서 현재까지 경과 시간 계산
2. 경과 시간 < `MARKET_AGE_HOURS` (48시간)이면 → 해당 마켓의 Stage 1 시그널 confidence에 `MARKET_AGE_BONUS` (+0.15) 가산
3. Signal.metadata에 `"market_age_hours": float, "market_age_bonus_applied": bool` 추가

### 5.4 Stage 2: Contrarian Z-score + 주말 드리프트 (AC-11)

**파일**: `src/strategies/contrarian.py`
**Reactor**: Alpha, Stage 2
**데이터 소스**: CLOB API (가격 히스토리 `prices-history`, interval="1w")
**입력**: Target List 마켓만 분석

**입력**:
- `MarketData.prices_history`: 최근 1주 가격 히스토리
- `MarketData.yes_price`: 현재 가격

**로직**:
1. 가격 히스토리에서 Z-score 계산: `z = (current - mean) / stdev` (statistics 모듈)
2. **주말 드리프트 감지** (AC-11, 비판자 CRITICAL-01 반영):
   - 히스토리 포인트를 요일별로 분류
   - 금~일(주말) 가격 변동 = |price_sunday - price_friday|
   - 평일 평균 stdev 계산
   - 주말 변동 > 평일 stdev * `CONTRARIAN_WEEKEND_STDEV_MULT` (2.0) → 주말 과잉반응
   - 주말 과잉반응 감지 시 confidence += `CONTRARIAN_WEEKEND_BONUS` (0.10)
3. |Z| > `CONTRARIAN_Z_THRESHOLD` (2.0)이면 반대 포지션 시그널:
   - z > 2.0: 과매수 → BUY NO
   - z < -2.0: 과매도 → BUY YES
4. **Position Crowding Index** (AC-13) — 보조지표:
   - `data_client.get_holders(token_id)` 호출
   - API 성공 시: 상위 보유자의 비율 합산. 상위 N명이 80%+ 보유 → 쏠림
   - 쏠림 감지 시 confidence += `CROWDING_BONUS` (0.10)
   - API 실패(404 등) 시: 보조지표 비활성화, 경고 로그 (graceful degradation)

**출력 Signal**:
- strategy: `StrategyType.CONTRARIAN`
- reactor_source: `ReactorType.ALPHA`
- side: Z-score 방향의 반대
- confidence: min(0.85, 0.5 + |z| * 0.1 + weekend_bonus + crowding_bonus)
- urgency: HIGH (|z| > 3.0), MEDIUM (그 외)
- metadata: `{"z_score": float, "mean": float, "stdev": float, "is_weekend_drift": bool, "weekend_bonus": float, "crowding_pct": float | null, "crowding_bonus": float}`
- expires_at: now + 300초

### 5.5 Stage 2: Correlated Markets — 분석 전용 (AC-12)

**파일**: `src/strategies/correlated.py`
**Reactor**: Alpha, Stage 2
**데이터 소스**: Gamma API (이벤트, 태그) + CLOB API (가격)
**입력**: Target List 마켓

**핵심 설계 결정** (비판자 CRITICAL-03 반영):
AC-12는 **분석/식별만** 수행한다. 즉시 실행은 Reactor Omega의 Complete Set(AC-18)이 담당한다.
- AC-12: implied conditional 분석 + 가격 합 이상 감지 → Hit List 추가
- AC-18: 실시간 WS로 가격 합 모니터링 → 임계값 초과 시 FOK 즉시 실행
- AC-12가 감지한 "가격 합 이상"은 Hit List에 추가하여 Stage 3의 WS 모니터링 대상으로 등록한다.
- AC-12의 가격 합 임계값: 합 > 1.02 또는 < 0.98 (`CORRELATED_SUM_THRESHOLD`)
- AC-18의 차익 임계값: 합 > 1.03 또는 < 0.97 (`COMPLETE_SET_THRESHOLD`)
- AC-12 임계값이 AC-18보다 느슨하다: "이상 징후 감지"(Alpha)는 "즉시 차익"(Omega)보다 낮은 기준.

**로직**:
1. event_id별 마켓 그룹핑 (`market_cache.get_event_groups()`)
2. 각 그룹 내 마켓의 가격 합 계산:
   - 2-아웃컴 마켓: yes_price + no_price (정상 = 1.0)
   - N-아웃컴 이벤트: 모든 마켓의 YES 가격 합 (정상 = 1.0)
3. **Complete Set 이상 감지**: 합 > 1.02 또는 < 0.98 → Hit List 추가
4. **Implied conditional 분석**:
   - P(A|B) 추정 = P(A and B) / P(B) (같은 이벤트 내 관련 마켓)
   - P(A)*P(B)와 비교: 비율 > `CORRELATED_CONDITIONAL_THRESHOLD` (1.5)이면 미스프라이싱
5. 미스프라이싱 마켓에 Hit List 추가 시그널 생성

**출력 Signal**:
- strategy: `StrategyType.CORRELATED`
- reactor_source: `ReactorType.ALPHA`
- side: BUY 또는 SELL (저평가 쪽 BUY)
- confidence: 0.55 ~ 0.80
- urgency: MEDIUM (분석 결과이므로 Patient Executor 예정)
- metadata: `{"event_id": str, "correlated_markets": list[str], "implied_conditional": float, "complete_set_sum": float, "sum_deviation": float}`
- expires_at: now + 300초

### 5.6 Stage 3: Liquidity Vacuum + Vol-Price Divergence (AC-15, AC-16)

**파일**: `src/strategies/liquidity_vacuum.py`
**Reactor**: Alpha, Stage 3
**데이터 소스**: WebSocket (`book`, `price_change`, `last_trade_price` 이벤트)
**requires_ws**: True
**입력**: Hit List 마켓 (WS 구독 대상)

**입력**:
- `WSBookEvent`: 실시간 오더북 스냅샷
- `WSTradeEvent`: 실시간 체결 이벤트

**Liquidity Vacuum 로직** (AC-15):
1. 스프레드 계산: best_ask - best_bid
2. 깊이 비대칭 계산: total_bid_size vs total_ask_size (상위 5단계)
3. 스프레드 > `LIQUIDITY_SPREAD_THRESHOLD` (0.05) → 진공 감지
4. 깊이 비대칭 > `LIQUIDITY_DEPTH_RATIO` (3:1) → 한쪽 유동성 고갈
5. 빈 쪽에 GTC 리밋 주문 시그널

**Vol-Price Divergence 로직** (AC-16, 비판자 MINOR-04 반영):
- 60초 슬라이딩 윈도우로 체결 이벤트 집계
- **흡수 괴리**: 60초간 거래량 합 > 이전 60초의 `VOL_PRICE_VOLUME_SURGE` (3배)인데 가격 변동 < `VOL_PRICE_PRICE_THRESHOLD` (0.02) → 대량 매수/매도 흡수 감지
- **진공 괴리**: 거래량 < 평균의 `VOL_PRICE_VOLUME_DROUGHT` (0.3배)인데 가격 변동 > `VOL_PRICE_PRICE_VACUUM` (0.05) → 유동성 부재 가격 이동
- Vol-Price Divergence 감지 시 Liquidity Vacuum 시그널의 confidence += 0.10

**출력 Signal** (AC-17 → Patient Executor):
- strategy: `StrategyType.LIQUIDITY_VACUUM`
- reactor_source: `ReactorType.ALPHA`
- side: 유동성 부족 쪽의 반대 (매수벽 없으면 BUY)
- confidence: 0.45 ~ 0.75 (Vol-Price Divergence 보너스 포함 시 최대 0.85)
- urgency: CRITICAL (스프레드 > 0.10), HIGH (0.05~0.10)
- metadata: `{"spread": float, "bid_depth": float, "ask_depth": float, "asymmetry_ratio": float, "vol_price_divergence": str | null, "volume_ratio": float | null}`
- expires_at: now + 120초 (유동성 상황은 빠르게 변함)

### 5.7 Reactor Omega: Complete Set Arbitrage (AC-18, AC-19)

**파일**: `src/strategies/complete_set.py`
**Reactor**: Omega (Fast Brain)
**데이터 소스**: WebSocket (`price_change` 이벤트) — 실시간
**requires_ws**: True

**입력**:
- 같은 event_id에 속한 마켓들의 실시간 가격 (WS)
- `market_cache.get_event_groups()`: event_id → markets 매핑

**로직** (AC-18):
1. WS `price_change` 이벤트 수신 시 해당 event_id의 모든 마켓 가격 합 재계산
2. 2-아웃컴: yes_price + no_price (보완 가격은 WS에서 실시간 갱신)
3. N-아웃컴 이벤트: 모든 YES 가격 합
4. 합 > `COMPLETE_SET_THRESHOLD + 1.0` (1.03) 또는 < `1.0 - COMPLETE_SET_THRESHOLD` (0.97) → 차익 기회
5. 차익 방향 결정:
   - 합 > 1.03: 모든 아웃컴 SELL (합이 1.0으로 수렴하면 이익)
   - 합 < 0.97: 저평가 아웃컴 BUY
6. **즉시 실행** (AC-19): Sniper Executor에 직접 전달 (Signal Queue 우회)
7. 실행 후 Meta Brain에 `notify_omega_anomaly(market_id, event_id)` 호출 (Golden Cross용)
8. 해당 마켓의 Alpha 시그널 큐 소거 (AC-40)

**출력 Signal** (Sniper Executor 직접 전달):
- strategy: `StrategyType.COMPLETE_SET`
- reactor_source: `ReactorType.OMEGA`
- side: BUY 또는 SELL (차익 방향)
- confidence: 0.70 ~ 0.95 (합 편차 크기에 비례)
- urgency: CRITICAL
- metadata: `{"event_id": str, "markets_in_set": list[str], "price_sum": float, "deviation": float, "arb_direction": str}`
- expires_at: now + 30초 (차익 기회는 매우 단기)

---

## 6. Risk Sentinel 5층 구조

(3.9절에서 상세 설명. 여기는 요약 테이블.)

| 층 | 이름 | 검사 내용 | 통과 조건 | 실패 시 |
|----|------|-----------|-----------|---------|
| 1 | Kelly Sizer | Fractional Kelly × Governor배수 × GoldenCross배수 - 유지비용 - 실행비용 | size > 0 & profit > fee + $0.50 | 거부 (KELLY_ZERO / EXECUTION_COST) |
| 2 | Single Market Cap | 해당 마켓 총 노출 | 기존 + 신규 <= bankroll × 0.15 | 거부 (SINGLE_MARKET_LIMIT) |
| 3 | Total Exposure Cap | 전체 포지션 노출 | 전체 + 신규 <= bankroll × 0.60 | 거부 (TOTAL_EXPOSURE_LIMIT) |
| 4 | Circuit Breaker | 일일 손실 | daily_loss < bankroll × 0.08 | 당일 전면 중단 + GTC 취소 |
| 5 | DD Throttle | 최고점 대비 하락 | DD < 15% | >5%: ×0.5, >10%: ×0.25, >15%: 중단 |

---

## 7. Frequency Governor 상세

(3.11절에서 상세 설명. 여기는 통합 파라미터 테이블.)

### 7.1 모드별 전체 파라미터

| 파라미터 | TURBO | NORMAL | STEALTH | AUTO |
|----------|-------|--------|---------|------|
| Stage 1 스캔 주기 | 180초 | 300초 | 600초 | DD에 따라 |
| Stage 2 스캔 주기 | 30초 | 60초 | 120초 | DD에 따라 |
| Kelly 배수 | x1.0 | x0.7 | x0.4 | DD에 따라 |
| Omega 활성 | Yes | Yes | Yes | Yes |
| 설정 방법 | 환경변수 | 환경변수 | 환경변수 | 환경변수 |
| 런타임 전환 | SIGHUP/DB | SIGHUP/DB | SIGHUP/DB | 자동 |

### 7.2 AUTO 모드 DD 전환 테이블

| Drawdown 범위 | 적용 모드 | 결합 시 Risk Sentinel Layer 5 |
|---------------|-----------|------------------------------|
| DD < 3% | TURBO (Kelly x1.0) | x1.0 (Layer 5 미적용) |
| 3% <= DD < 5% | NORMAL (Kelly x0.7) | x1.0 (Layer 5 미적용) |
| 5% <= DD < 6% | NORMAL (Kelly x0.7) | x0.5 → 실질 Kelly x0.35 |
| 6% <= DD < 10% | STEALTH (Kelly x0.4) | x0.5 → 실질 Kelly x0.20 |
| 10% <= DD < 15% | STEALTH (Kelly x0.4) | x0.25 → 실질 Kelly x0.10 |
| DD >= 15% | STEALTH | 거래 중단 |

### 7.3 런타임 모드 변경 (AC-30)

1. **SIGHUP 시그널**: `kill -HUP <pid>` → DB의 `frequency_mode` 값을 읽어 모드 전환
2. **DB 플래그**: `daily_stats.frequency_mode` 필드를 외부에서 UPDATE → 다음 체크 주기에 감지
3. AUTO 모드에서 수동 전환 시 AUTO 해제, 수동 모드 유지

---

## 8. 중복 방지 + 유지비용 + 실행 비용 필터

### 8.1 동일 마켓 중복 주문 방지 (AC-39)

**문제**: Reactor Alpha와 Omega가 동시에 같은 마켓에 시그널을 생성할 수 있다.

**규칙**:
1. 마켓에 **미체결 GTC 주문이 있으면** → 새 시그널 스킵
2. 기존 포지션이 있으면:
   - **같은 방향** 시그널 → 스킵 (중복 진입 방지)
   - **반대 방향** 시그널 → 기존 포지션 청산 후 신규 진입
3. 체크 위치: `engine.py`의 `_consume_signals()` 내부, Meta Brain 이전

### 8.2 Omega 우선 (AC-40)

**규칙**: Reactor Omega가 FOK 실행 시, 해당 마켓의 Reactor Alpha 시그널 큐를 소거한다.

**이유**: Omega는 즉시 실행(FOK)이므로 이미 포지션이 잡혔거나 실패했다. Alpha의 Patient 주문이 추가로 나가면 중복.

**구현**: `signal_queue.purge_market(market_id)` — PriorityQueue에서 해당 market_id의 시그널을 제거.
(asyncio.PriorityQueue는 중간 삭제가 불편하므로, 내부에 `_purged_markets: set[str]`를 유지하고 get() 시 필터링)

### 8.3 유지비용 반영 (AC-41)

**문제**: 장기 포지션은 자금이 동결되어 기회비용이 발생한다.

**계산**:
```
days_to_settlement = (market.end_date - now).days
holding_cost_rate = days_to_settlement / 365 * RISK_FREE_RATE  # RISK_FREE_RATE = 0.05
adjusted_edge = raw_edge - holding_cost_rate
```

**적용 위치**: Risk Sentinel Layer 1 (Kelly Sizer)
- `adjusted_edge`로 Kelly 재계산
- `adjusted_edge <= 0`이면 → size = 0 → 거부 (유지비용이 엣지를 초과)
- 결제일까지 1일인 마켓: holding_cost = 0.014% (무시 가능)
- 결제일까지 180일인 마켓: holding_cost = 2.47% (상당한 차감)

### 8.4 실행 비용 필터 (AC-42)

**문제**: 소액 거래에서 수수료가 기대이익을 초과할 수 있다.

**계산**:
```
fee_rate = await clob_client.get_fee_rate(token_id)  # bps, 동적 조회
expected_profit = size * adjusted_edge
fee_cost = fee_rate / 10000 * min(price, 1 - price) * size
net_profit = expected_profit - fee_cost
```

**필터**: `net_profit < MIN_PROFIT_THRESHOLD ($0.50)` → 실행 스킵

**참고**: Oracle 보고서에 따르면 대부분의 마켓은 수수료 0%. 수수료 0 마켓에서는 이 필터가 `expected_profit > $0.50`만 체크한다.

---

## 9. 통합 계약

> 이 섹션은 2명 이상의 에이전트(또는 모듈)가 공유하는 연결점을 정의한다.
> 모든 개발자는 여기 명시된 이름을 **그대로** 사용해야 한다. 임의 변경 금지.

### 9.1 환경변수 (.env)

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

# === Frequency Governor ===
FREQUENCY_MODE=AUTO                              # TURBO, NORMAL, STEALTH, AUTO

# === Risk ===
RISK_FREE_RATE=0.05                              # 연 5% (유지비용 계산용)
MIN_PROFIT_THRESHOLD=0.50                        # 최소 순이익 USDC

# === 전략 토글 (1=활성, 0=비활성) ===
STRATEGY_AMBIGUITY=1
STRATEGY_ORACLE_FEAR=1
STRATEGY_CONTRARIAN=1
STRATEGY_CORRELATED=1
STRATEGY_LIQUIDITY_VACUUM=1
STRATEGY_COMPLETE_SET=1
```

### 9.2 파일 경로

| 용도 | 경로 | 소유 |
|------|------|------|
| 엔트리포인트 | `src/main.py` | backend |
| 공유 타입 | `src/shared/types.py` | architect (개발자 읽기전용) |
| 설정 | `config.py` | backend |
| DB 파일 | `data/reaper.db` | 런타임 자동 생성 |
| 환경변수 템플릿 | `.env.example` | backend |
| 실행 스크립트 | `start.sh`, `start.bat` | backend |

### 9.3 API 엔드포인트 URL (상수)

```python
# config.py에 정의, 모든 모듈이 참조
CLOB_HOST     = "https://clob.polymarket.com"
GAMMA_HOST    = "https://gamma-api.polymarket.com"
DATA_HOST     = "https://data-api.polymarket.com"
WS_MARKET_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
WS_USER_URL   = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
```

### 9.4 WebSocket 메시지 형식

**Market Channel 구독 요청** (ws_manager.py가 전송):
```json
{
  "auth": {},
  "assets_ids": ["<token_id_1>", "<token_id_2>"],
  "type": "market"
}
```

**User Channel 구독 요청** (ws_manager.py가 전송, L2 인증):
```json
{
  "auth": {
    "apiKey": "<POLY_API_KEY>",
    "secret": "<POLY_API_SECRET>",
    "passphrase": "<POLY_API_PASSPHRASE>"
  },
  "type": "user"
}
```

**수신 이벤트 타입**:
- `last_trade_price`: `{"event_type": "last_trade_price", "asset_id": str, "price": str, "side": str, "size": str, "timestamp": str}`
- `price_change`: `{"event_type": "price_change", "asset_id": str, "market": str, "changes": [...], "timestamp": str, "hash": str}`
- `book`: 오더북 전체 스냅샷 `{"event_type": "book", "market": str, "asset_id": str, "bids": [...], "asks": [...]}`

### 9.5 Signal 흐름 인터페이스

```
[Reactor Alpha]
  Stage 1~3 Strategy.analyze() / on_ws_event()
      → Signal (reactor_source=ALPHA)
      → SignalQueue.put()
              ↓
        MetaBrain.consume()
              ↓
        TradeDecision (golden_cross 플래그)
              ↓
        FrequencyGovernor.get_kelly_multiplier()
              ↓
        RiskSentinel.evaluate()
              ↓
        RiskApproval
              ↓
        Executor.execute()  (Patient)
              ↓
        TradeResult → DB.record_trade()

[Reactor Omega]
  CompleteSet.on_ws_event()
      → Signal (reactor_source=OMEGA)
      → [즉시] RiskSentinel.evaluate()
              ↓
        RiskApproval
              ↓
        Executor.execute()  (Sniper / FOK)
              ↓
        TradeResult → DB.record_trade()
              ↓
        MetaBrain.notify_omega_anomaly()  (Golden Cross 판정용)
        SignalQueue.purge_market()         (AC-40)
```

**데이터 타입 흐름**: `Signal → TradeDecision → RiskApproval → TradeResult`
이 4개 타입은 `src/shared/types.py`에 정의되어 있다.

### 9.6 DB 테이블명

| 테이블 | 용도 | v1.1 변경 |
|--------|------|-----------|
| `signals` | 전략 시그널 기록 | `reactor_source` 컬럼 추가 |
| `trades` | 체결 거래 기록 | `reactor_source`, `golden_cross`, `holding_cost`, `fee_cost` 추가 |
| `portfolio` | 포지션 스냅샷 | 변경 없음 |
| `daily_stats` | 일별 통계 | `alpha_signals`, `omega_signals`, `golden_crosses`, `frequency_mode` 추가 |

### 9.7 모듈 간 의존성

```
config.py ← 모든 모듈

src/shared/types.py ← 모든 모듈

src/api/clob_client.py ← engine.py, executor.py, strategies/*
src/api/gamma_client.py ← market_cache.py
src/api/data_client.py ← market_cache.py, tracker.py, contrarian.py (holders)
src/api/ws_manager.py ← engine.py, liquidity_vacuum.py, complete_set.py

src/data/market_cache.py ← engine.py, strategies/*, meta_brain.py
src/data/db.py ← engine.py, tracker.py, frequency_governor.py

src/strategies/base.py ← strategies/*
src/strategies/* → signal_queue.py (Signal 생산)
src/strategies/complete_set.py → executor.py (Omega 직접 실행)
src/strategies/complete_set.py → meta_brain.py (Omega anomaly 알림)
src/strategies/complete_set.py → signal_queue.py (purge_market)

src/core/signal_queue.py → meta_brain.py (Signal 소비)
src/core/meta_brain.py → risk_sentinel.py (TradeDecision)
src/core/frequency_governor.py ← risk_sentinel.py (Kelly 배수), engine.py (스캔 주기)
src/core/risk_sentinel.py → executor.py (RiskApproval)
src/core/executor.py → clob_client.py (주문 실행)

src/portfolio/tracker.py ← risk_sentinel.py (포지션 조회)
src/portfolio/tracker.py ← engine.py (동기화)
```

### 9.8 Rate Limit 배분

| 대상 | Polymarket 제한 | v1.1 목표 | 배분 |
|------|----------------|-----------|------|
| 공개 API (Gamma/CLOB 공개) | 100 req/분 | 최대 65 req/분 | Stage 1: ~15, Stage 2: ~20, Cache 갱신: ~15, 포지션 동기화: ~5, 예비: ~10 |
| CLOB 주문 | 60 orders/분 | 최대 20 orders/분 | Patient: ~10, Sniper: ~5, 취소: ~5 |
| CLOB 전체 | 3,000 req/10분 | 최대 1,500 req/10분 | 여유 50% 확보 |
| 배치 주문 | 15개/콜 | 미사용 | 단건 위주 (Complete Set 차익 시에만 고려) |
| WebSocket | 토큰 ID 구독 수 무제한 | Stage 3 Hit List 기준 ~50~100 | Hit List 마켓 + Complete Set 감시 대상 |

---

## 10. 설계 결정 근거

### 10.1 왜 듀얼 리액터인가?

Complete Set 차익(밀리초 단위)과 메타 스코어링(분 단위)은 본질적으로 다른 시간 스케일이다. 단일 파이프라인에 넣으면 느린 분석이 빠른 차익 기회를 놓치게 한다. 두 리액터를 분리하여 각자의 속도로 독립 실행하면서, Meta Brain이 교차점(Golden Cross)을 감지하여 시너지를 만든다.

### 10.2 왜 3단계 퍼널인가?

v1.0은 모든 전략이 전체 마켓을 독립 분석하여 중복 API 호출이 많았다. 3단계 퍼널은:
- Stage 1: ~500개 활성 마켓 → ~50개 Target List (90% 필터링, 저비용 분석)
- Stage 2: ~50개 → ~10개 Hit List (정밀 분석, 가격 히스토리 필요)
- Stage 3: ~10개만 WS 구독 (실시간 모니터링, 최소 리소스)

이 구조가 Rate Limit을 효율적으로 사용하고, 분석 정밀도를 높인다.

### 10.3 왜 py-clob-client를 run_in_executor로 래핑하는가?

py-clob-client는 동기 라이브러리(requests 기반)이다. asyncio 이벤트 루프를 블로킹하지 않기 위해 `loop.run_in_executor(None, sync_call)`로 스레드풀에 위임한다. SDK의 서명/인증 로직(HMAC, EIP-712)을 재구현하는 것보다 안전하다.

### 10.4 왜 Gamma/Data API는 aiohttp 직접 사용하는가?

인증이 불필요하거나 단순 GET 요청이다. aiohttp로 직접 호출하면 run_in_executor 오버헤드 없이 네이티브 async 성능을 얻는다.

### 10.5 왜 Risk Sentinel에서 Correlation Guard를 제거했는가?

v1.0의 Layer 6 Correlation Guard는 같은 event_id/tag 마켓의 과잉 노출을 방지했다. v1.1에서는 Correlated Markets 전략(AC-12)이 Stage 2에서 상관 분석을 직접 수행하므로, 시그널 생성 단계에서 이미 상관 마켓을 인식한다. Hit List에 올라간 마켓은 이미 상관 분석을 통과한 것이므로, Risk Sentinel에서 중복 체크할 필요가 없다.

### 10.6 왜 보조지표는 별도 파일이 아닌가?

Market Age, Crowding, Vol-Price Divergence는 독립 시그널을 생산하지 않고, 기존 전략의 confidence를 보강한다. 별도 파일로 분리하면 모듈 간 결합이 복잡해지고, confidence 조정 로직이 산재된다. 해당 Stage의 전략 내부에 포함하여 응집도를 높인다.

### 10.7 왜 Omega는 Signal Queue를 우회하는가?

Complete Set 차익은 밀리초 단위의 시간 민감 기회다. Signal Queue → Meta Brain → Risk Sentinel 파이프라인을 거치면 수백ms~수초의 지연이 발생하여 기회를 놓친다. Omega는 Risk Sentinel만 통과하고 즉시 실행한다. Meta Brain에는 실행 후 알림만 보내어 Golden Cross 판정에 활용한다.

### 10.8 왜 AC-12와 AC-18을 분리하는가? (비판자 CRITICAL-03 반영)

AC-12(Correlated, Stage 2)는 "이 마켓에 가격 합 이상이 있다"는 **분석 결과**를 Hit List에 추가한다. 임계값이 느슨하다(0.02).
AC-18(Complete Set, Omega)는 "지금 당장 차익을 잡아야 한다"는 **실행 트리거**다. 임계값이 엄격하다(0.03).

분리의 이점:
1. Alpha는 더 많은 "의심" 마켓을 Stage 3로 넘겨 WS 모니터링 대상을 확대
2. Omega는 확실한 차익만 즉시 실행하여 슬리피지 위험 최소화
3. 두 시스템이 같은 마켓에 동시 시그널 생성 시 AC-39/40의 중복 방지 규칙이 적용

### 10.9 왜 유지비용을 Kelly Sizer에서 차감하는가? (비판자 CRITICAL-02 반영)

포지션 유지 기간이 길수록 자금이 동결되어 다른 기회를 놓친다. 기회비용을 edge에서 차감하면 Kelly 공식이 자동으로 장기 포지션의 크기를 줄인다. risk_free_rate = 5%는 보수적 추정이며 config에서 관리한다.

### 10.10 왜 테스트넷이 없는가?

Oracle 보고서: "Polymarket은 별도의 공개 테스트넷 환경을 제공하지 않습니다." DRY_RUN=true 기본값이 유일한 안전 테스트 방법이다.

---

## 11. 에러 처리 및 복구

### 11.1 API 에러

| HTTP 코드 | 대응 |
|-----------|------|
| 429 (Rate Limit) | 지수 백오프 (1s → 2s → 4s, 최대 3회) → 실패 시 다음 주기에 재시도 |
| 401/403 (인증) | 로그 WARNING, API 키 재발급 필요 알림 |
| 500+ (서버) | 1회 재시도 후 스킵, 다음 polling 주기에 재시도 |
| 타임아웃 | 10초 timeout, 1회 재시도 |
| 네트워크 에러 | 지수 백오프로 재시도, 5회 실패 시 WARNING 로그 |

### 11.2 WebSocket 복구 (AC-04)

1. 연결 끊김 감지 (30초 무메시지 = heartbeat 타임아웃)
2. 지수 백오프로 재연결 (1s → 2s → 4s → 8s → 최대 30s)
3. 재연결 후 `_subscribed_assets` 리스트로 자동 재구독
4. 단절 구간 보정: 재연결 후 REST API로 최신 가격/오더북 1회 fetch (갭 메우기)
5. 5회 연속 재연결 실패 → REST 폴링 폴백 모드 전환 (WARNING 로그)

### 11.3 Graceful Shutdown (AC-36)

1. SIGINT/SIGTERM 수신 → `running = False` 플래그
2. 신규 시그널 생성 중단
3. 진행 중인 주문 완료 대기 (최대 10초)
4. 미체결 GTC 주문 취소 여부는 사용자 설정에 따라 (기본: 유지)
5. WebSocket 연결 종료
6. DB 커밋 및 종료
7. 구조화된 로그 기록

### 11.4 구조화된 로깅 (AC-37)

- Python `logging` 모듈 사용
- `LOG_LEVEL` 환경변수로 레벨 설정
- 로그 형식: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- 모듈별 로거: `logging.getLogger("reaper.engine")`, `logging.getLogger("reaper.strategy.ambiguity")` 등

### 11.5 전략별 에러 격리

각 전략의 `analyze()` 호출은 try/except로 감싸고, 개별 전략 실패가 전체 시스템을 중단시키지 않는다:
```python
for strategy in stage_strategies:
    try:
        signals = await strategy.analyze(markets)
        for s in signals:
            await signal_queue.put(s)
    except Exception as e:
        logger.error(f"Strategy {strategy.name} failed: {e}")
        # 해당 전략 스킵, 다음 전략 계속 실행
```

---

## 12. 의존성

```
# requirements.txt
py-clob-client>=0.15.0        # Polymarket 공식 Python SDK
aiohttp>=3.9.0                 # 비동기 HTTP/WebSocket
aiosqlite>=0.19.0              # 비동기 SQLite
websockets>=12.0               # WebSocket 클라이언트 (ws_manager)
```

**표준 라이브러리 (별도 설치 불필요)**:
- asyncio, statistics, json, os, time, datetime, dataclasses, enum, logging, signal, hashlib, hmac, base64, math, uuid, collections

---

## 13. 보안 고려사항

- 개인키(`POLY_PRIVATE_KEY`)는 .env에만 저장, 코드/로그에 절대 노출 금지
- .env는 .gitignore에 반드시 포함
- API 시크릿은 메모리에서 Config 인스턴스로만 접근
- DB 파일은 로컬 전용, 네트워크 공유 금지
- L2 서명은 30초 만료 (타임스탬프 동기화 필요)
- DRY_RUN=true 기본값으로 실수 방지
- 로깅 시 시크릿 마스킹 (API 키, 개인키 등은 앞 6자만 표시)

---

## AC 매핑 체크리스트

| AC | 설계 반영 위치 | 상태 |
|----|---------------|------|
| AC-01 | engine.py asyncio.gather 구조 | O |
| AC-02 | clob_client.py run_in_executor | O |
| AC-03 | gamma_client.py, data_client.py aiohttp | O |
| AC-04 | ws_manager.py 자동 재연결 + 재구독 | O |
| AC-05 | config.py 환경변수 관리, DRY_RUN=true | O |
| AC-06 | db.py aiosqlite, 4 테이블 | O |
| AC-07 | ambiguity.py TF-IDF + resolution source 미명시 | O |
| AC-08 | oracle_fear.py 분쟁 키워드 + YES 할인 | O |
| AC-09 | engine.py _run_stage1 Market Age +0.15 | O |
| AC-10 | engine.py Target List 캐시 저장 | O |
| AC-11 | contrarian.py Z-score + 주말 드리프트 | O |
| AC-12 | correlated.py 분석 전용 (임계값 0.02, implied conditional 정의) | O |
| AC-13 | contrarian.py Position Crowding (graceful degradation) | O |
| AC-14 | engine.py Hit List = Stage 2 결과 | O |
| AC-15 | liquidity_vacuum.py WS 오더북 모니터링 | O |
| AC-16 | liquidity_vacuum.py Vol-Price Divergence (수치 기준 명시) | O |
| AC-17 | engine.py Stage 3 → Patient Executor (GTC/postOnly) | O |
| AC-18 | complete_set.py WS 실시간 가격 합 (임계값 0.03) | O |
| AC-19 | complete_set.py → Sniper Executor (FOK) | O |
| AC-20 | meta_brain.py Signal 버퍼 (600초 윈도우) | O |
| AC-21 | meta_brain.py Golden Cross (Kelly 1.5x) | O |
| AC-22 | meta_brain.py 전략별 가중치 → 가중 평균 | O |
| AC-23 | risk_sentinel.py Layer 1 Kelly 0.4 × Governor 배수 | O |
| AC-24 | risk_sentinel.py Layer 2 Single Market 15% | O |
| AC-25 | risk_sentinel.py Layer 3 Total Exposure 60% | O |
| AC-26 | risk_sentinel.py Layer 4 Circuit Breaker 8% | O |
| AC-27 | risk_sentinel.py Layer 5 DD Throttle (곱셈 중첩 명시) | O |
| AC-28 | frequency_governor.py 4모드 파라미터 테이블 | O |
| AC-29 | frequency_governor.py AUTO 모드 DD 전환 | O |
| AC-30 | frequency_governor.py SIGHUP / DB 플래그 | O |
| AC-31 | executor.py Sniper (FOK, slippage) | O |
| AC-32 | executor.py Patient (GTC + postOnly) | O |
| AC-33 | executor.py DRY_RUN 가상 체결 | O |
| AC-34 | tracker.py Data API 동기화 + DRY_RUN | O |
| AC-35 | db.py daily_stats 자동 집계 | O |
| AC-36 | engine.py Graceful shutdown (SIGINT/SIGTERM) | O |
| AC-37 | 구조화된 로깅 (logging 모듈, LOG_LEVEL) | O |
| AC-38 | .env.example + start.sh/start.bat | O |
| AC-39 | engine.py 중복 주문 방지 | O |
| AC-40 | engine.py/complete_set.py Omega 우선 + α 큐 소거 | O |
| AC-41 | risk_sentinel.py Layer 1 유지비용 차감 | O |
| AC-42 | risk_sentinel.py Layer 1 실행 비용 필터 | O |

**비판자 보고서 반영 체크리스트**:

| 결함 | 반영 위치 | 상태 |
|------|-----------|------|
| CRITICAL-01: 주말 드리프트 | contrarian.py 로직 (5.4절) | O |
| CRITICAL-02: 유지비용 | risk_sentinel.py Layer 1 + HoldingCost 타입 (8.3절) | O |
| CRITICAL-03: AC-12/18 역할 경계 | correlated.py vs complete_set.py 분리 + 임계값 차별화 (5.5/5.7절) | O |
| CRITICAL-04: 중복 주문 방지 | engine.py AC-39/40 (8.1/8.2절) | O |
| MINOR-01: 모호성 키워드 사전 | Config.AMBIGUITY_KEYWORDS 리스트 | O |
| MINOR-02: 분쟁 키워드 | Config.ORACLE_FEAR_KEYWORDS + 텍스트 매칭 명시 | O |
| MINOR-03: /holders API | graceful degradation 명시 (5.4절) | O |
| MINOR-04: Vol-Price 수치 기준 | VOL_PRICE_* config 파라미터 (5.6절) | O |
| MINOR-05: 전략 가중치 | Config.WEIGHT_* + 런타임 변경 가능 | O |
| MINOR-06: DD 임계값 불일치 | 독립 작동 + 곱셈 중첩 의도 명시 (7.2절) | O |
| MINOR-07: Governor 배수 미정의 | 모드별 파라미터 테이블 (7.1절) | O |
| MINOR-08: 실행 비용 필터 | AC-42 + MIN_PROFIT_THRESHOLD (8.4절) | O |
| MINOR-09: WS 재연결 상태 복구 | 자동 재구독 + REST 갭 메우기 (11.2절) | O |
| MINOR-10: 소스 부재 분석 | ambiguity.py resolution_source 체크 (5.1절) | O |

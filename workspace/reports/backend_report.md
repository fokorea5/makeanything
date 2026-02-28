# Backend Report — Polymarket 자동매매 트레이딩 봇

**작성일**: 2026-02-17
**에이전트**: developer-backend

---

## AC별 완료 여부

| AC | 내용 | 상태 | 비고 |
|----|------|------|------|
| AC-1 | Polymarket API 클라이언트 — CLOB/Gamma/Data 3레이어 연동, L2 인증, 마켓 조회/오더북/주문/포지션 API 래핑 | 완료 | `src/api/polymarket_client.py`, `gamma_client.py`, `data_client.py` |
| AC-2 | 전략1 해결 기준 아비트라지 — 모호 키워드 스코어링, 명확 소스 유무 판단, NO 포지션 시그널 | 완료 | `src/strategies/resolution_arb.py` |
| AC-3 | 전략2 오라클 공포 프리미엄 — 분쟁/논란 이력 감지, 5-10¢ 할인 탐지, 매수 시그널 | 완료 | `src/strategies/oracle_fear.py` |
| AC-4 | 전략3 군중 반대 지표 — Z-score >2 감지, 주말 드리프트/결제일 과열 패턴, 반대 포지션 시그널 | 완료 | `src/strategies/contrarian.py` |
| AC-5 | 전략4 연관 시장 비효율 — 태그/이벤트 기반 군집화, implied conditional >1.5 감지, 시그널 | 완료 | `src/strategies/correlated.py` |
| AC-6 | 전략5 유동성 진공 사냥 — spread >0.05 + depth_ratio >2 감지, 리밋 오더 시그널 | 완료 | `src/strategies/liquidity_vacuum.py` |
| AC-7 | 전략6 메타봇 — 복합 스코어 계산, 2개↑ 중첩 보너스, 최종 거래 결정 | 완료 | `src/strategies/meta_bot.py` |
| AC-8 | 드라이런 모드 — 실거래 없이 시뮬레이션, 가상 P&L 추적, 시그널 로그 기록 | 완료 | `src/engine/order_executor.py`, `src/db/database.py` |
| AC-9 | 리스크 관리 — 최대 포지션 크기, 포트폴리오 노출 한도, 단일 시장 집중도 제한 | 완료 | `src/engine/risk_manager.py` |
| AC-10 | 자동 거래 엔진 — 전략 스케줄링, 연속 실행, 시그널→주문 자동화, 거래 로그 | 완료 | `src/engine/trading_engine.py` |
| AC-11 | 실행 환경 — start.sh/start.bat, .env.example, requirements.txt, 원스텝 실행 | 완료 | 프로젝트 루트 |

**전체 AC: 11/11 완료**

---

## 구현된 파일 목록

### 1단계: 기반 인프라
- `src/__init__.py` — 빈 파일 (기존)
- `src/config.py` — Config dataclass, from_env(), validate_for_live_trading()
- `src/api/__init__.py` — API 패키지
- `src/api/rate_limiter.py` — 슬라이딩 윈도우 Rate Limiter (80 req/분)
- `src/api/polymarket_client.py` — CLOB SDK 래핑 (L0/L2, get_order_book, get_midpoint, place_limit_order 등)
- `src/api/gamma_client.py` — Gamma API (get_markets, get_events, get_tags 등)
- `src/api/data_client.py` — Data API (get_positions, get_portfolio_value 등)
- `src/db/__init__.py` — DB 패키지
- `src/db/schema.sql` — DDL (trade_logs, signal_logs, virtual_positions, daily_pnl)
- `src/db/database.py` — SQLite Database 클래스

### 2단계: 전략 모듈
- `src/strategies/__init__.py` — 전략 패키지
- `src/strategies/base.py` — BaseStrategy ABC (safe_analyze 포함)
- `src/strategies/resolution_arb.py` — 전략1: 모호성 스코어 → NO 매수
- `src/strategies/oracle_fear.py` — 전략2: 오라클 공포 → YES 매수
- `src/strategies/contrarian.py` — 전략3: Z-score 이상치 → 반대 포지션
- `src/strategies/correlated.py` — 전략4: 이벤트/태그 그룹 → 가격 불일치 감지
- `src/strategies/liquidity_vacuum.py` — 전략5: 오더북 비대칭 → 리밋 오더
- `src/strategies/meta_bot.py` — 전략6: 복합 스코어 + 중첩 보너스 → TradeDecision

### 3단계: 엔진
- `src/engine/__init__.py` — 엔진 패키지
- `src/engine/risk_manager.py` — RiskManager (5단계 검사)
- `src/engine/order_executor.py` — OrderExecutor (드라이런/실거래 분기)
- `src/engine/trading_engine.py` — TradingEngine + Scheduler (메인 루프)

### 4단계: 엔트리포인트 + 실행 환경
- `src/main.py` — CLI 파싱 (--live, --cycle-interval, --log-level, --db-path)
- `requirements.txt` — py-clob-client>=0.5.0, requests>=2.28.0, python-dotenv>=1.0.0
- `.env.example` — 환경 변수 템플릿
- `start.sh` — Linux/macOS 실행 스크립트 (실행 권한 부여됨)
- `start.bat` — Windows 실행 스크립트

---

## 실행 테스트 결과

### python -m src.main --help
```
usage: polymarket-bot [-h] [--live] [--cycle-interval SECONDS]
                      [--log-level LEVEL] [--db-path PATH] [--version]
...
```
→ 정상 동작 확인

### import 검증
모든 파일 import 오류 없음:
- src.config, src.api.*, src.db.database, src.strategies.*, src.engine.* 전부 성공

### 전략 기능 테스트
- 전략1 (resolution_arb): 모호한 시장 1개 → 시그널 1개 생성 (ambiguity_score=0.92)
- 전략2 (oracle_fear): 분쟁 키워드 + Politics 카테고리 → 시그널 1개
- 전략3 (contrarian): Z-score 이상치 시뮬레이션 → 시그널 1개
- 전략4 (correlated): 이벤트 그룹 YES 합=1.35 → NO 매수 시그널 1개
- 전략5 (liquidity_vacuum): spread=0.20, depth_ratio=10 → 리밋 오더 시그널 1개
- MetaBot: 5개 전략 시그널 → 2개 거래 결정

### DB + 드라이런 테스트
- RiskManager: 크기=35.00 USD 승인 (composite_score 0.7 기준)
- OrderExecutor 드라이런: DRY-XXXXXXXX order_id 생성
- 가상 포지션 DB 저장 확인

---

## 통합 계약 준수 확인 (DESIGN.md 섹션 11)

| 항목 | 계약 값 | 실제 구현 | 일치 |
|------|---------|-----------|------|
| POLY_PRIVATE_KEY | 환경 변수명 | src/config.py | ✓ |
| CLOB_HOST | https://clob.polymarket.com | shared/types.py 상수 사용 | ✓ |
| GAMMA_BASE_URL | https://gamma-api.polymarket.com | shared/types.py 상수 사용 | ✓ |
| DATA_BASE_URL | https://data-api.polymarket.com | shared/types.py 상수 사용 | ✓ |
| CHAIN_ID | 137 | shared/types.py 상수 사용 | ✓ |
| DB_PATH | data/polymarket_bot.db | config.db_path 기본값 | ✓ |
| DRY_RUN 기본값 | true | Config.dry_run=True | ✓ |
| import 규칙 | from src.shared.types import ... | 전 파일 준수 | ✓ |
| CLI --live | 실거래 플래그 | src/main.py | ✓ |

---

## 주요 설계 결정

1. **py-clob-client 없을 때 fallback**: ImportError를 포착하여 REST fallback 모드로 동작. 설치 없이도 임포트 성공.
2. **BaseStrategy.safe_analyze()**: 전략 예외가 엔진 전체를 중단시키지 않도록 개별 에러 포착.
3. **EnrichedMarket 구조**: order_book, price_history를 선택적 필드로 설계. 필요한 전략만 해당 데이터 사용.
4. **API 요청 절약**: 오더북은 상위 20개, 가격 히스토리는 상위 10개만 조회 (사이클당 약 27 requests).
5. **@risk/@confidence 태그**: 금융거래 관련 코드와 미검증 로직에 태그 부착.

---

## 알려진 제약 사항

- py-clob-client API 응답 형식은 버전별로 다를 수 있음 (`# @confidence: low` 태그 부착됨)
- 전략3 (contrarian)의 패턴 감지는 price_history가 최소 3개 포인트 이상 필요
- Data API 실제 스키마는 실거래 환경에서 검증 필요 (`# @confidence: low`)
- 실거래는 POLY_PRIVATE_KEY 등 L2 자격증명 필수 + USDC.e 지갑 사전 승인 필요

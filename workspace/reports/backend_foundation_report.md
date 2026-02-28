# Backend Foundation Report -- Polymarket Reaper Bot v1.1

**작성일**: 2026-02-17
**작성자**: Backend Agent
**범위**: Foundation Layer (config, API clients, data layer, portfolio tracker, support files)

---

## 1. 구현된 파일 목록 (16개)

| # | 파일 | 줄 수 | 역할 |
|---|------|-------|------|
| 1 | `config.py` | ~260 | 통합 설정 관리, .env 직접 파싱, 모든 파라미터 기본값 |
| 2 | `src/__init__.py` | 0 | 패키지 마커 |
| 3 | `src/api/__init__.py` | 0 | 패키지 마커 |
| 4 | `src/api/clob_client.py` | ~310 | CLOB API async 래퍼, run_in_executor, Rate Limit, 429 백오프 |
| 5 | `src/api/gamma_client.py` | ~220 | Gamma API aiohttp 직접 호출, GammaMarket 변환 |
| 6 | `src/api/data_client.py` | ~200 | Data API aiohttp 직접 호출, /holders 404 graceful degradation |
| 7 | `src/api/ws_manager.py` | ~280 | Market + User WS 채널, 자동 재연결, 재구독, 5회 실패 콜백 |
| 8 | `src/data/__init__.py` | 0 | 패키지 마커 |
| 9 | `src/data/market_cache.py` | ~300 | 5분 TTL 인메모리 캐시, event_id 그룹핑, WS 실시간 업데이트 |
| 10 | `src/data/db.py` | ~320 | aiosqlite, 4개 테이블 DDL, CRUD, 일별 통계 upsert |
| 11 | `src/portfolio/__init__.py` | 0 | 패키지 마커 |
| 12 | `src/portfolio/tracker.py` | ~230 | Data API 동기화, DRY_RUN 가상 포지션, DD 계산 |
| 13 | `.env.example` | 24 | 환경변수 템플릿 (DESIGN.md 9.1 그대로) |
| 14 | `requirements.txt` | 4 | Python 의존성 (DESIGN.md 12절) |
| 15 | `start.sh` | 35 | Linux/Mac 실행 스크립트, Python 3.9+ 체크 |
| 16 | `start.bat` | 35 | Windows 실행 스크립트, Python 3.9+ 체크 |

---

## 2. AC 매핑

| AC | 구현 파일 | 구현 내용 |
|----|-----------|-----------|
| AC-02 | `src/api/clob_client.py` | py-clob-client를 `run_in_executor`로 async 래핑 |
| AC-03 | `src/api/gamma_client.py`, `src/api/data_client.py` | aiohttp 네이티브 async 호출 |
| AC-04 | `src/api/ws_manager.py` | 자동 재연결(지수 백오프 1s~30s), 재구독, 5회 실패 콜백 |
| AC-05 | `config.py` | .env 직접 파싱(dotenv 미사용), DRY_RUN=true 기본값, 모든 설정 파라미터 |
| AC-06 | `src/data/db.py` | aiosqlite, signals/trades/portfolio/daily_stats 4개 테이블 |
| AC-13 (일부) | `src/api/data_client.py` | `get_holders()` 404 시 None 반환 (graceful degradation) |
| AC-30 (일부) | `src/data/db.py` | `get_frequency_mode()`, `set_frequency_mode()` DB 플래그 |
| AC-33 (일부) | `src/portfolio/tracker.py` | `record_virtual_trade()` DRY_RUN 가상 체결 기록 |
| AC-34 | `src/portfolio/tracker.py` | Data API 포지션 동기화 + DRY_RUN 가상 포지션 관리 |
| AC-35 (일부) | `src/data/db.py` | `update_daily_stats()` upsert, `get_daily_stats()` 조회 |
| AC-37 (일부) | `config.py` | logging.basicConfig 설정, LOG_LEVEL 환경변수, 포맷 지정 |
| AC-38 | `.env.example`, `start.sh`, `start.bat` | 환경변수 템플릿 + 실행 스크립트 |
| AC-39 (일부) | `src/portfolio/tracker.py` | `has_open_orders()`, 주문 추적 인터페이스 |
| AC-41 (파라미터) | `config.py` | RISK_FREE_RATE = 0.05 |
| AC-42 (파라미터) | `config.py` | MIN_PROFIT_THRESHOLD = 0.50 |

---

## 3. 통합 계약 준수 사항

- **API URL**: DESIGN.md 9.3절의 5개 URL 상수 `config.py`에 정확히 반영
- **환경변수명**: DESIGN.md 9.1절의 모든 변수명 그대로 사용
- **DB 테이블**: DESIGN.md 4절의 SQL DDL 그대로 복사 (signals, trades, portfolio, daily_stats)
- **WS 메시지 형식**: DESIGN.md 9.4절의 구독 JSON 형식 그대로 구현
- **타입 사용**: `src/shared/types.py`의 모든 관련 타입 import하여 사용 (수정하지 않음)
- **로거 네이밍**: `logging.getLogger("reaper.모듈명")` 패턴 일관 적용

---

## 4. 주의사항 / 제한사항

### 4.1 py-clob-client 호환성
- `@confidence: low` 표시됨. py-clob-client의 API 표면(메서드명, 파라미터)은 버전에 따라 달라질 수 있음.
- `ClobClient`를 import할 수 없는 환경에서는 stub 모드로 동작 (모든 메서드가 빈 값 반환).
- `get_fee_rate` 메서드는 SDK 버전에 따라 존재하지 않을 수 있어 `getattr` 방어 코드 적용.

### 4.2 Rate Limit
- Semaphore + sliding window 이중 제어 구현.
- 공개 API: 65 req/분 목표 (제한 100 중).
- 주문 API: 20 orders/분 목표 (제한 60 중).
- 429 응답 시 지수 백오프 1s -> 2s -> 4s (최대 3회).

### 4.3 WebSocket
- `websockets` 라이브러리 사용. 메이저 버전 변경 시 API 차이 가능.
- Heartbeat timeout 30초. 무메시지 시 재연결 트리거.
- 5회 연속 재연결 실패 시 `on_ws_failure` 콜백 호출 (engine에서 REST 폴백 구현 필요).

### 4.4 MarketDataCache
- Gamma API에서 token_id를 직접 제공하지 않음. CLOB API 또는 엔진 레벨에서 token_id를 채워야 함.
- `event_id`는 별도 `enrich_with_events()` 호출로 채워짐.

### 4.5 DB
- WAL 모드 활성화로 읽기 성능 향상.
- daily_stats의 UPSERT (`ON CONFLICT(date) DO UPDATE`) 사용.

### 4.6 PortfolioTracker
- DRY_RUN 시 기본 가상 bankroll = 1000 USDC (실 환경에서는 Data API에서 동기화).
- 일일 P&L은 UTC 00:00 기준 자동 리셋.

### 4.7 보안
- `@risk: auth` 주석: ClobClient 초기화, post_order, WS User 구독 부분.
- API 키/개인키는 로그에 앞 6자만 표시 (`_mask_secret` 함수).
- `.env.example`에 실제 값 미포함.

---

## 5. 다음 단계 의존성

Foundation Layer가 완성되었으므로 다음 모듈이 이 위에 구현 가능:
- `src/core/engine.py` -- API 클라이언트 초기화 및 오케스트레이션
- `src/core/signal_queue.py` -- asyncio.PriorityQueue + purge_market
- `src/strategies/base.py` -- BaseStrategy + 전략 구현
- `src/core/frequency_governor.py` -- Config 참조, DB 플래그 연동
- `src/core/risk_sentinel.py` -- PortfolioTracker, Config 참조
- `src/core/executor.py` -- AsyncClobClient.post_order 호출

# Architect Report — Polymarket Reaper Bot v1.0

**작성일**: 2026-02-17
**에이전트**: Architect (설계자)
**상태**: 완료 (v2 — Signal Marketplace 아키텍처 전면 재설계)

---

## 산출물

| 파일 | 경로 | 설명 |
|------|------|------|
| DESIGN.md | `workspace/projects/polymarket-reaper/DESIGN.md` | 전체 아키텍처 설계 문서 (10개 섹션) |
| types.py | `workspace/projects/polymarket-reaper/src/shared/types.py` | 공유 타입 정의 (Enum 7개, dataclass 20개) |
| \_\_init\_\_.py | `workspace/projects/polymarket-reaper/src/shared/__init__.py` | 패키지 init |

---

## DESIGN.md 요약

### 포함 항목
1. **아키텍처 개요**: Signal Marketplace 아키텍처 ASCII 다이어그램
2. **디렉토리 구조**: 전체 파일 트리 (40+ 파일)
3. **모듈 역할 상세**: 15개 모듈 각각의 역할, 주요 메서드, 동작 원리
4. **Signal Flow 다이어그램**: Strategy -> Signal Queue -> Meta Brain -> Risk Sentinel -> Executor
5. **DB 스키마**: signals, trades, portfolio, daily_stats (4개 테이블, 인덱스 포함)
6. **통합 계약**: 환경변수, 파일 경로, API URL, WebSocket 메시지 형식, 모듈 간 의존성, Rate Limit 배분
7. **전략별 입출력 명세**: 10개 전략 각각의 입력 데이터, 로직 요약, 출력 Signal 형식
8. **Risk Sentinel 6층 구조 상세**: 각 층의 로직, 임계값, 수식
9. **설계 결정 근거**: 7개 주요 결정의 이유
10. **에러 처리 및 복구**: API 에러, WebSocket 복구, Graceful Shutdown

### Oracle Report 반영 사항
- Rate Limit: 100 req/분 (공개), 60 orders/분 (주문) -> 전략별 polling 주기 배분 (합계 ~40 req/분)
- WebSocket URL: `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- postOnly + FOK/FAK 동시 설정 불가 -> Dual Executor 완전 분리
- 수수료 0% 마켓 -> Maker Rebate 전략에서 fee_rate_bps > 0 마켓만 대상
- L2 서명 30초 만료 -> py-clob-client SDK가 서명 관리, 타임스탬프 동기화 필요
- 테스트넷 없음 -> DRY_RUN=true 기본값이 유일한 안전장치
- 배치 주문 최대 15개/콜 -> 현재 단건 위주 설계, 향후 확장 가능
- WebSocket 구독 해제 미지원 -> 재연결 시 새 연결 생성
- py-clob-client 동기 라이브러리 -> run_in_executor로 async 래핑

---

## types.py 요약

### Enum (7개)
- `StrategyType`: 10개 전략 식별자 (str Enum, DB 저장 시 .value 사용)
- `SignalUrgency`: CRITICAL/HIGH/MEDIUM/LOW (IntEnum, PriorityQueue 우선순위)
- `ExecutorMode`: SNIPER/PATIENT (str Enum)
- `OrderSide`: BUY/SELL (str Enum)
- `OrderType`: GTC/GTD/FOK/FAK/postOnly (str Enum)
- `TradeStatus`: FILLED/PARTIAL/REJECTED/DRY_RUN (str Enum)
- `RiskRejectReason`: 6개 거부 사유 (str Enum)

### Core Flow Dataclass (5개)
- `Signal`: 전략 시그널 (dataclass(order=True), sort_key=(urgency, timestamp)로 PriorityQueue 정렬)
- `TradeDecision`: Meta Brain 거래 결정 (수렴 결과, contributing_signals 포함)
- `RiskApproval`: Risk Sentinel 승인/거부 (6개 layer_results 포함)
- `RiskCheck`: 리스크 상태 스냅샷 (bankroll, exposure, drawdown 등)
- `TradeResult`: Executor 거래 결과 (체결/가상 결과)

### Market Data Dataclass (10개)
- `PricePoint`, `OrderBookLevel`, `OrderBookSnapshot` (property: best_bid, best_ask, spread, mid)
- `TokenInfo`, `TagInfo`, `MarketData` (property: yes_token_id, no_token_id)
- `GammaMarket`, `GammaEvent`, `GammaTag`
- `PositionData`

### Portfolio/Stats Dataclass (2개)
- `Position`, `DailyStats`

### WebSocket Event Dataclass (3개)
- `WSTradeEvent`, `WSPriceChangeEvent`, `WSBookEvent`

---

## 설계 핵심 결정

1. **asyncio 이벤트 기반**: .plan.md에 asyncio가 명시되어 있고, WebSocket 실시간 + REST 폴링 하이브리드에 필수
2. **py-clob-client run_in_executor 래핑**: SDK 서명/인증 로직 재사용, asyncio 블로킹 방지
3. **Gamma/Data API는 aiohttp 직접**: 인증 불필요, 네이티브 async 성능
4. **Meta Brain은 core에 배치**: 시그널 소비자이므로 strategies/ 밖, signal_queue-executor 파이프라인 사이
5. **Signal.sort_key 패턴**: dataclass(order=True) + tuple(urgency, timestamp)로 PriorityQueue 호환
6. **Dual Executor 분리**: postOnly + FOK 동시 불가 제약 준수
7. **DRY_RUN=true 기본값**: 테스트넷 없으므로 기본 안전장치

---

## v1 대비 v2 변경 사항

| 항목 | v1 (이전) | v2 (현재) |
|------|-----------|-----------|
| 전략 수 | 6개 | 10개 (파생 4개 추가) |
| 아키텍처 | 동기 단일 루프 | asyncio 이벤트 기반 Signal Marketplace |
| WebSocket | 미사용 | 실시간 market 채널 (Liquidity Vacuum, Whale Shadow) |
| Executor | 단일 | Dual (Sniper + Patient) |
| Meta Brain | 가중 평균만 | 수렴 탐지 + 중첩 보너스 + urgency 라우팅 |
| Risk | 5단계 검사 | 6층 방어 (Correlation Guard 추가) |
| 타입 | 14개 dataclass | 20개 dataclass + 7개 Enum |
| Signal Queue | 없음 | asyncio.PriorityQueue (urgency 기반) |

---

## 예외/이슈 사항

없음. .plan.md와 oracle_report.md 간 불일치 없었음.

---

**보고서 작성 완료**: 2026-02-17
**작성자**: Architect Agent
**상태**: 작업 완료

# Architect Agent Report

**작성일**: 2026-02-17
**에이전트**: Architect (설계자)
**프로젝트**: Polymarket 자동매매 트레이딩 봇

---

## 작업 요약

### 산출물

| 파일 | 상태 | 설명 |
|------|------|------|
| `projects/polymarket-bot/DESIGN.md` | 작성 완료 | 전체 설계 문서 (14개 섹션) |
| `projects/polymarket-bot/src/shared/types.py` | 작성 완료 | 공유 타입 정의 (Enum 5개, dataclass 14개, 상수 8개) |
| `projects/polymarket-bot/src/shared/__init__.py` | 작성 완료 | 패키지 init |
| `projects/polymarket-bot/src/__init__.py` | 작성 완료 | 패키지 init |

### DESIGN.md 포함 내용

1. **시스템 구조 개요**: ASCII 아키텍처 다이어그램, 모듈별 역할 설명
2. **디렉토리 구조**: 전체 파일 트리 + 각 파일의 역할
3. **Polymarket API 사용 계획**: CLOB/Gamma/Data 3레이어별 엔드포인트 매핑, API 클라이언트 3개 클래스 설계, RateLimiter 설계
4. **전략 설계 (6개)**: 각 전략의 입력 데이터, 로직 (수식/조건 포함), 출력 시그널, 설정 파라미터 전부 명시
5. **메타봇 복합 스코어 계산**: 가중 평균 + 중첩 보너스 공식, 시나리오별 예시 테이블
6. **드라이런 모드 설계**: 실거래/드라이런 동작 차이표, OrderExecutor 분기 로직, 가상 P&L 추적
7. **리스크 관리 파라미터**: 6개 파라미터, RiskManager.check() 5단계 검사 로직
8. **트레이딩 엔진 설계**: 메인 루프 흐름, Polling 주기 분배, Scheduler 클래스
9. **DB 스키마**: 4개 테이블 (trade_logs, signal_logs, virtual_positions, daily_pnl), 인덱스
10. **설정 시스템**: .env 환경 변수, Config/RiskConfig/MetaBotConfig dataclass
11. **통합 계약**: 환경 변수명, 파일 경로, API URL 상수, 공유 타입 목록, import 규칙, CLI 인터페이스
12. **결정 이유 요약**: 10개 기술 선택에 대한 근거 테이블
13. **제약 사항**: API/전략/운영 3영역 제약 (oracle_report.md 반영)
14. **의존성**: requirements.txt 내용 (3개 패키지)

### oracle_report.md 반영 사항

- **테스트넷 없음** → 드라이런 모드를 기본값(True)으로 설계
- **Rate Limit 100 req/분** → RateLimiter 80 req/분 (20% 마진), 전략별 polling 간격 차등 배분
- **L2 서명 30초 만료** → py-clob-client SDK가 자동 관리, 직접 HMAC 구현 불필요
- **배치 주문 최대 15개/콜** → 현재 설계에서 대량 일괄 주문 상황 없음
- **분쟁 이력 API 없음** → 오라클 공포 전략은 키워드/카테고리 기반 휴리스틱으로 대체
- **고래 추적 불가** → 군중 반대 전략은 Z-score 가격 이상치 감지로 대체
- **WebSocket 미사용** → REST polling 방식 채택 (SDK와 일관성, 구현 단순성)
- **EOA 지갑 사전 approve 필요** → 제약 사항에 명시

### 설계 핵심 결정

1. **동기(sync) Python**: py-clob-client가 동기 SDK이므로 aiohttp 비동기 도입은 불필요한 복잡성. 30초 사이클이면 동기 방식으로 충분.
2. **단일 프로세스**: 6개 전략이 순차 실행되고, Rate limit도 단일 리미터로 관리. 멀티프로세스/멀티스레드 불필요.
3. **SQLite**: 로컬 단일 봇이므로 외부 DB 불필요. 표준 라이브러리만으로 거래 로그 + 시그널 로그 + 가상 포지션 관리.
4. **드라이런 기본값 True**: 사용자 안전을 위해 명시적 `--live` 플래그 없이는 실거래 불가.
5. **전략 가중치 차등**: 객관적 비효율(연관 시장 1.2)은 높이고, 단기적 기회(유동성 진공 0.6)는 낮춤. 반대매매(군중 반대 0.8)는 위험도 반영.
6. **외부 의존성 최소화**: py-clob-client, requests, python-dotenv 3개만 사용. numpy 등 대형 라이브러리 배제. statistics 표준 라이브러리로 Z-score 계산.

### 공유 타입 (types.py) 요약

| 카테고리 | 타입 | 설명 |
|----------|------|------|
| Enum | Direction, TokenSide, OrderType, OrderStatus, PositionStatus | 문자열 Enum 5개 |
| 가격/오더북 | PricePoint, OrderBookEntry, OrderBook | 시세 데이터 3개 |
| 시장 | MarketToken, GammaMarket, EnrichedMarket | 시장 메타데이터 3개 |
| 시그널 | Signal | 전략 출력 1개 |
| 거래 | TradeDecision, OrderResult | 메타봇/실행 결과 2개 |
| 포지션 | Position | 보유 포지션 1개 |
| 리스크 | RiskCheckResult | 리스크 검사 결과 1개 |
| 설정 | RiskConfig, MetaBotConfig, StrategyConfig | 설정 타입 3개 |
| 상수 | STRATEGY_DEFAULT_PARAMS, STRATEGY_DEFAULT_INTERVALS, API URL | 전략 파라미터 + URL 상수 |

---

## 예외/이슈 사항

없음. .plan.md와 oracle_report.md 간 불일치 없었음.

---

**보고서 작성 완료**: 2026-02-17
**작성자**: Architect Agent
**상태**: 작업 완료

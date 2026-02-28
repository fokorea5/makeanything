# Architect Report — Polymarket Reaper Bot v1.1

**작성일**: 2026-02-17
**에이전트**: Architect (설계자)
**상태**: 완료 (v1.1 — 듀얼 리액터 3단계 퍼널 전면 재설계)

---

## 산출물

| 파일 | 경로 | 설명 |
|------|------|------|
| DESIGN.md | `workspace/projects/polymarket-reaper/DESIGN.md` | v1.1 전체 아키텍처 설계 문서 (13개 섹션 + AC 매핑 체크리스트) |
| types.py | `workspace/projects/polymarket-reaper/src/shared/types.py` | v1.1 공유 타입 정의 (Enum 9개, dataclass 22개) |

---

## v1.0 → v1.1 핵심 변경

| 항목 | v1.0 | v1.1 |
|------|------|------|
| 아키텍처 | 10전략 독립 병렬 → Signal Queue | 듀얼 리액터 3단계 퍼널 |
| 전략 수 | 10개 전략 | 6코어 + 3보조 |
| 리액터 | 단일 파이프라인 | Alpha (Slow Brain) + Omega (Fast Brain) |
| Meta Brain | 수렴 탐지 전용 | Golden Cross (Alpha+Omega 교차, Kelly 1.5x) |
| Risk Sentinel | 6층 (Correlation Guard 포함) | 5층 (Correlation Guard를 Correlated 전략으로 흡수) |
| Frequency Governor | 없음 | 4모드 (TURBO/NORMAL/STEALTH/AUTO) |
| 유지비용 | 미반영 | Kelly Sizer에서 기회비용 차감 (AC-41) |
| 중복 방지 | 없음 | 마켓별 주문 상태 추적 + Omega 우선 (AC-39/40) |
| 실행 비용 필터 | 없음 | 기대이익 > 수수료 + $0.50 (AC-42) |
| 타입 | 7 Enum + 20 dataclass | 9 Enum + 22 dataclass |

---

## DESIGN.md 섹션 구성

| # | 섹션 | 내용 |
|---|------|------|
| 1 | 아키텍처 개요 | 듀얼 리액터 ASCII 다이어그램, v1.0→v1.1 변경 요약 |
| 2 | 디렉토리 구조 | 전체 파일 트리 (v1.0 제거/신규 파일 명시) |
| 3 | 모듈 역할 상세 | 15개 모듈: config, api/4, core/6, strategies/base, data/2, portfolio/1 |
| 4 | DB 스키마 | signals, trades, portfolio, daily_stats (v1.1 신규 컬럼 포함) |
| 5 | 전략별 입출력 명세 | 6코어 + 3보조: 입력, 로직, 출력 Signal, expires_at, urgency |
| 6 | Risk Sentinel 5층 | Kelly→Single→Total→Circuit→DD Throttle (요약 테이블) |
| 7 | Frequency Governor | 모드별 파라미터 테이블, AUTO DD 전환, DD 곱셈 중첩 |
| 8 | 중복 방지/유지비용/실행비용 | AC-39~42 상세 |
| 9 | 통합 계약 | 환경변수, 파일 경로, WS, Signal 흐름, DB, 모듈 의존성, Rate Limit |
| 10 | 설계 결정 근거 | 10개 핵심 결정의 이유 |
| 11 | 에러 처리 및 복구 | API, WS 복구, Graceful Shutdown, 로깅, 전략 격리 |
| 12 | 의존성 | requirements.txt 4개 패키지 |
| 13 | 보안 고려사항 | 시크릿 관리, DRY_RUN 기본값 |
| 부록 | AC 매핑 체크리스트 | 42개 AC + 비판자 14개 결함 전체 반영 확인 |

---

## types.py 변경 요약

### 신규 Enum (2개)
- `FrequencyMode`: TURBO, NORMAL, STEALTH, AUTO
- `ReactorType`: ALPHA, OMEGA

### 변경된 Enum
- `StrategyType`: 10전략 → 6코어(AMBIGUITY, ORACLE_FEAR, CONTRARIAN, CORRELATED, LIQUIDITY_VACUUM, COMPLETE_SET) + 3보조(MARKET_AGE, CROWDING, VOL_PRICE_DIVERGENCE). 제거: META_BRAIN, SETTLEMENT_DECAY, EVENT_CASCADE, MAKER_REBATE, WHALE_SHADOW
- `RiskRejectReason`: CORRELATION_LIMIT 제거, EXECUTION_COST/HOLDING_COST/DUPLICATE_ORDER 추가

### 변경된 Dataclass
- `Signal`: `reactor_source: ReactorType` 필드 추가
- `TradeDecision`: `reactor_source`, `golden_cross`, `holding_cost` 필드 추가
- `RiskLayerResult`: layer 범위 1~5 (v1.0은 1~6)
- `RiskCheck`: `correlation_groups` 제거, `frequency_mode` 추가
- `TradeResult`: `reactor_source`, `golden_cross`, `holding_cost`, `fee_cost` 필드 추가
- `DailyStats`: `alpha_signals`, `omega_signals`, `golden_crosses`, `frequency_mode` 필드 추가

### 신규 Dataclass (3개)
- `FrequencyState`: Governor 현재 상태 (모드, 주기, Kelly 배수)
- `HoldingCost`: 유지비용 계산 결과 (AC-41)
- `ExecutionFilter`: 실행 비용 필터 결과 (AC-42)

---

## 비판자 보고서 반영 상세

### CRITICAL 4건 — 전부 반영

| # | 결함 | 해소 방법 |
|---|------|-----------|
| CRITICAL-01 | 주말 드리프트 AC 누락 | contrarian.py에 주말 드리프트 감지 로직 설계 (평일 stdev x2 비교, confidence 보너스 +0.10) |
| CRITICAL-02 | 유지비용 AC 누락 | Risk Sentinel Layer 1에서 days_to_settlement / 365 * risk_free_rate를 edge에서 차감 |
| CRITICAL-03 | AC-12/AC-18 역할 경계 모호 | AC-12는 분석 전용(임계값 0.02), AC-18은 실행 트리거(임계값 0.03)로 명확 분리. implied conditional 정의 명시 |
| CRITICAL-04 | 중복 주문 방지 AC 부재 | AC-39(미체결 GTC 체크 + 포지션 방향 확인) + AC-40(Omega 우선, Alpha 큐 소거) |

### MINOR 10건 — 전부 반영

| # | 결함 | 해소 방법 |
|---|------|-----------|
| MINOR-01 | 모호성 키워드 사전 미정의 | Config.AMBIGUITY_KEYWORDS 리스트로 관리, 기본 13개 키워드 명시 |
| MINOR-02 | 분쟁 키워드 정의 부재 | Config.ORACLE_FEAR_KEYWORDS + 텍스트 매칭 방식 명시 (API 분쟁 이력 미제공 확인) |
| MINOR-03 | /holders API 존재 미확인 | data_client.get_holders()에서 404 시 None 반환 (graceful degradation) |
| MINOR-04 | Vol-Price Divergence 수치 기준 | VOL_PRICE_VOLUME_SURGE(3x), VOL_PRICE_VOLUME_DROUGHT(0.3x), VOL_PRICE_PRICE_THRESHOLD(0.02), VOL_PRICE_PRICE_VACUUM(0.05) |
| MINOR-05 | 전략 가중치 미명시 | Config.WEIGHT_* 6개 파라미터, 런타임 변경 가능 |
| MINOR-06 | DD 임계값 불일치 | Governor와 Sentinel은 독립 작동, 곱셈으로 중첩. AUTO DD 전환 테이블로 결합 효과 명시 |
| MINOR-07 | Governor 배수 미정의 | TURBO x1.0 / NORMAL x0.7 / STEALTH x0.4 + Stage 1/2 주기 명시 |
| MINOR-08 | 실행 비용 필터 부재 | AC-42: MIN_PROFIT_THRESHOLD($0.50), net_profit = expected_profit - fee_cost |
| MINOR-09 | WS 재연결 상태 복구 | 자동 재구독(_subscribed_assets) + REST 폴백으로 갭 메우기 |
| MINOR-10 | 소스 부재 분석 누락 | ambiguity.py에서 resolution_source 빈 문자열/null 체크 → source_penalty +0.2 |

---

## 설계 핵심 결정 (10개)

1. **듀얼 리액터 분리**: 시간 스케일이 다른 분석(분)과 차익(밀리초)을 독립 실행
2. **3단계 퍼널**: ~500 → ~50 → ~10으로 점진 필터링, Rate Limit 효율화
3. **Omega Signal Queue 우회**: 차익 기회의 시간 민감성을 위해 직접 Executor 연결
4. **AC-12/18 임계값 차별화**: 분석(0.02) vs 실행(0.03)으로 역할 분리
5. **Correlation Guard 제거**: Correlated 전략이 Stage 2에서 직접 상관 분석
6. **DD 이중 안전망**: Governor(빈도) + Sentinel(크기) 곱셈 중첩은 의도된 설계
7. **유지비용 Kelly 차감**: 장기 포지션의 기회비용을 edge에서 자동 반영
8. **보조지표 인라인 배치**: 독립 시그널 미생산 지표는 해당 전략 내부에 응집
9. **py-clob-client run_in_executor**: SDK 서명/인증 재사용, async 블로킹 방지
10. **DRY_RUN=true 기본값**: 테스트넷 없음(oracle_report 확인)에 대한 안전장치

---

## 예외/이슈 사항

없음. .plan.md(42 AC), oracle_report.md, critique_report.md 간 불일치 없었음.
42개 AC 전부 DESIGN.md에 반영 확인 (AC 매핑 체크리스트 참조).
비판자 CRITICAL 4건 + MINOR 10건 전부 해소.

---

**보고서 작성 완료**: 2026-02-17
**작성자**: Architect Agent
**상태**: 작업 완료

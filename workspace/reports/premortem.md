# Pre-mortem — Polymarket Reaper Bot v1.1

**작성일**: 2026-02-17

## 실패 시나리오 3개

### 시나리오 1: Rate Limit 병목으로 시그널 지연

**상황**: Reactor α Stage 1이 1000+개 마켓을 Gamma API로 스캔할 때 100 req/분 한도에 도달. Target List 생성이 5분 → 15분으로 지연. 그 사이 기회가 소멸.

**확률**: 중간 (마켓 수 증가 시 발생)

**완화 방안**:
- Gamma API 페이지네이션 캐시: 전체 마켓 목록은 5분 TTL 캐시. 변경분만 delta 조회.
- Stage 1은 캐시된 데이터로 분석, API 갱신은 백그라운드.
- Rate limit 카운터를 중앙 관리하여 Reactor α/Ω 간 배분.

### 시나리오 2: WebSocket 단절 중 Complete Set 기회 놓침

**상황**: WebSocket 연결이 끊어지고 재연결에 30초 소요. 그 동안 Complete Set 차익 기회 발생 및 소멸. Reactor Ω가 무방비 상태.

**확률**: 낮음 (WS 안정성에 의존)

**완화 방안**:
- WS 단절 감지 즉시 REST API 폴링 폴백 모드 (10초 주기).
- 재연결 성공 시 폴백 중단, WS 복귀.
- 재연결 5회 실패 시 REST 전용 모드로 운영 (성능 저하 허용).

### 시나리오 3: 전략 오판에 의한 연쇄 손실

**상황**: Ambiguity Scoring이 특정 카테고리 마켓들을 오판하여 다수의 NO 포지션 보유. 해당 카테고리에서 연쇄 YES 결제 발생. 일일 손실 8% 서킷에 도달.

**확률**: 중간 (모호성 판단은 주관적)

**완화 방안**:
- Correlation Guard가 같은 태그/카테고리 마켓 총 노출 제한 (Correlated Markets 전략 내 구현).
- Circuit Breaker(AC-26) 발동 시 당일 전면 중단 + 기존 GTC 취소.
- DRY_RUN 기간 동안 Ambiguity 키워드 사전을 실제 결과와 비교하여 튜닝.

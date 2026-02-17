# Pre-mortem: Polymarket Reaper Bot v1.0

## 실패 시나리오 1: WebSocket 연결 불안정으로 Whale Shadow/Liquidity Vacuum 무력화
**위험도**: HIGH
**원인**: Polymarket WebSocket 서버의 구독 해제 미지원, 연결 끊김 시 오더북 데이터 갭
**영향**: 실시간 전략 2개(Whale Shadow, Liquidity Vacuum)가 stale 데이터로 잘못된 시그널 생성 → 손실
**대응**:
- 자동 재연결 + 지수 백오프 (최대 5회, 1s→2s→4s→8s→16s)
- 연결 상태 heartbeat 모니터 (30초 무응답 → 재연결)
- stale 판정 타임스탬프: 마지막 메시지 후 60초 경과 시 해당 전략 시그널 자동 비활성화
- WebSocket 실패 시 REST 폴백으로 30초 주기 polling (degraded mode)

## 실패 시나리오 2: asyncio 동시성 경합으로 시그널 순서 역전 / 중복 주문
**위험도**: HIGH
**원인**: 10개 전략이 동시에 시그널 발행, Meta Brain과 Executor 간 race condition
**영향**: 같은 시장에 중복 주문, 또는 outdated 시그널이 최신보다 먼저 실행
**대응**:
- Signal Queue에 timestamp + sequence_number로 엄격한 정렬
- condition_id 기준 deduplication: 같은 시장에 60초 내 중복 시그널 무시
- Executor에 asyncio.Lock() per condition_id: 한 시장에 동시 주문 방지
- 모든 시그널에 TTL 부여 (Sniper: 10초, Patient: 120초), 만료된 시그널 자동 폐기

## 실패 시나리오 3: Rate Limit 초과로 API 차단 → 전략 polling 전면 마비
**위험도**: MEDIUM
**원인**: 10개 전략 × polling 주기가 100 req/min 공개 한도 초과, 429 연쇄 발생
**영향**: 시장 데이터 갱신 불가 → stale 데이터로 시그널 생성 → 손실 또는 기회 상실
**대응**:
- 전략별 polling 주기 분산 스케줄링: jitter(±20%) 추가
- Global rate limiter: asyncio.Semaphore + TokenBucket 알고리즘
  - 공개 API: 최대 80 req/min (한도의 80%)
  - 주문 API: 최대 45 orders/min (한도의 75%)
- 429 응답 시 지수 백오프 + Retry-After 헤더 존중
- WebSocket 데이터 우선 사용으로 REST 호출 최소화 (특히 오더북)

## 추가 리스크 메모
- **L2 서명 30초 만료**: 시그널→주문 파이프라인 지연 시 서명 만료 가능. 서명은 주문 직전에 생성.
- **py-clob-client 동기 한계**: SDK가 동기 전용. async wrapper에서 `run_in_executor`로 감싸되, 서명/주문 호출만 해당. 순수 HTTP는 aiohttp 직접 사용.
- **Complete Set 아비트라지**: neg_risk 마켓에서만 동작. neg_risk 필터 필수.

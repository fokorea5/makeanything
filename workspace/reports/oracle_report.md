# Oracle Agent Report: Polymarket API 조사

**작성일**: 2026-02-17
**에이전트**: Oracle
**목적**: Polymarket 자동매매봇 개발을 위한 API 철저 조사

---

## 1. Polymarket API 아키텍처 개요

Polymarket은 세 개의 독립된 API 레이어로 구성됩니다:

| API | 기본 URL | 역할 |
|-----|----------|------|
| **CLOB API** | `https://clob.polymarket.com` | 오더북 거래 (주문 생성/취소/조회) |
| **Gamma API** | `https://gamma-api.polymarket.com` | 마켓 메타데이터 및 탐색 |
| **Data API** | `https://data-api.polymarket.com` | 사용자 포지션/거래내역/포트폴리오 |

Polymarket의 구조는 **하이브리드 탈중앙화**입니다:
- 오프체인: 오퍼레이터가 매칭/정렬/실행 서비스 제공
- 온체인: Polygon 블록체인에서 비수탁(non-custodial) 방식으로 정산
- 콜래터럴: USDC.e (PoS) 사용
- 아웃컴 토큰: ERC-1155 기반 Conditional Token Framework (CTF)

---

## 2. CLOB API 엔드포인트

### 2.1 시스템/헬스체크 (인증 불필요)

```
GET  https://clob.polymarket.com/          # Health check
GET  https://clob.polymarket.com/time      # 서버 시간
```

**응답 예시 (`/time`)**:
```json
{
  "time": 1708185600000
}
```

---

### 2.2 마켓 목록 조회 (인증 불필요)

```
GET  https://clob.polymarket.com/markets
GET  https://clob.polymarket.com/markets/{condition_id}
```

**파라미터 (`/markets`)**:
- `next_cursor`: 페이지네이션 커서

**응답 예시**:
```json
{
  "limit": 100,
  "count": 100,
  "next_cursor": "abc123",
  "data": [
    {
      "condition_id": "0x1234...",
      "question_id": "0xabcd...",
      "tokens": [
        {
          "token_id": "39182227286566757...",
          "outcome": "Yes"
        },
        {
          "token_id": "82910112384751234...",
          "outcome": "No"
        }
      ],
      "rewards": {...},
      "minimum_order_size": 5,
      "minimum_tick_size": 0.01,
      "description": "Will X happen?",
      "category": "Politics",
      "end_date_iso": "2026-11-05T00:00:00Z",
      "game_start_time": null,
      "question": "Will X happen?",
      "market_slug": "will-x-happen",
      "active": true,
      "closed": false,
      "archived": false
    }
  ]
}
```

---

### 2.3 오더북 조회 (인증 불필요)

```
GET  https://clob.polymarket.com/book?token_id={token_id}
GET  https://clob.polymarket.com/books           # 복수 토큰 일괄 조회
```

**파라미터**:
- `token_id`: 아웃컴 토큰 ID

**응답 예시**:
```json
{
  "market": "0x1234...",
  "asset_id": "39182227286566757...",
  "bids": [
    {"price": "0.55", "size": "100.0"},
    {"price": "0.54", "size": "250.0"}
  ],
  "asks": [
    {"price": "0.56", "size": "150.0"},
    {"price": "0.57", "size": "200.0"}
  ],
  "hash": "0xabcd..."
}
```

---

### 2.4 가격 조회 (인증 불필요)

```
GET  https://clob.polymarket.com/price?token_id={token_id}&side=BUY
GET  https://clob.polymarket.com/prices            # 복수 토큰
GET  https://clob.polymarket.com/midpoint?token_id={token_id}
GET  https://clob.polymarket.com/midpoints         # 복수 토큰
GET  https://clob.polymarket.com/spread?token_id={token_id}
GET  https://clob.polymarket.com/last-trade-price?token_id={token_id}
```

**응답 예시 (`/midpoint`)**:
```json
{
  "mid": "0.555"
}
```

---

### 2.5 가격 히스토리 (인증 불필요)

```
GET  https://clob.polymarket.com/prices-history
```

**파라미터**:
- `token_id`: 토큰 ID
- `interval`: 기간 (예: `"1d"`, `"1w"`, `"1m"`, `"all"`)
- `fidelity`: 데이터 밀도 (선택)

**응답 예시**:
```json
{
  "history": [
    {"t": 1708099200, "p": 0.52},
    {"t": 1708185600, "p": 0.55},
    {"t": 1708272000, "p": 0.57}
  ]
}
```

---

### 2.6 주문 생성 (인증 필요 - L2)

```
POST  https://clob.polymarket.com/order        # 단일 주문
POST  https://clob.polymarket.com/orders       # 배치 주문 (최대 15개)
```

**요청 바디 (단일 주문)**:
```json
{
  "order": {
    "salt": 12345678,
    "maker": "0xUserAddress...",
    "signer": "0xSignerAddress...",
    "taker": "0x0000000000000000000000000000000000000000",
    "tokenId": "39182227286566757...",
    "makerAmount": "100000000",
    "takerAmount": "55000000",
    "expiration": "0",
    "nonce": "0",
    "feeRateBps": "0",
    "side": 0,
    "signatureType": 0,
    "signature": "0xSignatureHex..."
  },
  "owner": "0xUserAddress...",
  "orderType": "GTC"
}
```

**지원 orderType**:
- `GTC`: Good-Til-Cancelled (취소 전까지 유효)
- `GTD`: Good-Til-Date (특정 날짜까지)
- `FOK`: Fill-Or-Kill (전량 즉시 체결 또는 취소)
- `FAK`: Fill-And-Kill (부분 체결 허용, 나머지 취소)
- `postOnly`: 지정가 메이커 전용 (maker-only)

**응답 예시**:
```json
{
  "success": true,
  "errorMsg": "",
  "orderID": "0xOrderHash...",
  "transactionHash": "0x...",
  "status": "MATCHED",
  "takingAmount": "55000000",
  "makingAmount": "100000000"
}
```

---

### 2.7 주문 취소 (인증 필요 - L2)

```
DELETE  https://clob.polymarket.com/order/{order_id}           # 단일 취소
DELETE  https://clob.polymarket.com/orders                      # 복수 ID로 취소
DELETE  https://clob.polymarket.com/orders/all                  # 전체 취소
DELETE  https://clob.polymarket.com/orders/market               # 특정 마켓 전체 취소
```

---

### 2.8 주문 조회 (인증 필요 - L2)

```
GET  https://clob.polymarket.com/data/order/{order_hash}
GET  https://clob.polymarket.com/data/orders
```

**파라미터 (`/data/orders`)**:
- `market`: condition_id (선택)
- `asset_id`: token_id (선택)
- `before`: 타임스탬프 (선택)
- `after`: 타임스탬프 (선택)

---

### 2.9 거래내역 조회 (인증 필요 - L2)

```
GET  https://clob.polymarket.com/data/trades
```

**파라미터**:
- `maker_address`: 메이커 주소 (선택)
- `market`: condition_id (선택)
- `before`, `after`: 시간 필터 (선택)

---

### 2.10 수수료 조회 (인증 불필요)

```
GET  https://clob.polymarket.com/fee-rate-bps?token_id={token_id}
```

---

## 3. Gamma Markets API 엔드포인트

### 3.1 마켓 목록 및 상세

```
GET  https://gamma-api.polymarket.com/markets
GET  https://gamma-api.polymarket.com/markets/{id}
GET  https://gamma-api.polymarket.com/markets?slug={slug}
```

**파라미터 (`/markets`)**:
- `limit`: 결과 수 (기본값 100)
- `offset`: 페이지네이션
- `active`: true/false 필터
- `closed`: true/false 필터
- `tag_id`: 태그별 필터
- `order`: 정렬 기준
- `ascending`: true/false

**응답 예시**:
```json
[
  {
    "id": 503236,
    "question": "Will X happen?",
    "conditionId": "0x1234...",
    "slug": "will-x-happen",
    "resolutionSource": "https://...",
    "endDate": "2026-11-05",
    "liquidity": "125000.50",
    "startDate": "2026-01-01",
    "image": "https://...",
    "icon": "https://...",
    "description": "...",
    "outcomes": "[\"Yes\",\"No\"]",
    "outcomePrices": "[\"0.55\",\"0.45\"]",
    "volume": "850000.00",
    "active": true,
    "closed": false,
    "tags": [{"id": 1, "label": "Politics"}],
    "negRisk": false,
    "negRiskMarketID": ""
  }
]
```

### 3.2 이벤트 조회

```
GET  https://gamma-api.polymarket.com/events
GET  https://gamma-api.polymarket.com/events/{id}
```

### 3.3 태그 조회

```
GET  https://gamma-api.polymarket.com/tags
GET  https://gamma-api.polymarket.com/tags/{id}
GET  https://gamma-api.polymarket.com/tags/slug/{slug}
GET  https://gamma-api.polymarket.com/tags/{id}/related-tags
```

### 3.4 헬스체크

```
GET  https://gamma-api.polymarket.com/     # "OK" 반환
```

---

## 4. Data API 엔드포인트

### 4.1 포지션 조회 (공개 - 지갑 주소 필요)

```
GET  https://data-api.polymarket.com/positions?user={wallet_address}
```

**파라미터**:
- `user`: 지갑 주소 (필수)
- `market`: condition_id (선택)
- `event_id`: 이벤트 ID (선택)
- `redeemable`: true/false (선택)
- `mergeable`: true/false (선택)
- `limit`, `offset`: 페이지네이션

**응답 예시**:
```json
[
  {
    "proxyWallet": "0xProxyAddress...",
    "asset": "39182227286566757...",
    "conditionId": "0x1234...",
    "size": "100.0",
    "avgPrice": "0.55",
    "initialValue": "55.0",
    "currentValue": "58.5",
    "cashPnl": "3.5",
    "percentPnl": "6.36",
    "totalBought": "55.0",
    "realizedPnl": "0.0",
    "curPrice": "0.585",
    "outcome": "Yes",
    "title": "Will X happen?"
  }
]
```

### 4.2 포트폴리오 가치 조회

```
GET  https://data-api.polymarket.com/value?user={wallet_address}
```

### 4.3 사용자 활동 및 거래내역

```
GET  https://data-api.polymarket.com/activity?user={wallet_address}
GET  https://data-api.polymarket.com/trades?user={wallet_address}
```

### 4.4 마켓 홀더 조회

```
GET  https://data-api.polymarket.com/holders?token={token_id}
```

---

## 5. 인증 방식

### 5.1 인증 레벨 개요

Polymarket CLOB API는 **3단계 인증** 구조를 사용합니다:

| 레벨 | 명칭 | 필요 | 접근 범위 |
|------|------|------|-----------|
| L0 | 무인증 | 없음 | 공개 시세/오더북 조회 |
| L1 | 지갑 서명 | Polygon 개인키 | API 키 생성/파기 |
| L2 | API 키 (HMAC) | API키+시크릿+패스프레이즈 | 주문 생성/취소/조회, 거래내역 |

### 5.2 L1 인증 (EIP-712 지갑 서명)

L1은 **EIP-712 타입 데이터 서명** 방식입니다. API 키 발급에만 사용됩니다.

**서명 구조**:
```json
{
  "domain": {"name": "ClobAuthDomain", "version": "1", "chainId": 137},
  "types": {
    "ClobAuth": [
      {"name": "address", "type": "address"},
      {"name": "timestamp", "type": "string"},
      {"name": "nonce", "type": "int256"},
      {"name": "message", "type": "string"}
    ]
  },
  "message": {
    "address": "0xUserAddress...",
    "timestamp": "1708185600",
    "nonce": 0,
    "message": "This message attests that I control the given wallet."
  }
}
```

**엔드포인트**:
```
POST  https://clob.polymarket.com/auth/api-key         # 신규 생성 (L1 헤더 필요)
GET   https://clob.polymarket.com/auth/api-key         # 파생/조회 (L1 헤더 필요)
DELETE https://clob.polymarket.com/auth/api-key        # 삭제 (L1 헤더 필요)
```

**API 키 응답**:
```json
{
  "apiKey": "550e8400-e29b-41d4-a716-446655440000",
  "secret": "base64EncodedSecretString==",
  "passphrase": "randomPassphraseString"
}
```

### 5.3 L2 인증 (HMAC-SHA256 API 키)

L2는 **HMAC-SHA256**으로 각 요청에 서명합니다.

**서명 방법**:
```python
import hmac
import hashlib
import base64
from datetime import datetime

timestamp = str(int(datetime.now().timestamp()))
method = "POST"
path = "/order"
body = '{"order": {...}, "owner": "0x...", "orderType": "GTC"}'

# 서명 문자열: timestamp + method + path + body
message = timestamp + method + path + body

signature = base64.b64encode(
    hmac.new(
        base64.b64decode(api_secret),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
).decode('utf-8')
```

**L2 요청 헤더**:
```
POLY-ADDRESS: 0xYourAddress...
POLY-SIGNATURE: <hmac_signature>
POLY-TIMESTAMP: <unix_timestamp>
POLY-NONCE: <nonce>
POLY-API-KEY: <api_key>
POLY-PASSPHRASE: <passphrase>
Content-Type: application/json
```

**중요**: L2 서명은 30초 후 만료됩니다.

### 5.4 서명 유형 (Signature Type)

| 값 | 유형 | 설명 |
|----|------|------|
| 0 | EOA | MetaMask, 하드웨어 지갑 (직접 제어) |
| 1 | POLY_PROXY | Magic Link, 이메일 지갑 |
| 2 | GNOSIS_SAFE | 브라우저 프록시 지갑 |

### 5.5 테스트넷 여부

**공식 메인넷 전용** - Polymarket은 별도의 공개 테스트넷 환경을 제공하지 않습니다.
- Polygon Mumbai Testnet에 배포된 이력 있음 (현재는 Mainnet 전용)
- 봇 개발 시 소액으로 실거래 테스트 권장
- 공식 문서에서 sandbox/testnet URL을 명시하지 않음

---

## 6. Rate Limit

### 6.1 API별 요청 제한

| API | 제한 |
|-----|------|
| 공개 (Gamma/CLOB 공개) | 100 req/분 |
| CLOB 주문 엔드포인트 | 60 orders/분 (API 키당) |
| 배치 주문 (`/orders`) | 최대 15개 주문/콜 |
| 전체 CLOB | 3,000 req/10분 |

### 6.2 Rate Limit 처리

- HTTP 429 반환 시 지수 백오프(exponential backoff) 구현 필요
- Throttling 방식 (요청 지연, 즉시 거부 아님)
- 배치 주문 API로 여러 주문을 1회 호출로 처리 가능 (효율 향상)

### 6.3 WebSocket 지원

**WSS 엔드포인트**: 실시간 푸시 데이터 제공

**채널 유형**:

| 채널 | 용도 | 인증 |
|------|------|------|
| `market` | 가격 변화, 체결 이벤트, 최우선 호가 변화 | 불필요 |
| `user` | 내 주문 상태, 체결 알림 | L2 필요 |

**구독 메시지 예시**:
```json
// Market Channel 구독 (인증 불필요)
{
  "auth": {"apiKey": "", "secret": "", "passphrase": ""},
  "markets": ["0xConditionId1...", "0xConditionId2..."],
  "assets_ids": ["token_id_1", "token_id_2"],
  "type": "market"
}
```

```json
// User Channel 구독 (L2 인증 필요)
{
  "auth": {
    "apiKey": "your-api-key",
    "secret": "your-secret",
    "passphrase": "your-passphrase"
  },
  "type": "user"
}
```

**Market Channel 이벤트 타입**:
- `last_trade_price`: 최근 체결 정보 (asset_id, price, side, size, timestamp)
- `price_change`: 최우선 호가 변화 (asset_id, changes, event_type, market, timestamp, hash)
- `book`: 오더북 스냅샷

**WebSocket 제한사항**:
- 구독 해제(unsubscribe) 미지원
- Market 채널은 토큰 ID 구독 수 무제한 (기존 100개 제한 해제됨)
- Heartbeat: 연결 끊기면 모든 오픈 오더 자동 취소 (Rust 클라이언트)

---

## 7. 주문 실행 메커니즘

### 7.1 CLOB 구조

Polymarket의 CLOB는 **하이브리드 탈중앙화** 구조입니다:

```
사용자 → 서명된 주문 → CLOB 오퍼레이터 (오프체인 매칭) → Polygon 스마트컨트랙트 (온체인 정산)
```

- **오프체인**: 가격-시간 우선순위(price-time priority)로 매칭
- **온체인**: CTF Exchange 스마트컨트랙트에서 ERC-1155 토큰 전송

**통합 오더북 특성**:
- YES 매수 $0.60 = NO 매수 $0.40과 동일 (합산 = $1.00)
- 양쪽 아웃컴이 단일 오더북 공유 → 더 깊은 유동성

### 7.2 주문 유형 상세

| 유형 | 설명 | 특징 |
|------|------|------|
| GTC (Good-Til-Cancelled) | 취소 전까지 오더북에 대기 | 기본 지정가 주문 |
| GTD (Good-Til-Date) | 특정 만료 시각까지 유효 | 타임스탬프 지정 |
| FOK (Fill-Or-Kill) | 즉시 전량 체결 or 전량 취소 | 시장가 주문에 해당 |
| FAK (Fill-And-Kill) | 즉시 가능한 양만 체결, 나머지 취소 | 부분 체결 허용 |
| postOnly | 메이커 전용 (크로스 시 거부) | 리베이트 수취 목적 |

**주의**: `postOnly`와 FOK/FAK 동시 설정 불가 (거부됨)

### 7.3 수수료 구조

**기본 원칙**: 대부분의 마켓은 **수수료 0%** (완전 무료)

수수료가 부과되는 마켓 (예: 15분 크립토 마켓) 공식:
- **매도 (아웃컴 토큰 → USDC)**:
  ```
  feeQuote = baseRate × min(price, 1 − price) × size
  ```
- **매수 (USDC → 아웃컴 토큰)**:
  ```
  feeBase = baseRate × min(price, 1 − price) × (size / price)
  ```

**수수료 특성**:
- `min(price, 1−price)` 스케일링으로 극단 확률에서 수수료 감소
  - p=0.50: 최대 1.56% 유효 수수료율
  - p=0.10: ~0.20%
  - p=0.05: ~0.06%
- 수수료 상한: **10%**
- 메이커 리베이트: 테이커 수수료의 일부를 메이커에게 USDC로 일별 지급
- US DCM (규제 버전): 테이커 수수료 0.10% (10 bps)

### 7.4 최소 주문 금액

- **최소 주문 크기**: 마켓별로 다름 (`minimum_order_size` 필드 확인)
- **일반적 최소**: ~5 USDC
- **최대 주문 크기**: 사용 가능한 잔고로 제한
  ```
  maxOrderSize = underlyingAssetBalance − Σ(orderSize − orderFillAmount)
  ```
- **틱 사이즈**: `minimum_tick_size` 필드 (일반적으로 0.01)

### 7.5 사전 준비 (EOA 지갑)

MetaMask/하드웨어 지갑 사용 시 거래 전 토큰 승인 필요:
- USDC.e: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- Conditional Tokens (CTF): `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`

Magic/이메일 지갑은 자동 승인됨.

---

## 8. Python SDK 및 라이브러리

### 8.1 공식 Python 클라이언트 (py-clob-client)

**설치**:
```bash
pip install py-clob-client
# Python 3.9+ 필요
```

**GitHub**: https://github.com/Polymarket/py-clob-client
**PyPI**: https://pypi.org/project/py-clob-client/

#### 클라이언트 초기화

```python
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds

HOST = "https://clob.polymarket.com"
CHAIN_ID = POLYGON  # 137

# L0: 인증 없이 공개 데이터만 조회
client = ClobClient(HOST)

# L1+L2: 전체 트레이딩 (EOA 지갑)
client = ClobClient(
    host=HOST,
    key="0xYourPrivateKey...",
    chain_id=CHAIN_ID,
    creds=ApiCreds(
        api_key="your-api-key",
        api_secret="your-secret",
        api_passphrase="your-passphrase"
    ),
    signature_type=0  # EOA
)

# L1+L2: Magic/프록시 지갑
client = ClobClient(
    host=HOST,
    key="0xSignerPrivateKey...",
    chain_id=CHAIN_ID,
    creds=api_creds,
    signature_type=1,  # POLY_PROXY
    funder="0xFunderAddress..."  # 실제 자금 보유 주소
)
```

#### API 키 생성

```python
# L1 인증으로 API 키 생성 or 파생
api_creds = client.create_or_derive_api_creds()
print(f"API Key: {api_creds.api_key}")
print(f"Secret: {api_creds.api_secret}")
print(f"Passphrase: {api_creds.api_passphrase}")
```

#### 공개 데이터 조회

```python
# 헬스체크
ok = client.get_ok()

# 마켓 목록
markets = client.get_simplified_markets()
markets_paginated = client.get_markets(next_cursor="")

# 오더북
orderbook = client.get_order_book(token_id="39182227286566757...")

# 가격
mid = client.get_midpoint(token_id="39182227...")
price_buy = client.get_price(token_id="39182227...", side="BUY")
price_sell = client.get_price(token_id="39182227...", side="SELL")
last_price = client.get_last_trade_price(token_id="39182227...")
```

#### 주문 실행

```python
from py_clob_client.clob_types import OrderArgs, OrderType, MarketOrderArgs

# 지정가 주문 (GTC)
order_args = OrderArgs(
    token_id="39182227286566757...",
    price=0.55,       # 0.01 ~ 0.99
    size=100.0,       # 토큰 수량
    side="BUY"        # "BUY" or "SELL"
)
signed_order = client.create_order(order_args)
result = client.post_order(signed_order, OrderType.GTC)
print(f"Order ID: {result['orderID']}")

# 시장가 주문 (FOK)
market_args = MarketOrderArgs(
    token_id="39182227...",
    amount=50.0  # USDC 금액
)
market_order = client.create_market_order(market_args)
result = client.post_order(market_order, OrderType.FOK)

# 주문 취소
cancel_result = client.cancel(order_id="0xOrderHash...")
client.cancel_all()  # 전체 취소
```

#### 주문 및 포지션 조회

```python
from py_clob_client.clob_types import OpenOrderParams

# 오픈 주문 조회
orders = client.get_orders(OpenOrderParams(
    market="0xConditionId..."  # 선택
))

# 거래내역
trades = client.get_trades()
```

### 8.2 공식 AI Agent 프레임워크

**GitHub**: https://github.com/Polymarket/agents
**라이선스**: MIT

```bash
pip install polymarket-agents
```

자연어로 Polymarket 마켓 분석 및 자동 거래 가능.

### 8.3 비공식/커뮤니티 라이브러리

| 라이브러리 | PyPI | 설명 |
|-----------|------|------|
| `polymarket-apis` | `pip install polymarket-apis` | 비공식 래퍼 |
| `quantpylib` | `pip install quantpylib` | Polymarket 포함 멀티 거래소 |

### 8.4 Rust 클라이언트 (고성능)

**GitHub**: https://github.com/Polymarket/rs-clob-client

특징:
- 강 타입 요청 빌더
- 자동 하트비트 전송 (연결 끊기면 오픈 오더 자동 취소)
- Alloy 지원

### 8.5 Node.js 클라이언트

```bash
npm install @polymarket/clob-client
```

### 8.6 NautilusTrader 통합

[NautilusTrader](https://nautilustrader.io/docs/latest/integrations/polymarket/) - 고성능 알고리즘 트레이딩 플랫폼으로 Polymarket 통합 제공.

---

## 9. 제한사항

### 9.1 지역 제한 (Geographic Restrictions)

**현황 (2026-02-17 기준)**:
- **미국**: CFTC 승인으로 공식 접근 가능 (2025년 말 이후)
  - KYC (신원 확인) 필수
  - 등록된 FCM (Futures Commission Merchant)을 통해서만 거래
  - 일부 주(텍사스, 네바다, 매사추세츠, 테네시 등) 추가 제한 가능
- **OFAC 제재 국가**: 완전 차단 (이란, 북한, 러시아 특정 지역 등)
- **기타 규제 대응 국가**: 접근 제한 또는 close-only 모드

**VPN 우회**: Polymarket ToS 위반. 계정 정지/자금 동결 위험.

### 9.2 최소 주문 및 출금

- **최소 주문**: 마켓별 `minimum_order_size` 확인 (일반적 5 USDC)
- **최소 틱**: `minimum_tick_size` 확인 (일반적 0.01)
- **출금**: Polygon 네트워크를 통해 USDC 출금 (가스비 필요)
- **콜래터럴**: USDC.e (Polygon PoS Bridged USDC) 사용
- **정산**: 마켓 종료 후 CTF Exchange 스마트컨트랙트에서 자동 정산

### 9.3 기술적 제한

- 구독 해제 미지원 (WebSocket)
- L2 서명 만료: 30초
- 배치 주문: 최대 15개/콜
- API 키 만료: 만료 없음 (단, L1로 언제든 삭제/재생성 가능)
- 포지션 조회: CLOB API에 공식 지원 없음 (Data API 사용)

---

## 10. 자동매매봇 관련 정책

### 10.1 봇 트레이딩 허용 여부

**공식적으로 허용** - Polymarket은 봇/자동화 트레이딩을 명시적으로 지원합니다:

1. **공식 CLOB API** 제공: 마켓메이커 및 트레이더를 위한 프로그래밍 방식 주문 관리
2. **공식 AI Agent 프레임워크**: MIT 라이선스로 오픈소스 제공
3. **Gamma API 문서 명시**: "automated trading systems" 사용 사례를 명시적으로 언급
4. **메이커 리베이트**: 유동성 공급 봇을 장려하는 리베이트 프로그램 운영

### 10.2 ToS 관련 제약

- **지역 제한 우회 금지**: VPN으로 제한 국가에서 접근 금지
- **시장 조작 금지**: ToS에서 명시 (정확한 조항은 https://polymarket.com/tos 확인)
- **계정 공유 금지**: 단일 API 키는 단일 계정용
- **비허가 자동화**: 과도한 요청으로 서비스 방해 금지

### 10.3 봇 개발 시 권장사항

```python
import time
import logging
from py_clob_client.client import ClobClient

class PolymarketBot:
    def __init__(self, private_key, api_creds):
        self.client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=137,
            creds=api_creds
        )

    def safe_post_order(self, order, order_type, retries=3):
        """Rate limit 고려한 안전한 주문 실행"""
        for attempt in range(retries):
            try:
                result = self.client.post_order(order, order_type)
                return result
            except Exception as e:
                if "429" in str(e):
                    wait_time = 2 ** attempt  # 지수 백오프
                    logging.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif attempt == retries - 1:
                    raise
        return None
```

---

## 11. 빠른 시작 예시

### 11.1 환경 설정

```bash
pip install py-clob-client
```

```python
# .env
PRIVATE_KEY=0xYourPolygonPrivateKey
POLY_API_KEY=your-api-key
POLY_API_SECRET=your-secret
POLY_API_PASSPHRASE=your-passphrase
POLY_ADDRESS=0xYourWalletAddress
```

### 11.2 마켓 탐색 및 오더북 조회

```python
import os
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

# 공개 데이터 - 인증 불필요
client = ClobClient("https://clob.polymarket.com")

# 마켓 목록 (CLOB)
markets = client.get_simplified_markets()
for m in markets['data'][:3]:
    print(f"Market: {m['question']}")
    for token in m['tokens']:
        book = client.get_order_book(token['token_id'])
        mid = client.get_midpoint(token['token_id'])
        print(f"  {token['outcome']}: mid={mid['mid']}, bids={len(book['bids'])}, asks={len(book['asks'])}")

# Gamma API로 상세 마켓 메타데이터
import requests
resp = requests.get("https://gamma-api.polymarket.com/markets", params={
    "active": True,
    "closed": False,
    "limit": 10,
    "order": "volume",
    "ascending": False
})
top_markets = resp.json()
for m in top_markets:
    print(f"{m['question']}: volume=${float(m['volume']):,.0f}, prices={m['outcomePrices']}")
```

### 11.3 주문 실행 (인증 필요)

```python
import os
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType

client = ClobClient(
    host="https://clob.polymarket.com",
    key=os.environ["PRIVATE_KEY"],
    chain_id=POLYGON,
    creds=ApiCreds(
        api_key=os.environ["POLY_API_KEY"],
        api_secret=os.environ["POLY_API_SECRET"],
        api_passphrase=os.environ["POLY_API_PASSPHRASE"]
    )
)

TOKEN_ID = "39182227286566757926769923857730776203547401708661426564300709353277001600667"

# 지정가 매수 (GTC)
order_args = OrderArgs(
    token_id=TOKEN_ID,
    price=0.50,   # $0.50 per share
    size=10.0,    # 10 shares = $5.00 total
    side="BUY"
)
signed_order = client.create_order(order_args)
result = client.post_order(signed_order, OrderType.GTC)
print(f"Order placed: {result}")

# 오픈 주문 조회
open_orders = client.get_orders()
print(f"Open orders: {len(open_orders)}")

# 주문 취소
if open_orders:
    client.cancel(order_id=open_orders[0]['id'])
```

### 11.4 WebSocket 실시간 스트림

```python
import asyncio
import websockets
import json

async def subscribe_market():
    uri = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    async with websockets.connect(uri) as ws:
        subscribe_msg = {
            "auth": {},
            "assets_ids": ["39182227286566757..."],
            "type": "market"
        }
        await ws.send(json.dumps(subscribe_msg))

        async for message in ws:
            data = json.loads(message)
            if isinstance(data, list):
                for event in data:
                    if event.get('event_type') == 'price_change':
                        print(f"Price: {event['asset_id'][:10]}... @ {event.get('price')}")

asyncio.run(subscribe_market())
```

---

## 12. 핵심 요약 및 권장사항

### 12.1 API 선택 가이드

| 목적 | API | 인증 |
|------|-----|------|
| 마켓 목록/메타데이터 | Gamma API | 불필요 |
| 실시간 가격/오더북 | CLOB REST/WSS | 불필요 |
| 가격 히스토리 | CLOB REST | 불필요 |
| 주문 실행 | CLOB REST | L2 필요 |
| 포지션 조회 | Data API | 불필요 (지갑 주소) |
| 실시간 주문 상태 | CLOB WSS user 채널 | L2 필요 |

### 12.2 봇 개발 체크리스트

- [ ] Polygon 지갑 생성 및 USDC.e 준비
- [ ] `py-clob-client` 설치 (Python 3.9+)
- [ ] L1 서명으로 API 키 생성 (`create_or_derive_api_creds`)
- [ ] EOA 지갑의 경우 USDC, CTF 토큰 approve 설정
- [ ] Rate limit 준수: 60 orders/분, 100 req/분 (공개)
- [ ] 지수 백오프 재시도 로직 구현
- [ ] 배치 주문 API 활용 (최대 15개/콜)
- [ ] WebSocket으로 실시간 가격 수신
- [ ] `fee_rate_bps` 동적 조회 (하드코딩 금지)
- [ ] 지역 제한 확인 (VPN 사용 금지)

---

## Sources

- [Polymarket 공식 문서](https://docs.polymarket.com/)
- [CLOB API 소개](https://docs.polymarket.com/developers/CLOB/introduction)
- [CLOB 엔드포인트 목록](https://docs.polymarket.com/quickstart/reference/endpoints)
- [Gamma Markets API 개요](https://docs.polymarket.com/developers/gamma-markets-api/overview)
- [CLOB 인증](https://docs.polymarket.com/developers/CLOB/authentication)
- [API Rate Limits](https://docs.polymarket.com/quickstart/introduction/rate-limits)
- [WSS 개요](https://docs.polymarket.com/developers/CLOB/websocket/wss-overview)
- [Market Channel](https://docs.polymarket.com/developers/CLOB/websocket/market-channel)
- [User Channel](https://docs.polymarket.com/developers/CLOB/websocket/user-channel)
- [가격 히스토리](https://docs.polymarket.com/developers/CLOB/timeseries)
- [주문 생성](https://docs.polymarket.com/developers/CLOB/orders/create-order)
- [지역 제한](https://docs.polymarket.com/polymarket-learn/FAQ/geoblocking)
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client)
- [py-clob-client PyPI](https://pypi.org/project/py-clob-client/)
- [Polymarket Agents GitHub](https://github.com/Polymarket/agents)
- [Polymarket ToS](https://polymarket.com/tos)
- [NautilusTrader Polymarket 통합](https://nautilustrader.io/docs/latest/integrations/polymarket/)
- [Polymarket 자동매매봇 가이드 - QuantVPS](https://www.quantvps.com/blog/automated-trading-polymarket)
- [Polymarket API 아키텍처 분석 - Medium](https://medium.com/@gwrx2005/the-polymarket-api-architecture-endpoints-and-use-cases-f1d88fa6c1bf)
- [Polymarket 수수료 분석 - QuantJourney](https://quantjourney.substack.com/p/understanding-the-polymarket-fee)

---

**보고서 작성 완료**: 2026-02-17
**작성자**: Oracle Agent
**상태**: 조사 완료

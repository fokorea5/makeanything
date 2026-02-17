# Trading Hub

자동매매 봇 통합 관리 대시보드

## 프로젝트 소개

Trading Hub는 여러 암호화폐 및 주식 자동매매 봇을 한 곳에서 관리할 수 있는 웹 기반 대시보드입니다.

### 주요 기능

- **봇 관리**: 여러 봇을 등록하고 시작/중지, 상태 모니터링
- **자산 추적**: 봇별 잔고 및 전체 자산 현황 실시간 조회
- **거래 기록**: 모든 거래 내역을 필터링, 검색, 페이지네이션으로 열람
- **텔레그램 알림**: 봇 에러, 큰 거래, 일일 수익 등을 텔레그램으로 수신
- **실시간 업데이트**: WebSocket을 통한 실시간 봇 상태 갱신
- **수익률 차트**: Chart.js 기반 일별 수익률 및 자산 분배 시각화

### UI 설명

- **대시보드**: 봇 상태 카드 그리드, 전체 자산 요약, 수익률 라인 차트
- **봇 관리 페이지**: 봇 등록 폼, 봇 목록, ON/OFF 토글 버튼, 상태 뱃지
- **거래 내역 페이지**: 거래 테이블, 봇/기간/종목 필터, 페이지네이션
- **자산 현황 페이지**: 봇별 자산 테이블, 자산 분배 도넛 차트

---

## 기술 스택

### Backend
- **Python 3.11+**
- **FastAPI**: 비동기 웹 프레임워크, WebSocket 지원, 자동 API 문서
- **SQLAlchemy 2.0**: ORM (SQLite)
- **SQLite**: 로컬 데이터베이스 (개인 사용에 적합)
- **Cryptography (Fernet)**: API 키 암호화

### Frontend
- **HTML + Vanilla JavaScript**: 빌드 도구 없는 경량 구조
- **Chart.js (CDN)**: 수익률 및 자산 차트 시각화

### 알림
- **Telegram Bot API**: HTTP 직접 호출로 알림 전송

### 거래소 연동
- **pyupbit**: 업비트 API 연동
- **python-binance**: 바이낸스 API 연동
- **SimAdapter**: 실거래 없이 시뮬레이션 가능

---

## 설치 방법

### 1. 클론

```bash
git clone https://github.com/yourusername/trading-hub.git
cd trading-hub
```

### 2. 가상환경 생성

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 다음 값을 설정하세요:

```env
DATABASE_URL=sqlite:///./data/trading_hub.db
ENCRYPTION_KEY=your-fernet-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
BOT_TICK_INTERVAL=10
WS_PUSH_INTERVAL=3
```

> **ENCRYPTION_KEY 생성 방법**:
> ```python
> from cryptography.fernet import Fernet
> print(Fernet.generate_key().decode())
> ```

### 5. 실행

```bash
python main.py
```

앱이 시작되면:
- 웹 대시보드: [http://localhost:8000](http://localhost:8000)
- API 문서 (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Docker 실행

Docker Compose를 사용하면 더 간편하게 실행할 수 있습니다.

```bash
docker-compose up -d
```

컨테이너 중지:

```bash
docker-compose down
```

---

## 환경 변수 설명

| 변수명 | 설명 | 필수 | 기본값 |
|--------|------|------|--------|
| `DATABASE_URL` | SQLite DB 경로 | 아니오 | `sqlite:///./data/trading_hub.db` |
| `ENCRYPTION_KEY` | API 키 암호화에 사용되는 Fernet 키 | **예** | — |
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급받은 텔레그램 봇 토큰 | **예** | — |
| `TELEGRAM_CHAT_ID` | 텔레그램 알림을 받을 채팅 ID | **예** | — |
| `BOT_TICK_INTERVAL` | 봇이 `on_tick`을 호출하는 간격 (초) | 아니오 | `10` |
| `WS_PUSH_INTERVAL` | WebSocket 상태 push 간격 (초) | 아니오 | `3` |

### TELEGRAM_CHAT_ID 확인 방법

1. 텔레그램 봇에 `/start` 메시지 전송
2. 브라우저에서 다음 URL 접속:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. `"chat":{"id":123456789}` 에서 ID 확인

---

## 봇 추가 가이드

### 웹 대시보드에서 봇 추가

1. 웹 대시보드에서 **"봇 관리"** 페이지로 이동
2. **"봇 추가"** 버튼 클릭
3. 다음 정보를 입력:
   - **봇 이름**: 식별하기 쉬운 이름 (예: `Grid Bot BTC`)
   - **거래소 선택**: `upbit`, `binance`, 또는 `simulation`
   - **봇 타입**: 전략 유형 (예: `grid`, `dca`, `custom`)
   - **API 키** (선택): 거래소 API Key (암호화되어 DB에 저장됨)
   - **API Secret** (선택): 거래소 Secret Key
   - **설정 (JSON)**: 봇별 전략 파라미터
4. **"등록"** 버튼 클릭
5. 봇 목록에서 **시작 버튼**을 눌러 가동

### 시뮬레이션 봇 실행

실거래 없이 테스트하려면 거래소를 `simulation`으로 선택하세요.
API 키 입력 불필요하며, 랜덤 시세로 매매 시뮬레이션이 실행됩니다.

---

## 새 봇 타입 개발하기

Trading Hub는 확장 가능한 봇 프레임워크를 제공합니다.
새로운 전략의 봇을 만들려면 `BaseBot`을 상속하여 구현하세요.

### BaseBot 상속 예시

```python
# src/models/my_custom_bot.py
from src.models.base_bot import BaseBot
from src.models.exchange_adapter import ExchangeAdapter

class MyCustomBot(BaseBot):
    def __init__(self, bot_id: int, name: str, config: dict, adapter: ExchangeAdapter):
        super().__init__(bot_id, name, config, adapter)
        # 초기화 로직

    async def on_init(self) -> None:
        """봇 초기화. 거래소 연결, 설정 로드"""
        print(f"{self.name} 초기화 완료")

    async def on_tick(self) -> None:
        """주기적 실행 로직. 시세 확인, 전략 판단, 주문"""
        # 현재 시세 조회
        ticker = await self.adapter.get_ticker(self.config.get("symbol", "BTC/KRW"))

        # 전략 로직 (예: 이동평균 크로스)
        # ...

        # 주문 예시
        # order = await self.adapter.place_order(
        #     symbol="BTC/KRW",
        #     side="buy",
        #     quantity=0.01,
        #     price=ticker.current_price
        # )

    async def on_stop(self) -> None:
        """정리 작업. 연결 해제, 열린 주문 처리"""
        print(f"{self.name} 종료")
```

### 새 거래소 연동하기

새 거래소를 추가하려면 `ExchangeAdapter` 인터페이스를 구현하세요.

```python
# src/models/my_exchange_adapter.py
from src.models.exchange_adapter import ExchangeAdapter, AssetInfo, TickerInfo, OrderResult
from typing import List

class MyExchangeAdapter(ExchangeAdapter):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        # 거래소 클라이언트 초기화

    async def get_balance(self) -> List[AssetInfo]:
        """잔고 조회"""
        # 구현
        pass

    async def get_ticker(self, symbol: str) -> TickerInfo:
        """현재가 조회"""
        # 구현
        pass

    async def place_order(self, symbol: str, side: str, quantity: float, price: float = None) -> OrderResult:
        """주문 생성"""
        # 구현
        pass

    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        # 구현
        pass

    async def get_order_status(self, order_id: str):
        """주문 상태 조회"""
        # 구현
        pass
```

### 봇 등록 API 호출

```bash
curl -X POST http://localhost:8000/api/bots \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Bot",
    "exchange": "simulation",
    "type": "custom",
    "config": {
      "symbol": "BTC/KRW",
      "strategy": "my_strategy",
      "interval": 60
    }
  }'
```

---

## API 문서

### 주요 엔드포인트 요약

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/bots` | 봇 등록 |
| `GET` | `/api/bots` | 봇 목록 조회 |
| `GET` | `/api/bots/{bot_id}` | 봇 상세 조회 |
| `PATCH` | `/api/bots/{bot_id}/start` | 봇 시작 |
| `PATCH` | `/api/bots/{bot_id}/stop` | 봇 중지 |
| `DELETE` | `/api/bots/{bot_id}` | 봇 삭제 |
| `GET` | `/api/assets` | 봇별 자산 목록 |
| `GET` | `/api/assets/summary` | 전체 자산 요약 |
| `POST` | `/api/trades` | 거래 기록 저장 |
| `GET` | `/api/trades` | 거래 목록 조회 (필터/페이지네이션) |
| `POST` | `/api/alerts/test` | 테스트 알림 전송 |
| `GET` | `/api/alerts` | 알림 이력 조회 |
| `WS` | `/ws/status` | 실시간 봇 상태 스트림 |

### 자동 API 문서

FastAPI는 Swagger UI와 ReDoc을 자동으로 생성합니다.

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

API 문서에서 각 엔드포인트의 요청/응답 스키마, 필드 설명, Try it out 기능을 사용할 수 있습니다.

---

## 프로젝트 구조

```
trading-hub/
├── main.py                  # FastAPI 앱 진입점
├── requirements.txt         # Python 의존성
├── .env.example             # 환경변수 템플릿
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── api/                 # FastAPI 라우터
│   │   ├── bots.py          # 봇 관리 엔드포인트
│   │   ├── assets.py        # 자산 조회 엔드포인트
│   │   ├── trades.py        # 거래 기록 엔드포인트
│   │   ├── alerts.py        # 알림 엔드포인트
│   │   └── ws.py            # WebSocket 엔드포인트
│   ├── db/                  # 데이터베이스
│   │   ├── database.py      # SQLite 연결, 세션 관리
│   │   └── models.py        # SQLAlchemy ORM 모델
│   ├── models/              # 봇 프레임워크
│   │   ├── base_bot.py      # BaseBot 추상 클래스
│   │   ├── exchange_adapter.py  # ExchangeAdapter 인터페이스
│   │   └── sim_bot.py       # 시뮬레이션 봇 구현체
│   ├── shared/              # 공유 타입 (Pydantic 스키마)
│   │   └── types.py
│   ├── services/            # 공통 서비스
│   │   ├── encryption.py    # Fernet 암호화/복호화
│   │   └── telegram.py      # 텔레그램 알림 전송
│   ├── pages/               # HTML 페이지
│   │   ├── dashboard.html
│   │   ├── bots.html
│   │   ├── trades.html
│   │   └── assets.html
│   └── styles/              # CSS
│       └── main.css
├── static/                  # 프론트엔드 정적 파일
│   ├── app.js               # 메인 JS
│   ├── charts.js            # Chart.js 래퍼
│   └── ws.js                # WebSocket 클라이언트
├── tests/                   # 테스트
│   ├── test_api_bots.py
│   ├── test_api_assets.py
│   ├── test_api_trades.py
│   └── test_encryption.py
└── data/
    └── trading_hub.db       # SQLite DB 파일 (gitignore)
```

---

## 보안

### API 키 암호화

- 거래소 API 키는 **Fernet (대칭 암호화)**로 암호화되어 DB에 저장됩니다.
- `.env` 파일의 `ENCRYPTION_KEY`를 사용하여 암호화/복호화합니다.
- API 응답에는 **암호화 전 키가 절대 포함되지 않습니다**.

### 키 관리 규칙

- `ENCRYPTION_KEY`는 `.env`에만 존재해야 합니다.
- `.env` 파일은 반드시 `.gitignore`에 등록하세요.
- API 키를 코드에 하드코딩하지 마세요.

### CORS 설정

- 개발 환경: `allow_origins=["*"]`
- 운영 환경: 특정 도메인으로 제한 권장

---

## 테스트

```bash
pytest tests/
```

주요 테스트 항목:
- 봇 API (등록, 시작/중지, 삭제)
- 자산 API (조회, 요약)
- 거래 API (저장, 필터/페이지네이션)
- 봇 프레임워크 (BaseBot, SimBot)
- 암호화 (Fernet 암호화/복호화)

---

## 라이선스

MIT License

Copyright (c) 2026 Trading Hub

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 기여

이 프로젝트는 개인 프로젝트이지만, 이슈 제출이나 Pull Request는 환영합니다.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 문의

문제가 발생하거나 질문이 있으시면 [GitHub Issues](https://github.com/yourusername/trading-hub/issues)에 등록해주세요.

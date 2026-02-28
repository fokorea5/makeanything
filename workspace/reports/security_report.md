# Security Audit Report -- Polymarket 자동매매 트레이딩 봇

**Date:** 2026-02-17
**Auditor:** Security Agent (Opus)
**Scope:** `/workspace/projects/polymarket-bot/` 전체 소스코드

감사 대상 파일:
- `src/config.py`
- `src/api/polymarket_client.py`
- `src/api/gamma_client.py`
- `src/api/data_client.py`
- `src/api/rate_limiter.py`
- `src/db/database.py`
- `src/db/schema.sql`
- `src/engine/order_executor.py`
- `src/engine/risk_manager.py`
- `src/engine/trading_engine.py`
- `src/strategies/base.py`
- `src/shared/types.py`
- `src/main.py`
- `.env.example`
- `start.sh`
- `start.bat`

---

## 요약 (Executive Summary)

전체 16개 파일에 대해 8개 검증 항목을 감사했습니다.

| # | 항목 | 판정 | 심각도 |
|---|------|------|--------|
| a | 개인키/API키 로그 노출 | **PASS** | - |
| b | .env.example 실제 키 미포함 | **PASS** | - |
| c | SQL 파라미터 바인딩 | **PASS** | - |
| d | HTTP timeout 설정 | **PASS** | - |
| e | 에러 메시지 키 노출 | **WARN** | MEDIUM |
| f | 드라이런→실거래 전환 안전장치 | **PASS** | - |
| g | @risk 태그 사용 | **PASS** | - |
| h | .gitignore 설정 | **FAIL** | HIGH |

**FREEZE 해당 사항: 없음** (설계 변경 필요한 치명적 결함 없습니다. 발견된 모든 문제는 코드 수정으로 해결 가능.)

---

## 항목별 상세 분석

---

### (a) 개인키/API키가 로그에 노출되지 않는지

#### 판정: PASS

#### 분석

프로젝트 전체의 `logger.*` 호출을 검사했습니다.

**`src/api/polymarket_client.py`:**
- L68: `logger.info("PolymarketClient: L0 공개 조회 모드로 초기화 (dry_run=%s)", dry_run)` -- dry_run 불리언만 로깅. 양호.
- L83: `logger.info("PolymarketClient: L2 거래 모드로 초기화")` -- 키 정보 미포함. 양호.
- L347: `logger.error("place_limit_order 실패: %s", exc)` -- 예외 메시지만. 아래 (e) 항목 참조.

**`src/config.py`:**
- `validate_for_live_trading()` (L96-112): 누락된 환경 변수 **이름**만 에러에 포함 (`"POLY_PRIVATE_KEY"` 등). 실제 키 **값**은 포함되지 않음. 양호.

**`src/engine/trading_engine.py`:**
- L84-88: `PolymarketClient`에 `config.private_key`, `config.api_key` 등을 전달하지만 로깅하지 않음. 양호.
- L121-123: 모드, 사이클 간격, 전략 이름만 로깅. 양호.

**`src/main.py`:**
- L82: `print(f"설정 로드 오류: {exc}")` -- Config.from_env() 예외. 이 예외에 키 값이 포함될 가능성은 낮음 (환경 변수 파싱 오류).
- L120: `print(f"엔진 오류: {exc}")` -- 엔진 시작 예외를 stderr에 출력. 아래 (e) 참조.

**Config dataclass:**
- `Config` 클래스에 `__repr__`/`__str__` 커스텀 구현이 없으므로, dataclass 기본 `__repr__`이 사용될 경우 **모든 필드(private_key, api_secret 등)가 문자열에 포함**됩니다.
- 그러나 현재 코드에서 Config 객체를 직접 로그/print하는 코드는 **없습니다**.
- **권장 (MEDIUM):** Config dataclass에 `__repr__`을 오버라이드하여 민감 필드를 마스킹하세요. 향후 디버깅 시 실수로 `logger.info("config=%s", config)`를 추가하면 키가 노출됩니다.

---

### (b) .env.example에 실제 키 값이 포함되지 않는지

#### 판정: PASS

#### 분석

`.env.example` 파일 내용:
```
POLY_PRIVATE_KEY=0xYourPolygonPrivateKey
POLY_API_KEY=your-api-key
POLY_API_SECRET=your-api-secret
POLY_API_PASSPHRASE=your-api-passphrase
POLY_WALLET_ADDRESS=0xYourWalletAddress
```

- 모든 값이 **플레이스홀더 문자열** ("your-api-key", "0xYourPolygonPrivateKey" 등)입니다.
- 실제 키가 포함되어 있지 않음. **양호.**

---

### (c) SQL 쿼리에 파라미터 바인딩이 사용되는지 (f-string 금지)

#### 판정: PASS

#### 분석

`src/db/database.py`의 모든 SQL 실행문을 검사했습니다:

| 함수 | 쿼리 | 바인딩 |
|------|-------|--------|
| `insert_trade_log()` (L80-103) | `INSERT INTO trade_logs ... VALUES (?, ?, ?, ...)` | `?` 플레이스홀더 13개 |
| `get_recent_trades()` (L109-116) | `SELECT * FROM trade_logs ... LIMIT ?` | `?` 바인딩 |
| `insert_signal_logs()` (L142-150) | `INSERT INTO signal_logs ... VALUES (?, ?, ?, ...)` | `?` 플레이스홀더 11개, `executemany` 사용 |
| `insert_virtual_position()` (L162-179) | `INSERT INTO virtual_positions ... VALUES (?, ?, ?, ...)` | `?` 바인딩 8개 |
| `update_virtual_position_price()` (L188-199) | `SELECT ... WHERE token_id=? AND status='OPEN'` + `UPDATE ... WHERE id=?` | 모두 `?` 바인딩 |
| `get_open_virtual_positions()` (L204) | `SELECT * FROM virtual_positions WHERE status='OPEN'` | 파라미터 없음 (고정 쿼리) |
| `close_virtual_position()` (L211-228) | `SELECT ... WHERE id=?` + `UPDATE ... WHERE id=?` | `?` 바인딩 |
| `upsert_daily_pnl()` (L246-268) | `INSERT INTO daily_pnl ... VALUES (?, ?, ?, ...)` | `?` 바인딩 7개 |
| `get_today_pnl()` (L274-288) | `SELECT ... WHERE date=? AND dry_run=?` | `?` 바인딩 |
| `get_open_order_count()` (L293) | `SELECT COUNT(*) ... WHERE status='PENDING'` | 파라미터 없음 (고정 쿼리) |

- **모든 사용자 입력이 `?` 파라미터 바인딩을 통해 전달됩니다.**
- f-string이나 문자열 포매팅으로 SQL을 구성하는 코드가 **없습니다.**
- `_apply_schema()`는 `executescript()`로 DDL을 실행하지만, 이는 하드코딩된 schema.sql 파일이므로 위험 없음.
- **SQL 인젝션 위험 없음.**

---

### (d) HTTP 요청에 timeout이 설정되어 있는지

#### 판정: PASS

#### 분석

| 파일 | 위치 | timeout |
|------|------|---------|
| `polymarket_client.py` | `_rest_get()` L120 | `timeout=15` |
| `gamma_client.py` | `_get()` L43 | `timeout=15` |
| `data_client.py` | `_get()` L46 | `timeout=15` |

- 모든 직접 `requests.get()` 호출에 `timeout=15`(초)가 설정되어 있음. **양호.**
- `py-clob-client` SDK를 통한 호출 (`_call_with_retry`)은 SDK 내부 timeout에 의존하지만, `_call_with_retry`가 3회 재시도 후 `RuntimeError`를 발생시키므로 무한 대기는 방지됨.
- **권장 (LOW):** SDK 호출에도 외부 타임아웃(예: `signal.alarm` 또는 threading 기반)을 적용하면 더 안전합니다. SDK 내부에서 무한 대기가 발생할 가능성은 낮지만, 네트워크 장애 시 방어가 됩니다.

---

### (e) 에러 메시지에 API 키/개인키가 포함되지 않는지

#### 판정: WARN (심각도: MEDIUM)

#### 분석

**직접 노출 없음 (PASS 부분):**
- 로그 메시지에 API 키/개인키 값을 직접 포함하는 코드가 **없습니다.**
- `validate_for_live_trading()`: 누락된 키의 **이름**만 출력 ("POLY_PRIVATE_KEY"), 값은 출력하지 않음.

**간접 노출 위험 (WARN 부분):**

1. **`polymarket_client.py` L347-348:**
   ```python
   except Exception as exc:
       logger.error("place_limit_order 실패: %s", exc)
       return self._failed_result(token_id, side, price, size, str(exc))
   ```
   - `str(exc)`가 `OrderResult.error_message`에 저장되고, 이 값이 DB `trade_logs.error_message` 컬럼에 기록됨 (L103).
   - py-clob-client SDK가 인증 실패 시 응답 본문(API 키가 포함될 수 있는)을 예외 메시지에 포함할 가능성이 있음.
   - **위험도: MEDIUM** -- SDK의 예외 메시지 형식에 따라 다름.

2. **`order_executor.py` L188-189:**
   ```python
   logger.error("_execute_live 예외: %s", exc, exc_info=True)
   return self._failed_result(decision, price, str(exc))
   ```
   - `exc_info=True`는 전체 스택 트레이스를 로그에 기록. 스택에 로컬 변수(API 키 포함 가능)가 나타날 수 있음.
   - **위험도: MEDIUM**

3. **`main.py` L119:**
   ```python
   logger.error("엔진 시작 오류: %s", exc, exc_info=True)
   ```
   - 엔진 초기화 중 예외 발생 시 스택 트레이스에 Config 객체의 민감 정보가 포함될 수 있음.

4. **`main.py` L82, L120:**
   ```python
   print(f"설정 로드 오류: {exc}", file=sys.stderr)
   print(f"엔진 오류: {exc}", file=sys.stderr)
   ```
   - 콘솔(stderr)에 예외 문자열 직접 출력. 로컬 실행이므로 네트워크 노출 위험은 낮지만, 로그 수집 시스템에 전송될 수 있음.

**권장:**
- `exc_info=True` 사용 시 로그 레벨을 `DEBUG`로 제한하거나, 프로덕션에서 스택 트레이스를 비활성화.
- `error_message` DB 저장 시 민감 정보를 필터링하는 sanitize 함수 추가.
- Config에 `__repr__` 오버라이드 추가.

---

### (f) 드라이런→실거래 전환 시 안전장치가 있는지

#### 판정: PASS

#### 분석

**다중 안전장치가 구현되어 있음:**

1. **기본값 안전 (config.py L32):**
   ```python
   dry_run: bool = True  # DRY_RUN (기본값 True = 안전)
   ```
   - `.env` 미설정 시, CLI 인자 미지정 시 기본값이 `True`(드라이런). **양호.**

2. **환경 변수 파싱 (config.py L74):**
   ```python
   dry_run = _bool(os.environ.get("DRY_RUN", ""), True)
   ```
   - 빈 문자열이나 잘못된 값일 때 기본값 `True` 반환. **양호.**

3. **CLI 플래그 명시 (main.py L33-38):**
   ```python
   parser.add_argument("--live", action="store_true", default=False, ...)
   ```
   - `--live` 플래그를 명시적으로 전달해야만 실거래 활성화. **양호.**

4. **실거래 경고 + 5초 대기 (main.py L96-107):**
   ```python
   if not config.dry_run:
       print("\n[경고] 실거래 모드가 활성화되었습니다.\n"
             "        실제 USDC가 사용됩니다. 5초 후 시작합니다.\n"
             "        중단하려면 Ctrl+C를 누르세요.\n")
       time.sleep(5)
   ```
   - 사용자에게 경고 후 5초 취소 기회 제공. `KeyboardInterrupt` 처리됨. **양호.**

5. **자격증명 검증 (config.py L91-112 + trading_engine.py L134-137):**
   ```python
   if not self.config.dry_run:
       self.config.validate_for_live_trading()
   ```
   - 실거래 시 5개 필수 키(POLY_PRIVATE_KEY, API_KEY, SECRET, PASSPHRASE, WALLET_ADDRESS) 존재 검증. 누락 시 `ValueError` 발생으로 엔진 시작 차단. **양호.**

6. **OrderExecutor 경고 (order_executor.py L49-53):**
   ```python
   if not dry_run:
       logger.warning("OrderExecutor: 실거래 모드 활성화. ...")
   ```

7. **가격 유효성 검사 (order_executor.py L137-142):**
   ```python
   if not (0.01 <= price <= 0.99):
       return self._failed_result(decision, price, "비정상 가격")
   ```
   - 비정상 가격(0.01 미만, 0.99 초과) 주문 자동 거부. **양호.**

8. **리스크 관리자 (risk_manager.py):**
   - 일일 손실 한도, 오픈 주문 수 한도, 포트폴리오 노출 한도, 단일 시장 집중도 한도, 최소/최대 주문 크기 제한 등 5단계 리스크 검사. **양호.**

**결론:** 드라이런→실거래 전환에 충분한 다중 안전장치가 구현되어 있음.

---

### (g) 금융 거래 관련 @risk 태그가 적절히 사용되었는지

#### 판정: PASS

#### 분석

| 파일 | 위치 | 태그 | 적절성 |
|------|------|------|--------|
| `config.py` L94 | `validate_for_live_trading()` | `@risk: 금융거래` | O -- 실거래 설정 검증 |
| `polymarket_client.py` L5-6 | 모듈 독스트링 | `@risk: 금융거래` | O -- 모듈 수준 경고 |
| `polymarket_client.py` L40 | 클래스 독스트링 | `@risk: 금융거래` | O -- L2 자격증명 노출 경고 |
| `polymarket_client.py` L71 | L2 초기화 | `@risk: 금융거래` | O -- private_key 노출 금지 명시 |
| `polymarket_client.py` L289 | 거래 섹션 주석 | `@risk: 금융거래` | O |
| `polymarket_client.py` L302 | `place_limit_order` | `@risk: 금융거래` | O -- USDC 소비 명시 |
| `polymarket_client.py` L353 | `place_market_order` | `@risk: 금융거래` | O -- 슬리피지 경고 |
| `polymarket_client.py` L392 | `cancel_order` | `@risk: 금융거래` | O -- 취소 실패 위험 |
| `polymarket_client.py` L407 | `cancel_all_orders` | `@risk: 금융거래` | O -- 전체 취소 위험 |
| `order_executor.py` L8 | 모듈 독스트링 | `@risk: 금융거래` | O |
| `order_executor.py` L36 | 클래스 독스트링 | `@risk: 금융거래` | O |
| `order_executor.py` L64 | `execute()` | `@risk: 금융거래` | O |
| `order_executor.py` L126 | `_execute_live()` | `@risk: 금융거래` | O |
| `order_executor.py` L147 | 주문 제출 | `@risk: 금융거래` | O |
| `data_client.py` L25 | 클래스 독스트링 | `@risk: 개인정보` | O -- wallet_address 노출 경고 |

- 실제 자금을 소비/이동하는 모든 코드 경로에 `@risk: 금융거래` 태그가 적절히 표시됨.
- DataClient의 개인정보 위험도 `@risk: 개인정보`로 표시됨.
- **양호.**

---

### (h) .gitignore에 .env, data/ 등이 포함되어야 하는지 확인

#### 판정: FAIL (심각도: HIGH)

#### 분석

**프로젝트 수준 .gitignore 파일이 없습니다.**

`polymarket-bot/` 디렉토리 내에 `.gitignore` 파일이 존재하지 않습니다.

루트 레벨 `.gitignore` (`/home/user/makeanything/.gitignore`) 내용:
```
.env
db/*.db
__pycache__/
*.pyc
.plan.md
DESIGN.md
workspace/reports/*.md
workspace/alerts/*.md
!workspace/**/.gitkeep
```

**문제점:**

1. **`.env` 패턴은 루트 `.gitignore`에 포함되어 있음** -- 그러나 이는 루트 디렉토리의 `.env`만 매칭. `workspace/projects/polymarket-bot/.env`도 매칭됨 (`.env` 패턴은 경로 구분자가 없으므로 하위 디렉토리에도 적용). **부분적으로 양호.**

2. **`data/` 디렉토리가 .gitignore에 없음** -- `polymarket-bot/data/polymarket_bot.db`에 거래 기록, 시그널 로그 등이 저장되는데, 이 디렉토리가 Git 추적에서 명시적으로 제외되지 않음. `db/*.db`는 루트의 `db/` 하위만 매칭하므로, `workspace/projects/polymarket-bot/data/*.db`는 **매칭되지 않음**.
   - **위험: 거래 기록 DB가 실수로 커밋될 수 있음.**
   - 심각도: **HIGH** -- DB에 condition_id, token_id, 거래 전략, 포지션 정보 등이 포함됨.

3. **`*.db` 패턴은 루트 `.gitignore`에 포함됨** -- 이 패턴은 하위 디렉토리에도 적용되므로 `.db` 파일 자체는 제외됨. 그러나 `data/` 디렉토리 내의 다른 파일(로그 등)은 제외되지 않음.

**권장:**
- `workspace/projects/polymarket-bot/.gitignore` 파일 생성:
  ```
  .env
  data/
  __pycache__/
  *.pyc
  *.db
  ```
- 또는 루트 `.gitignore`에 `**/data/` 패턴 추가.

---

## 추가 발견 사항

---

### SEC-1: Config __repr__ 민감 정보 노출 가능성

**심각도: MEDIUM**

`Config` dataclass (`src/config.py`)에 `__repr__` 오버라이드가 없습니다. Python dataclass의 기본 `__repr__`은 모든 필드를 포함하므로:

```python
Config(private_key='0xABCDEF...', api_key='...', api_secret='...', ...)
```

현재 코드에서 Config 객체를 직접 로깅/출력하지 않지만, 향후 디버깅 중 실수로 노출 가능.

**권장:** Config에 `__repr__` 추가:
```python
def __repr__(self) -> str:
    return f"Config(dry_run={self.dry_run}, log_level='{self.log_level}', db_path='{self.db_path}')"
```

---

### SEC-2: SQLite check_same_thread=False

**심각도: LOW**

`database.py` L41:
```python
self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
```

- 현재 코드는 단일 스레드(동기 메인 루프)로 동작하므로 실질적 위험은 낮음.
- 그러나 향후 멀티스레드/비동기 확장 시 동시 쓰기로 데이터 손상 가능.
- WAL 모드 사용(`PRAGMA journal_mode=WAL`)으로 읽기 동시성은 양호하지만 쓰기 동시성은 보장 안 됨.

---

### SEC-3: start.sh 자동 .env 복사

**심각도: LOW**

`start.sh` L42-44:
```bash
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
```

- `.env` 파일이 없을 때 `.env.example`을 자동 복사함.
- 복사된 `.env`에는 플레이스홀더 값만 있으므로 실거래는 작동하지 않지만, 사용자가 이를 인식하지 못하고 드라이런을 실행할 수 있음.
- `start.bat`에도 동일한 로직 존재.
- **실질적 위험 낮음** (드라이런 기본값이므로 자금 손실 없음).

---

### SEC-4: HTTP 요청에 HTTPS 강제 확인

**심각도: INFO (양호)**

모든 API 엔드포인트가 HTTPS를 사용:
- `CLOB_HOST = "https://clob.polymarket.com"`
- `GAMMA_BASE_URL = "https://gamma-api.polymarket.com"`
- `DATA_BASE_URL = "https://data-api.polymarket.com"`

TLS/HTTPS가 하드코딩되어 있어 중간자 공격 위험 없음. **양호.**

---

### SEC-5: Rate Limiter 서비스 거부 방지

**심각도: INFO (양호)**

- 슬라이딩 윈도우 방식 80 req/분 제한 (API 한도 100의 80%).
- 429 응답 시 지수 백오프 (1초, 2초, 4초) + 최대 3회 재시도.
- IP 차단 방지에 적절한 구현. **양호.**

---

### SEC-6: 인증 구조

**심각도: INFO (해당 사항 없음)**

- 이 프로젝트는 웹 서버가 아닌 **로컬 CLI 봇**입니다.
- HTTP API를 제공하지 않으므로 인증/인가/CORS 등의 웹 보안 항목은 해당 없음.
- Polymarket API 인증은 py-clob-client SDK의 L2 서명 방식을 올바르게 사용.

---

## 전체 판정 요약

| # | 항목 | 판정 | 심각도 | 비고 |
|---|------|------|--------|------|
| a | 개인키/API키 로그 노출 | **PASS** | - | 직접 노출 없음. Config __repr__ 주의 (SEC-1) |
| b | .env.example 실제 키 | **PASS** | - | 플레이스홀더만 포함 |
| c | SQL 파라미터 바인딩 | **PASS** | - | 모든 쿼리에 `?` 바인딩 사용 |
| d | HTTP timeout | **PASS** | - | 모든 요청에 `timeout=15` |
| e | 에러 메시지 키 노출 | **WARN** | MEDIUM | `str(exc)`/`exc_info=True`로 간접 노출 가능 |
| f | 드라이런→실거래 안전장치 | **PASS** | - | 7단계 안전장치 (기본값/CLI/경고/5초대기/키검증/가격검증/리스크) |
| g | @risk 태그 | **PASS** | - | 모든 금융거래 코드에 적절히 표시 |
| h | .gitignore | **FAIL** | HIGH | 프로젝트 .gitignore 없음. data/ 디렉토리 Git 제외 안 됨 |
| - | Config __repr__ | **WARN** | MEDIUM | 민감 필드 마스킹 필요 (SEC-1) |
| - | SQLite thread-safety | **INFO** | LOW | 현재 단일 스레드라 위험 낮음 (SEC-2) |
| - | start.sh 자동 .env 복사 | **INFO** | LOW | 플레이스홀더라 실질 위험 낮음 (SEC-3) |

---

## 수정 권장사항 (우선순위 순)

1. **[HIGH] .gitignore 생성** (`workspace/projects/polymarket-bot/.gitignore`):
   ```
   .env
   data/
   __pycache__/
   *.pyc
   *.db
   ```

2. **[MEDIUM] Config __repr__ 오버라이드** (`src/config.py`):
   - 민감 필드(private_key, api_key, api_secret, api_passphrase)를 마스킹하여 실수 로깅 방지.

3. **[MEDIUM] 에러 메시지 sanitize** (`src/api/polymarket_client.py`, `src/engine/order_executor.py`):
   - `str(exc)`를 DB에 저장하기 전 민감 정보 필터링.
   - `exc_info=True` 사용을 DEBUG 레벨로 제한.

4. **[LOW] SDK 호출 외부 타임아웃** (`src/api/polymarket_client.py`):
   - `_call_with_retry`에 전체 타임아웃 추가.

---

## FREEZE 해당 사항

**없음.** 발견된 모든 문제는 코드 수정으로 해결 가능하며, 설계 변경이 필요한 치명적 결함은 없습니다.

# Nugget 빌드 설계 v5.7

> AI 대화(Claude, ChatGPT, Gemini) 자동 저장 크롬 확장 프로그램
> 완전 로컬 저장. MV3. Freemium (무료 500개 / Pro 무제한).

---

## 기술 스택

- Manifest V3 Chrome Extension
- Vanilla JS (번들러 없음)
- chrome.storage.local + unlimitedStorage
- ExtensionPay (extpay npm v3.1.2) — 결제
- 자체 i18n (chrome.i18n은 런타임 언어 변경 불가)

---

## 디렉토리 구조

```
nugget/
├── manifest.json
├── src/
│   ├── background/background.js       # Service Worker (메시지 허브, 저장, ExtensionPay)
│   ├── content/
│   │   ├── interceptor.js             # MAIN world — fetch 오버라이드 (API 가로채기)
│   │   ├── bridge.js                  # ISOLATED world — CustomEvent → sendMessage
│   │   ├── claude.js                  # DOM 셀렉터 폴백
│   │   ├── chatgpt.js                # DOM 셀렉터 폴백
│   │   ├── gemini.js                 # DOM 셀렉터 폴백
│   │   └── extpay-content.js         # ExtensionPay 결제 콜백
│   ├── popup/    (html + js + css)
│   ├── options/  (html + js + css)
│   ├── onboarding/ (html + js + css)
│   ├── config/selectors.js            # 플랫폼별 DOM 셀렉터 (핫패치)
│   ├── shared/
│   │   ├── types.js                   # JSDoc 타입
│   │   ├── constants.js               # 상수
│   │   └── utils.js                   # 해싱, 잡담필터, 태깅
│   ├── utils/
│   │   ├── i18n.js                    # 자체 i18n (ko/en)
│   │   └── theme.js                   # 라이트/다크/시스템 테마
│   ├── i18n/ (ko.json, en.json)
│   └── lib/ExtPay.js                  # ExtensionPay 라이브러리 복사
└── assets/ (아이콘)
```

---

## 핵심 아키텍처

### 대화 캡처 — 이중 경로

```
[메인] interceptor.js(MAIN world) → fetch 오버라이드 → SSE 파싱
         → CustomEvent → bridge.js(ISOLATED) → API_CAPTURE → Background

[폴백] content script(claude.js 등) → MutationObserver → DOM 셀렉터
         → SAVE_ENTRY → Background

Background에서 해시 기반 중복 제거 (둘 다 잡힐 경우 API 우선)
```

### 메시지 흐름

모든 통신은 `chrome.runtime.sendMessage`, `{ type, payload }` 형식.

**주요 메시지:**
| 방향 | type | 용도 |
|------|------|------|
| Content → BG | `SAVE_ENTRY` | DOM 캡처 대화 저장 |
| bridge → BG | `API_CAPTURE` | API 캡처 대화 저장 |
| Content → BG | `SELECTOR_FAILED` | 셀렉터 깨짐 알림 |
| Popup → BG | `GET_ENTRIES`, `SEARCH_ENTRIES` | 조회/검색 |
| Popup → BG | `TOGGLE_STAR`, `UPDATE_NOTE`, `COPY_MARKDOWN` | 카드 액션 |
| Popup/Options → BG | `GET_SETTINGS`, `UPDATE_SETTINGS` | 설정 |
| Popup/Options → BG | `GET_PRO_STATUS`, `OPEN_PAYMENT_PAGE` | Pro |
| Options → BG | `EXPORT_JSON`, `IMPORT_JSON` | 백업/복원 |
| ExtPay → BG | `PRO_STATUS_CHANGED` | 결제 완료 |

---

## 스토리지

| 키 | 내용 |
|----|------|
| `nugget_entries` | NuggetEntry[] — 대화 목록 |
| `nugget_settings` | 설정 (toast, junkFilter, language, theme, isPro, mdCopyCount 등) |
| `nugget_junk_keywords` | 잡담 키워드 목록 |
| `nugget_pro_cache` | Pro 상태 캐시 (7일 유효) |
| `nugget_remote_selectors` | 원격 셀렉터 캐시 (24시간 갱신) |
| `nugget_api_capture_hashes` | API 캡처 해시 (중복 방지, 최근 100개) |

### NuggetEntry
```
{ id, date(ISO), platform, question, answer, tags[], starred, isJunk, archived, sourceUrl, note, hash }
```

### NuggetSettings
```
{ toastEnabled, junkFilterEnabled, shortcutKey, maxFreeEntries(500),
  isPro, mdCopyCount, mdCopyResetDate, language('ko'|'en'|'auto'), theme('light'|'dark'|'system') }
```

---

## 핵심 로직

### 잡담 필터 (2단계, OR)
1. 길이 기준: CJK면 질문 15자미만 AND 답변 200자미만 → junk. 라틴이면 5단어미만 AND 답변 200자미만 → junk
2. 키워드: question.trim().toLowerCase()가 키워드 exact match → junk

### 자동 태깅
question+answer에서 키워드 매칭 → 코딩/글쓰기/업무/학습/크리에이티브/기타

### 중복 방지
`djb2(question + "|" + answer앞200자 + "|" + date)` → 기존 entries와 비교

### 무료 한도
- 500개 초과 시 오래된 것 archived:true (삭제 아님)
- MD 복사 월 20회, 메모 200자, 커스텀 태그 잠금
- Pro 업그레이드 시 전부 해제

### Pro 상태
- ExtensionPay getUser() → 캐시 7일
- 오프라인 + 캐시 유효 → Pro 유지
- 오프라인 + 캐시 만료 → Pro 유지 + "확인 필요" 배너

---

## API 가로채기 상세

### interceptor.js (MAIN world, document_start)
1. `window.fetch` 오버라이드
2. URL 패턴 매칭: claude `/api/.*/completion`, chatgpt `/backend-api/conversation`, gemini `/batchexecute`
3. `response.body.tee()` → 원본은 페이지로, 복제본은 파싱
4. 플랫폼별 SSE 파서:
   - Claude: `content_block_delta` → `delta.text` 이어붙이기
   - ChatGPT: `data:` 줄 → 마지막의 `message.content.parts[]`
   - Gemini: JSON 배열 파싱 (실패 빈번 → 조용히 폴백)
5. 파싱 성공 → `CustomEvent('__nugget_api_capture__')` 발송
6. 실패(어떤 이유든) → null 반환 → DOM 폴백이 알아서 처리

### bridge.js (ISOLATED world, document_start)
- `__nugget_api_capture__` 이벤트 수신 → `chrome.runtime.sendMessage({ type: 'API_CAPTURE' })`
- 이 한 가지 역할만 수행

### 중복 저장 방지
- Background: API_CAPTURE 저장 성공 시 해시를 `nugget_api_capture_hashes`에 기록
- Content Script: SAVE_ENTRY 전에 500ms 지연 (API가 먼저 처리될 여유)
- Background: SAVE_ENTRY 수신 시 해시가 이미 있으면 무시

---

## 원격 셀렉터 핫패치

- `chrome.alarms` 24시간 주기 → GitHub Raw JSON fetch
- 스키마 검증 후 `nugget_remote_selectors`에 캐시
- Content Script에서 셀렉터 사용 시: 원격 있으면 우선, 없으면 로컬 폴백

---

## i18n

- `src/i18n/ko.json`, `en.json` — 전체 UI 문자열
- HTML: `data-i18n="키"` 속성으로 마킹
- JS: `await initI18n()` → `t('key')` 로 번역
- 언어 변경: Options 즉시 반영(DOM 교체), Popup 다음 열 때, 토스트 storage.onChanged

---

## 다크모드

- CSS 커스텀 속성으로 관리: `[data-theme="light"]` / `[data-theme="dark"]`
- `theme.js`: initTheme() → settings 읽기 → `<html data-theme="...">` 설정
- system 모드: `prefers-color-scheme` 미디어쿼리 리스너로 실시간 감지
- 기존 Nugget Gold(#F5A623)는 다크 배경에서 대비 4.8:1 → 변경 없이 유지
- 플랫폼 컬러는 다크에서 밝기 +15~20% 조정

---

## Popup UI 구조

```
400px x 580px 고정

┌─ Today's Nugget (과거 대화 랜덤 1개) ─────── [X] ─┐
├─ [🔍 검색...] [필터▼] ───────────────────────────┤
├─ [Claude][ChatGPT][Gemini] [기간▼][태그▼] [★][잡담]┤
├─ 카드 리스트 (스크롤) ─────────────────────────────┤
│  ▌ Q: ... A: ... 📅날짜 #태그 [★][📝][MD]        │
├─ 📊 미니 통계 ──────────────────────────────────┤
└─ [백업][복원][⚙설정] [Pro 업그레이드] ──────────────┘
```

---

## Options UI 구조

```
최대 640px, 중앙 정렬

┌─ 일반 설정 ─────────────────────────────────────┐
│  언어 [한국어▼]  테마 [☀라이트][🌙다크][💻시스템]   │
│  ─────────────────────────────────────────────  │
│  토스트 [ON/OFF]  잡담필터 [ON/OFF]  단축키 [변경]  │
├─ 잡담 키워드 관리 ──────────────────────────────┤
├─ 데이터 관리 (진행바 + 백업/복원) ──────────────────┤
├─ Pro 구독 ────────────────────────────────────┤
└─ Nugget v1.1.0 ───────────────────────────────┘
```

---

## ExtensionPay 연동

```js
// background.js 최상단
importScripts('src/lib/ExtPay.js');
const extpay = ExtPay('nugget-ai-chat-memory');
extpay.startBackground();

// 콜백 내부에서는 재선언 필수 (MV3 컨텍스트 손실)
const extpay = ExtPay('nugget-ai-chat-memory'); // startBackground() 재호출 금지
```

---

## manifest.json 핵심

```json
{
  "manifest_version": 3,
  "version": "1.1.0",
  "permissions": ["storage", "unlimitedStorage", "activeTab", "alarms"],
  "background": { "service_worker": "src/background/background.js" },
  "content_scripts": [
    { "matches": ["AI 3사이트"], "js": ["interceptor.js"], "run_at": "document_start", "world": "MAIN" },
    { "matches": ["AI 3사이트"], "js": ["bridge.js"], "run_at": "document_start" },
    { "matches": ["claude.ai/*"], "js": ["types.js", "selectors.js", "claude.js"], "run_at": "document_idle" },
    // chatgpt, gemini도 동일 패턴
    { "matches": ["extensionpay.com/*"], "js": ["ExtPay.js", "extpay-content.js"] }
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'; connect-src 'self' https://extensionpay.com"
  }
}
```

---

## 주요 상수

```js
MAX_FREE_ENTRIES = 500
FREE_ARCHIVE_WARNING_THRESHOLD = 400
MAX_FREE_MD_COPIES_PER_MONTH = 20
MAX_FREE_NOTE_LENGTH = 200
PRO_CACHE_VALIDITY_DAYS = 7
TOAST_DURATION_MS = 1800
STREAMING_DEBOUNCE_MS = 1000
SAVE_ENTRY_DEDUP_DELAY_MS = 500
API_CAPTURE_HASH_MAX = 100
API_CAPTURE_EVENT_NAME = '__nugget_api_capture__'
REMOTE_SELECTORS_ALARM_NAME = 'fetch_remote_selectors'
```

---

## 에이전트 팀 편성 (이 프로젝트)

**풀스택 + 결제 = 8명:**
비판자(opus) → 설계자(opus) ∥ UI디자이너(opus) → Backend(sonnet) ∥ Frontend(sonnet) → QA(opus) + 보안(opus) → DevOps(haiku)

---

## AC 체크리스트 요약

| 영역 | AC 수 | 핵심 |
|------|-------|------|
| 자동 저장 | 4 | MutationObserver + fetch 가로채기 이중 경로 |
| 잡담 필터 | 3 | 2단계(길이+키워드) OR, isJunk 마킹 |
| 자동 태깅 | 2 | 키워드 매칭, 커스텀 태그 Pro 전용 |
| 검색 & 필터 | 2 | 전문 검색, 키워드 하이라이팅 |
| MD 복사 | 2 | 코드블록 유지, 무료 월 20회 |
| 메모 | 2 | blur 저장, 무료 200자 |
| 별표 | 1 | Ctrl+Shift+S 단축키 |
| 백업/복원 | 2 | JSON 병합, 한도 초과분 자동 archived |
| 토스트 | 1 | 우측 하단 1.5초 |
| Today's Nugget | 1 | 과거의 오늘 우선, 랜덤 |
| 온보딩 | 1 | 설치 시 자동 열림 |
| Pro/결제 | 5 | ExtensionPay, 아카이브 정책, 오프라인 캐시 |
| UI | 1 | 와이어프레임 준수 |
| 데이터 구조 | 2 | 엔트리 + 설정 필드 |
| 기타(MV3) | 3 | storage 필수, 인라인 금지, CSP |
| **v1.1** API 가로채기 | 5 | fetch 오버라이드, SSE 파서, 폴백, 중복 방지 |
| **v1.1** 원격 셀렉터 | 4 | GitHub JSON, 24시간, 캐시, 우선 적용 |
| **v1.1** i18n | 5 | ko/en, auto 감지, 즉시 반영 |
| **v1.1** 다크모드 | 6 | CSS 변수, system 실시간 감지 |
| **v1.1** 마이그레이션 | 1 | 기존 설정 보존 + 새 필드 기본값 |

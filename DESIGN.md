# DESIGN.md — Nugget: AI Chat Memory (Chrome Extension)

설계일: 2026-02-18 (v1.0) / 2026-02-18 (v1.1 업데이트)
설계자: 기술 아키텍트
참조: `.plan.md`, `.plan.v1.1.md`, `reports/oracle_report.md`, `reports/critique_report.md`, `reports/critique_v1.1_report.md`

---

## 1. 개요

Nugget은 Claude, ChatGPT, Gemini에서의 AI 대화를 자동 저장하고, 잡담을 필터링하며, 태그/검색/메모 기능으로 나중에 쉽게 찾을 수 있게 하는 Chrome Extension이다.

**핵심 설계 원칙:**
- 완전 로컬 저장 (서버 없음, 결제 확인만 ExtensionPay 서버 사용)
- Manifest V3 기반, Vanilla JS (번들러 없음)
- 단순함 우선 — 요구사항에 없는 복잡성을 추가하지 않음

---

## 2. 디렉토리 구조

```
nugget/
├── manifest.json
├── src/
│   ├── background/
│   │   └── background.js          # Service Worker (메시지 허브, 저장, ExtensionPay)
│   ├── content/
│   │   ├── interceptor.js          # [v1.1] MAIN world fetch 오버라이드 (API 가로채기)
│   │   ├── bridge.js               # [v1.1] ISOLATED world 브릿지 (CustomEvent → sendMessage)
│   │   ├── claude.js               # claude.ai 전용 Content Script (DOM 셀렉터 폴백)
│   │   ├── chatgpt.js              # chatgpt.com / chat.openai.com 전용 Content Script (DOM 셀렉터 폴백)
│   │   ├── gemini.js               # gemini.google.com 전용 Content Script (DOM 셀렉터 폴백)
│   │   └── extpay-content.js       # ExtensionPay 결제 콜백용 Content Script
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── popup.css
│   ├── options/
│   │   ├── options.html
│   │   ├── options.js
│   │   └── options.css
│   ├── onboarding/
│   │   ├── onboarding.html
│   │   ├── onboarding.js
│   │   └── onboarding.css
│   ├── config/
│   │   └── selectors.js            # 플랫폼별 DOM 셀렉터 (핫패치 가능)
│   ├── shared/
│   │   ├── types.js                # JSDoc 타입 정의 (공유 계약)
│   │   ├── constants.js            # 상수 (Extension ID, 한도값 등)
│   │   └── utils.js                # 공유 유틸리티 (해싱, 언어 판별, 필터 등)
│   ├── utils/                       # [v1.1] 유틸리티 (Backend 소유)
│   │   ├── i18n.js                  # [v1.1] 자체 i18n 시스템
│   │   └── theme.js                 # [v1.1] 테마 관리
│   ├── i18n/                        # [v1.1] 번역 파일 (Frontend 소유)
│   │   ├── ko.json                  # [v1.1] 한국어 번역
│   │   └── en.json                  # [v1.1] 영어 번역
│   └── lib/
│       └── ExtPay.js               # ExtensionPay 라이브러리 (npm extpay v3.1.2에서 복사)
├── assets/
│   ├── icon-16.png
│   ├── icon-32.png
│   ├── icon-48.png
│   └── icon-128.png
└── _locales/                        # manifest default_locale 용도 (런타임 i18n은 src/utils/i18n.js 사용)
```

**결정 이유:**
- Content Script를 플랫폼별로 분리한 이유: 각 AI 사이트의 DOM 구조가 완전히 다르므로 하나의 파일에 합치면 유지보수가 어려움. 셀렉터 실패 시 해당 사이트만 수정하면 됨.
- `src/config/selectors.js` 분리: AC-2 요구사항. DOM 구조 변경 시 이 파일만 수정하면 핫패치 가능 (Pre-mortem 1번 대응).
- `src/lib/ExtPay.js`: 번들러 없이 직접 파일 복사 방식 사용. npm에서 `extpay@3.1.2`의 `dist/ExtPay.js`를 복사.
- `extpay-content.js`: ExtensionPay의 `onPaid` 콜백을 받기 위해 `extensionpay.com`에 주입되는 Content Script (oracle_report.md 참조).
- **[v1.1]** `interceptor.js` + `bridge.js` 분리: MAIN world와 ISOLATED world는 별도 실행 컨텍스트이므로 파일을 분리해야 함. interceptor는 MAIN world에서 fetch를 패치하고, bridge는 ISOLATED world에서 chrome.runtime API에 접근하여 Background로 전달.
- **[v1.1]** `src/utils/` vs `src/shared/`: CLAUDE.md 규칙상 `src/shared/`는 설계자만 수정 가능. i18n.js와 theme.js는 Backend가 구현해야 하므로 `src/utils/`에 배치 (비판자 MINOR-9 반영).
- **[v1.1]** `src/i18n/`: 번역 JSON 파일. Chrome의 `chrome.i18n.getMessage()`는 런타임 언어 변경이 불가하므로, 자체 i18n 시스템에서 이 JSON을 직접 로드하여 사용.

---

## 3. manifest.json 설계

> **v1.1 변경사항:** `"alarms"` 권한 추가, MAIN world `interceptor.js`와 ISOLATED world `bridge.js` content_scripts 항목 추가, 버전 `1.1.0`으로 변경.

```json
{
  "manifest_version": 3,
  "name": "Nugget – AI Chat Memory",
  "version": "1.1.0",
  "description": "AI 대화를 자동 저장하고 나중에 쉽게 찾으세요",
  "permissions": [
    "storage",
    "unlimitedStorage",
    "activeTab",
    "alarms"
  ],
  "commands": {
    "toggle-star": {
      "suggested_key": {
        "default": "Ctrl+Shift+S",
        "mac": "Command+Shift+S"
      },
      "description": "가장 최근 엔트리에 별표 토글"
    }
  },
  "background": {
    "service_worker": "src/background/background.js"
  },
  "action": {
    "default_popup": "src/popup/popup.html",
    "default_icon": {
      "16": "assets/icon-16.png",
      "32": "assets/icon-32.png",
      "48": "assets/icon-48.png",
      "128": "assets/icon-128.png"
    }
  },
  "icons": {
    "16": "assets/icon-16.png",
    "48": "assets/icon-48.png",
    "128": "assets/icon-128.png"
  },
  "options_page": "src/options/options.html",
  "content_scripts": [
    {
      "matches": ["https://claude.ai/*", "https://chatgpt.com/*", "https://chat.openai.com/*", "https://gemini.google.com/*"],
      "js": ["src/content/interceptor.js"],
      "run_at": "document_start",
      "world": "MAIN"
    },
    {
      "matches": ["https://claude.ai/*", "https://chatgpt.com/*", "https://chat.openai.com/*", "https://gemini.google.com/*"],
      "js": ["src/content/bridge.js"],
      "run_at": "document_start"
    },
    {
      "matches": ["https://claude.ai/*"],
      "js": ["src/shared/types.js", "src/config/selectors.js", "src/content/claude.js"],
      "run_at": "document_idle"
    },
    {
      "matches": ["https://chatgpt.com/*", "https://chat.openai.com/*"],
      "js": ["src/shared/types.js", "src/config/selectors.js", "src/content/chatgpt.js"],
      "run_at": "document_idle"
    },
    {
      "matches": ["https://gemini.google.com/*"],
      "js": ["src/shared/types.js", "src/config/selectors.js", "src/content/gemini.js"],
      "run_at": "document_idle"
    },
    {
      "matches": ["https://extensionpay.com/*"],
      "js": ["src/lib/ExtPay.js", "src/content/extpay-content.js"],
      "run_at": "document_start"
    }
  ],
  "content_security_policy": {
    "extension_pages": "script-src 'self'; object-src 'self'; connect-src 'self' https://extensionpay.com"
  }
}
```

**결정 이유:**
- `unlimitedStorage`: chrome.storage.local 기본 10MB 한도 초과 대비 (Pre-mortem 2번, AC-26).
- `activeTab`: 현재 탭 URL 추출용.
- **[v1.1]** `alarms`: 원격 셀렉터 24시간 주기 fetch용 `chrome.alarms` API 권한 (AC-V11-6).
- Content Scripts에 `types.js`와 `selectors.js`를 주입: Content Script에서 타입 상수와 셀렉터에 접근 가능하게 함.
- `run_at: "document_idle"`: AI 사이트가 렌더링 완료된 후 스크립트 실행.
- `run_at: "document_start"` (ExtensionPay): oracle_report.md에서 요구하는 설정 그대로.
- CSP에 `connect-src https://extensionpay.com`: AC-30 요구사항.
- **[v1.1]** `interceptor.js` (`world: "MAIN"`, `run_at: "document_start"`): 페이지의 첫 fetch 호출 전에 오버라이드를 완료하기 위해 `document_start`에서 MAIN world로 주입 (AC-V11-3). 3개 AI 사이트 모두에 동일한 interceptor를 주입하고, 내부에서 URL 패턴으로 플랫폼을 판별한다.
- **[v1.1]** `bridge.js` (기본 ISOLATED world, `run_at: "document_start"`): interceptor.js가 발생시키는 CustomEvent를 수신하여 `chrome.runtime.sendMessage`로 Background에 전달. `document_start`에서 실행해야 interceptor보다 먼저 이벤트 리스너를 등록할 수 있다. ISOLATED world이므로 `chrome.runtime` API 접근 가능.
- **[v1.1]** 기존 ISOLATED world content_scripts(claude.js, chatgpt.js, gemini.js)는 그대로 유지. DOM 셀렉터 폴백 전용 (비판자 MINOR-1, MINOR-8 반영).

---

## 4. 메시징 아키텍처

Content Script와 Background(Service Worker) 사이의 모든 통신은 `chrome.runtime.sendMessage`를 사용한다.
Popup/Options/Onboarding과 Background 사이도 동일하다.

### 4.1 메시지 흐름도

> **v1.1 업데이트:** API 가로채기 경로 추가. interceptor.js는 MAIN world에서 CustomEvent로 bridge.js에 전달하고, bridge.js가 `chrome.runtime.sendMessage`로 Background에 전달한다.

```
[interceptor.js]  --CustomEvent-->  [bridge.js]  --sendMessage-->  [Background Service Worker]
  (MAIN world)                     (ISOLATED)        |                  (background.js)
                                                     |                       |
[Content Script]  --sendMessage--> (DOM 셀렉터 폴백)--+   <--sendMessage--  [Popup / Options / Onboarding]
   (claude.js)                                                               (popup.js / options.js)
   (chatgpt.js)                                                               |
   (gemini.js)                                                          chrome.storage.local
```

### 4.2 메시지 타입 정의

모든 메시지는 `{ type: string, payload: object }` 형식을 따른다.

| 방향 | type | payload | 응답 | 설명 |
|------|------|---------|------|------|
| Content -> BG | `SAVE_ENTRY` | `{ question, answer, platform, sourceUrl }` | `{ success, entry?, error? }` | 대화 감지 후 저장 요청 |
| Content -> BG | `SELECTOR_FAILED` | `{ platform, selector, error }` | `{ success }` | 셀렉터 작동 실패 알림 (AC-3) |
| **[v1.1]** bridge -> BG | `API_CAPTURE` | `{ platform, question, answer, sourceUrl }` | `{ success, entry?, error? }` | API 가로채기로 캡처한 대화 저장 (AC-V11-2) |
| Popup -> BG | `GET_ENTRIES` | `{ filters? }` | `{ entries[] }` | 엔트리 목록 조회 (필터 포함) |
| Popup -> BG | `SEARCH_ENTRIES` | `{ query, filters? }` | `{ entries[] }` | 키워드 검색 |
| Popup -> BG | `TOGGLE_STAR` | `{ entryId }` | `{ success, starred }` | 별표 토글 |
| Popup -> BG | `UPDATE_NOTE` | `{ entryId, note }` | `{ success }` | 메모 저장 (AC-14) |
| Popup -> BG | `COPY_MARKDOWN` | `{ entryId }` | `{ success, markdown?, limitReached? }` | MD 복사 (카운트 체크 포함, AC-13) |
| Popup -> BG | `GET_TODAYS_NUGGET` | `{}` | `{ entry? }` | 오늘의 너겟 조회 (AC-20) |
| Popup -> BG | `DISMISS_TODAYS_NUGGET` | `{}` | `{ success }` | 오늘의 너겟 닫기 |
| Popup/Options -> BG | `GET_SETTINGS` | `{}` | `{ settings }` | 설정 조회 |
| Popup/Options -> BG | `UPDATE_SETTINGS` | `{ key, value }` | `{ success }` | 설정 변경 |
| Options -> BG | `GET_JUNK_KEYWORDS` | `{}` | `{ keywords[] }` | 잡담 키워드 목록 조회 |
| Options -> BG | `UPDATE_JUNK_KEYWORDS` | `{ keywords[] }` | `{ success }` | 잡담 키워드 수정 (AC-6) |
| Options -> BG | `EXPORT_JSON` | `{}` | `{ data }` | JSON 내보내기 (AC-17) |
| Options -> BG | `IMPORT_JSON` | `{ data }` | `{ success, imported, skipped }` | JSON 불러오기 — 병합 (AC-17) |
| Options -> BG | `EXPORT_MARKDOWN_FILE` | `{}` | `{ success, markdown }` | Pro 전용 MD 파일 내보내기 (AC-18) |
| Options -> BG | `EXPORT_PDF` | `{}` | `{ success }` | Pro 전용 PDF 내보내기 (AC-18) |
| Popup/Options -> BG | `GET_PRO_STATUS` | `{}` | `{ isPro, cached }` | Pro 상태 조회 |
| Popup/Options -> BG | `OPEN_PAYMENT_PAGE` | `{}` | `{ success }` | 결제 페이지 열기 (AC-22) |
| Popup -> BG | `ADD_CUSTOM_TAG` | `{ entryId, tag }` | `{ success, limitReached? }` | 커스텀 태그 추가 (Pro 전용, AC-9) |
| BG -> Content | (없음) | — | — | BG는 Content에 메시지를 보낼 필요 없음 |

**결정 이유:**
- 모든 데이터 조작은 Background(Service Worker)에서만 수행. Content Script와 Popup은 요청만 보내고 결과를 받음. 이유: MV3 Service Worker가 데이터의 단일 진입점(Single Source of Truth)이 되어야 함 (AC-28).
- `SELECTOR_FAILED`: AC-3 대응. Content Script가 DOM 셀렉터 실패를 감지하면 Background에 알리고, Background가 뱃지를 설정함.
- **[v1.1]** `API_CAPTURE`: bridge.js가 interceptor.js로부터 수신한 API 캡처 데이터를 Background에 전달. Background는 `saveEntry()`와 동일한 파이프라인(해시, 잡담필터, 태깅, 한도체크)을 수행하되, 저장 성공 시 해시를 `nugget_api_capture_hashes`에 기록하여 후속 SAVE_ENTRY 중복을 방지 (비판자 CRITICAL-5 해결).

### 4.3 토스트 알림 메커니즘

토스트는 Content Script가 아닌 **Background에서 Content Script로의 응답**으로 구현한다.
`SAVE_ENTRY` 성공 시 Content Script가 응답의 `success: true`를 받으면 자체적으로 토스트 DOM을 페이지에 주입한다.

이유: Background(Service Worker)는 DOM에 접근할 수 없으므로, Content Script가 토스트 렌더링을 담당해야 한다. 메시지 응답의 성공 여부로 토스트 표시 여부를 결정한다.

---

## 5. 스토리지 스키마

모든 데이터는 `chrome.storage.local`에 저장한다.

### 5.1 스토리지 키 목록

| 키 이름 | 타입 | 설명 |
|---------|------|------|
| `nugget_entries` | `NuggetEntry[]` | 저장된 대화 엔트리 배열 |
| `nugget_settings` | `NuggetSettings` | 사용자 설정 객체 |
| `nugget_junk_keywords` | `string[]` | 잡담 필터 키워드 목록 |
| `nugget_pro_cache` | `ProStatusCache` | ExtensionPay Pro 상태 캐시 |
| `nugget_todays_nugget_dismissed` | `string` | 오늘의 너겟 닫기 날짜 (ISO date string, 예: "2026-02-18") |
| `nugget_custom_tags` | `string[]` | 사용자 커스텀 태그 목록 (Pro 전용) |
| **[v1.1]** `nugget_remote_selectors` | `RemoteSelectorsCache` | 원격 셀렉터 캐시 (AC-V11-7) |
| **[v1.1]** `nugget_api_capture_hashes` | `string[]` | API 캡처로 저장된 엔트리 해시 목록 — 중복 저장 방지용 (AC-V11-4a) |

### 5.2 NuggetEntry 스키마

```js
{
  id: string,            // crypto.randomUUID() 또는 타임스탬프+랜덤 조합
  date: string,          // ISO 8601 (예: "2026-02-18T14:30:00.000Z")
  platform: string,      // "claude" | "chatgpt" | "gemini"
  question: string,      // 사용자 질문 원문
  answer: string,        // AI 답변 원문
  tags: string[],        // 자동 태깅 결과 (예: ["코딩", "학습"])
  starred: boolean,      // 별표 여부 (기본: false)
  isJunk: boolean,       // 잡담 여부 (기본: false)
  archived: boolean,     // 아카이브 여부 — 무료 한도 초과 시 (기본: false)
  sourceUrl: string,     // 대화가 발생한 페이지 URL
  note: string,          // 사용자 메모 (기본: "")
  hash: string           // 중복 방지용 해시 (question + answer + date 조합)
}
```

**결정 이유:**
- AC-26 필드 그대로 반영. `hash` 필드 추가: AC-4 중복 방지를 위해 질문+답변+시간 조합 해시를 저장.
- `archived` 필드: AC-23의 아카이브 정책. 삭제하지 않고 숨기기 위한 플래그.
- `date`를 ISO 8601 string으로 저장: JSON 직렬화 호환성. Date 객체는 chrome.storage에 저장 불가.

### 5.3 NuggetSettings 스키마

```js
{
  toastEnabled: boolean,      // 토스트 알림 on/off (기본: true)
  junkFilterEnabled: boolean, // 잡담 필터 on/off (기본: true)
  shortcutKey: string,        // 단축키 (기본: "Ctrl+Shift+S") — 읽기 전용 표시용
  maxFreeEntries: number,     // 무료 한도 (기본: 500) — 상수
  isPro: boolean,             // Pro 여부 (로컬 캐시, 기본: false)
  mdCopyCount: number,        // 이번 달 MD 복사 횟수 (기본: 0)
  mdCopyResetDate: string,    // MD 복사 카운터 리셋 날짜 (ISO date, 매월 1일 0시 UTC, AC-23)
  language: string,           // [v1.1] UI 언어 ('ko' | 'en' | 'auto') (기본: 'auto') (AC-V11-13)
  theme: string               // [v1.1] 테마 ('light' | 'dark' | 'system') (기본: 'system') (AC-V11-17)
}
```

> **[v1.1] 마이그레이션 (AC-V11-21):** v1.0 사용자가 v1.1로 업데이트하면 기존 `nugget_settings`에 `language`, `theme` 필드가 없다. `loadSettings()`의 `Object.assign({}, defaultSettings(), stored)` 병합 로직에 의해 새 필드가 기본값(`language: 'auto'`, `theme: 'system'`)으로 자동 추가된다. `defaultSettings()` 함수에 이 두 필드를 반드시 포함해야 한다.

> **[v1.1] `language: 'auto'` 동작 (AC-V11-13, 비판자 MINOR-5 해결):** 'auto'일 때 `navigator.language`를 확인하여, 'ko'로 시작하면 `'ko'`, 'en'으로 시작하면 `'en'`, 그 외 미지원 언어이면 `'ko'` 폴백.

### 5.4 ProStatusCache 스키마

```js
{
  paid: boolean,        // ExtensionPay getUser().paid 결과
  checkedAt: string     // 마지막 확인 시각 (ISO 8601)
}
```

**결정 이유 (AC-24a 반영):**
- `checkedAt`으로부터 7일 이내이면 캐시된 `paid` 값을 사용.
- 7일 초과 + 오프라인이면 Pro 기능 유지 + "구독 확인 필요" 배너 표시.
- 온라인 상태에서는 매번 `getUser()`를 호출하여 캐시 갱신.

### 5.5 기본 잡담 키워드 목록

`nugget_junk_keywords` 초기값:

```js
[
  "안녕", "고마워", "감사", "ㅋㅋ", "ㅎㅎ", "ㅠㅠ", "오케이", "ㅇㅋ", "굿",
  "hi", "hello", "thanks", "thank you", "ok", "okay", "bye", "lol", "haha",
  "good", "nice", "cool", "yes", "no", "sure", "yep", "nope"
]
```

**결정 이유:** AC-6 기본 키워드 내장 요구사항. 한/영 공통 잡담 패턴. Options에서 사용자가 추가/삭제 가능.

---

## 6. 핵심 로직 설계

### 6.1 대화 감지 (Content Script)

각 Content Script(`claude.js`, `chatgpt.js`, `gemini.js`)는 동일한 패턴을 따른다:

1. **MutationObserver 등록**: `selectors.js`에서 플랫폼별 셀렉터를 가져와 대화 영역을 감시.
2. **스트리밍 완료 감지**: 답변 DOM의 변화가 멈추면(debounce 1초) 스트리밍 완료로 판단.
3. **질문+답변 추출**: 마지막 질문-답변 쌍을 셀렉터로 추출.
4. **Background에 전송**: `SAVE_ENTRY` 메시지로 전송.
5. **응답 처리**: 성공 시 토스트 표시, 실패 시 무시.

**셀렉터 실패 처리 (AC-3):**
- `try-catch`로 셀렉터 접근을 감싸고, 실패 시 `SELECTOR_FAILED` 메시지를 Background에 전송.
- Background는 `chrome.action.setBadgeText({ text: "!" })`로 뱃지 설정.

### 6.2 잡담 필터 (Background — utils.js)

AC-5의 2단계 필터를 `src/shared/utils.js`에 구현:

```
함수: classifyJunk(question, answer, keywords)

1단계 — 길이 기준:
  - isCJK(question) → question.length < 15 AND answer.length < 200 → isJunk 후보
  - !isCJK(question) → wordCount(question) < 5 AND answer.length < 200 → isJunk 후보
  - 1단계 통과 못하면 → isJunk: false (종료)

2단계 — 키워드 매칭:
  - question.trim().toLowerCase()가 keywords 배열의 어떤 항목과 exact match → isJunk: true
  - 매칭 없으면 → isJunk: false

언어 판별:
  - isCJK(text): 텍스트에 U+3000~U+9FFF 또는 U+AC00~U+D7AF 범위 문자가 1개 이상 있으면 true
```

**결정 이유:** AC-5의 정확한 사양을 그대로 구현. 1단계(길이)는 AND 조건이므로 둘 다 충족해야 함. 2단계는 1단계를 통과한 것에 대해서만 적용하는 것이 아니라, 독립적으로 적용한다. 즉 질문이 길더라도 키워드 exact match이면 잡담 처리된다.

> 수정: AC-5를 다시 읽으면 "1단계: ... → isJunk:true. 2단계: ... → isJunk:true"로 되어 있다. 즉 1단계와 2단계는 OR 관계이다. 어느 하나라도 통과하면 isJunk:true.

### 6.3 자동 태깅 (Background — utils.js)

AC-8의 키워드 매칭 기반 태깅을 `src/shared/utils.js`에 구현:

```
함수: autoTag(question, answer)

태그 매핑:
  "코딩"       → ["code", "코드", "function", "함수", "bug", "버그", "error", "에러", "api", "python", "javascript", "html", "css", "react", "프로그래밍", "개발", "배열", "변수", "알고리즘", "데이터베이스", "sql", "git"]
  "글쓰기"     → ["글", "write", "writing", "에세이", "essay", "블로그", "blog", "소설", "시", "poem", "번역", "translate", "문법", "grammar", "작문", "요약", "summary"]
  "업무"       → ["이메일", "email", "보고서", "report", "회의", "meeting", "일정", "schedule", "기획", "proposal", "업무", "work", "프레젠테이션", "ppt", "엑셀", "excel"]
  "학습"       → ["설명", "explain", "뜻", "meaning", "차이", "difference", "배우", "learn", "공부", "study", "개념", "concept", "이론", "theory", "강의", "tutorial", "원리"]
  "크리에이티브" → ["아이디어", "idea", "디자인", "design", "이미지", "image", "그림", "로고", "logo", "브레인스토밍", "brainstorm", "창작", "creative", "영감"]

로직:
  combined = (question + " " + answer).toLowerCase()
  각 태그의 키워드를 combined에서 검색 (단어 경계 무관, 부분 문자열 포함)
  매칭된 태그 모두 추가. 아무것도 매칭 안 되면 ["기타"]
```

### 6.4 중복 방지 (AC-4)

```
함수: generateHash(question, answer, dateString)

로직:
  input = question.trim() + "|" + answer.trim().substring(0, 200) + "|" + dateString
  hash = 간단한 문자열 해시 (djb2 또는 유사)
  저장 전 기존 entries에서 동일 hash 존재 여부 확인 → 존재하면 저장 스킵
```

**결정 이유:** answer 전체 대신 앞 200자만 해시에 포함 — 긴 답변의 해싱 비용 절감. 날짜를 포함하여 같은 질문-답변이라도 다른 시점이면 별도 엔트리.

### 6.5 MD 복사 한도 관리 (AC-13, AC-23)

```
함수: checkAndIncrementMdCopy(settings)

로직:
  현재 날짜(UTC)와 settings.mdCopyResetDate 비교
  새 달이면 → mdCopyCount = 0, mdCopyResetDate = 이번 달 1일로 갱신
  isPro이면 → 무조건 허용
  mdCopyCount >= 20이면 → { limitReached: true }
  아니면 → mdCopyCount++ 후 저장, { limitReached: false }
```

### 6.6 무료 한도 & 아카이브 (AC-23, AC-23a)

```
함수: enforceFreeLimits(entries, isPro)

로직:
  isPro이면 → 모든 entries의 archived = false로 해제, 리턴
  activeEntries = entries.filter(e => !e.archived && !e.isJunk)
  activeEntries를 date 내림차순 정렬
  activeEntries 500개 초과 시 → 오래된 것부터 archived = true

함수: onRestore(importedEntries, existingEntries, isPro) — AC-23a
  병합: id 기준 중복 제거, 새 엔트리 추가
  병합 후 enforceFreeLimits() 호출
```

### 6.7 Pro 상태 관리 (AC-22, AC-24a)

```
함수: checkProStatus()

로직:
  1. nugget_pro_cache 로드
  2. cache가 있고, checkedAt이 7일 이내이면:
     - isPro = cache.paid
     - 온라인이면 백그라운드에서 getUser() 호출하여 캐시 갱신 (비동기, 결과 기다리지 않음)
     - 리턴 { isPro, cached: true }
  3. cache가 없거나 7일 초과:
     - getUser() 호출 시도
     - 성공 → cache 갱신, { isPro: user.paid, cached: false }
     - 실패(오프라인) + cache 있음 → { isPro: cache.paid, cached: true, expired: true }
       (expired: true이면 UI에서 "구독 확인 필요" 배너 표시)
     - 실패(오프라인) + cache 없음 → { isPro: false, cached: false }
```

### 6.8 별표 단축키 (AC-16)

Background에서 `chrome.commands.onCommand` 리스너 등록:
```
"toggle-star" 커맨드 수신 시:
  → entries 중 date가 가장 최근인 엔트리의 starred 토글
  → chrome.storage.local에 저장
  → 활성 탭에 토스트 메시지 전송 (tabs.sendMessage)
```

**특이사항:** 단축키는 Background에서 처리하므로, Popup이 열려있지 않아도 동작한다. 토스트 피드백은 현재 활성 탭의 Content Script가 있을 때만 표시된다.

### 6.9 Today's Nugget (AC-20)

```
함수: getTodaysNugget(entries, dismissedDate)

로직:
  오늘 날짜 = new Date().toISOString().slice(0, 10)
  dismissedDate === 오늘 → null (이미 닫음)

  과거의_오늘 = entries.filter(e => e.date.slice(5, 10) === 오늘.slice(5, 10) AND e.date.slice(0, 4) !== 올해)
  과거의_오늘이 있으면 → 랜덤 1개 리턴
  없으면 → entries 중 랜덤 1개 리턴 (isJunk, archived 제외)
```

### 6.10 백업 알림 (AC-18)

Background에서 엔트리 저장 시마다 확인:
```
activeCount = entries.filter(e => !e.archived).length

무료 사용자:
  activeCount >= 400 (80%) → chrome.action.setBadgeText({ text: "!" }), 뱃지 색상 노란색
  activeCount >= 500 → "한도 도달" 안내 (Popup에서 표시)

Pro 사용자:
  activeCount가 500의 배수 도달 → 마일스톤 알림
```

---

## 7. ExtensionPay 연동 상세

### 7.1 Background 초기화

```js
// background.js 최상단
importScripts('src/lib/ExtPay.js');

const extpay = ExtPay('nugget-ai-chat-memory');  // Extension ID — 통합 계약 참조
extpay.startBackground();
```

### 7.2 MV3 콜백 내 재선언 (oracle_report.md 제약사항)

Service Worker 콜백(chrome.storage, chrome.runtime.onMessage 등) 내부에서 ExtPay를 사용할 때는 반드시 재선언:

```js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_PRO_STATUS') {
    const extpay = ExtPay('nugget-ai-chat-memory');  // 재선언 필수
    extpay.getUser()
      .then(user => { /* ... */ })
      .catch(err => { /* 오프라인 처리 */ });
    return true;  // 비동기 응답
  }
});
```

**주의:** `startBackground()`는 최초 1회만 호출. 재선언 시에는 호출하지 않음.

### 7.3 결제 완료 콜백

`extpay-content.js`가 `extensionpay.com`에 주입되어 `onPaid` 콜백을 수신:

```js
// src/content/extpay-content.js
// ExtPay.js가 먼저 주입됨 (manifest.json content_scripts 참조)
const extpay = ExtPay('nugget-ai-chat-memory');
extpay.onPaid.addListener(user => {
  chrome.runtime.sendMessage({ type: 'PRO_STATUS_CHANGED', payload: { paid: true } });
});
```

Background는 `PRO_STATUS_CHANGED` 수신 시 캐시 갱신 + settings.isPro 업데이트.

---

## 8. 통합 계약

이 섹션은 2명 이상의 에이전트가 공유하는 모든 연결점을 정의한다.
**이 계약에 있는 이름은 개발자가 임의로 변경할 수 없다.**

### 8.1 파일 이름과 경로

| 파일 | 경로 | 담당 |
|------|------|------|
| manifest.json | `nugget/manifest.json` | Backend |
| Background Service Worker | `nugget/src/background/background.js` | Backend |
| Content Script (Claude) | `nugget/src/content/claude.js` | Backend |
| Content Script (ChatGPT) | `nugget/src/content/chatgpt.js` | Backend |
| Content Script (Gemini) | `nugget/src/content/gemini.js` | Backend |
| Content Script (ExtensionPay) | `nugget/src/content/extpay-content.js` | Backend |
| DOM 셀렉터 설정 | `nugget/src/config/selectors.js` | Backend |
| ExtensionPay 라이브러리 | `nugget/src/lib/ExtPay.js` | Backend (파일 복사) |
| 공유 타입 정의 | `nugget/src/shared/types.js` | Architect (읽기 전용) |
| 공유 상수 | `nugget/src/shared/constants.js` | Architect (읽기 전용) |
| 공유 유틸리티 | `nugget/src/shared/utils.js` | Backend |
| Popup HTML | `nugget/src/popup/popup.html` | Frontend |
| Popup JS | `nugget/src/popup/popup.js` | Frontend |
| Popup CSS | `nugget/src/popup/popup.css` | Frontend |
| Options HTML | `nugget/src/options/options.html` | Frontend |
| Options JS | `nugget/src/options/options.js` | Frontend |
| Options CSS | `nugget/src/options/options.css` | Frontend |
| Onboarding HTML | `nugget/src/onboarding/onboarding.html` | Frontend |
| Onboarding JS | `nugget/src/onboarding/onboarding.js` | Frontend |
| Onboarding CSS | `nugget/src/onboarding/onboarding.css` | Frontend |
| 아이콘 | `nugget/assets/icon-{16,32,48,128}.png` | Frontend |

### 8.2 Chrome 메시지 타입

모든 메시지는 `{ type: string, payload: object }` 형식이다.

```js
// Content Script → Background
'SAVE_ENTRY'            // { question, answer, platform, sourceUrl }
'SELECTOR_FAILED'       // { platform, selector, error }

// Popup → Background
'GET_ENTRIES'           // { filters? }
'SEARCH_ENTRIES'        // { query, filters? }
'TOGGLE_STAR'           // { entryId }
'UPDATE_NOTE'           // { entryId, note }
'COPY_MARKDOWN'         // { entryId }
'GET_TODAYS_NUGGET'     // {}
'DISMISS_TODAYS_NUGGET' // {}
'ADD_CUSTOM_TAG'        // { entryId, tag }

// Popup/Options → Background
'GET_SETTINGS'          // {}
'UPDATE_SETTINGS'       // { key, value }
'GET_PRO_STATUS'        // {}
'OPEN_PAYMENT_PAGE'     // {}

// Options → Background
'GET_JUNK_KEYWORDS'     // {}
'UPDATE_JUNK_KEYWORDS'  // { keywords[] }
'EXPORT_JSON'           // {}
'IMPORT_JSON'           // { data }
'EXPORT_MARKDOWN_FILE'  // {}
'EXPORT_PDF'            // {}

// ExtensionPay Content Script → Background
'PRO_STATUS_CHANGED'    // { paid }

// Background → Content Script (tabs.sendMessage)
'SHOW_TOAST'            // { message }
```

### 8.3 Storage 키 이름

```js
'nugget_entries'                  // NuggetEntry[]
'nugget_settings'                 // NuggetSettings
'nugget_junk_keywords'            // string[]
'nugget_pro_cache'                // ProStatusCache
'nugget_todays_nugget_dismissed'  // string (ISO date)
'nugget_custom_tags'              // string[]
```

### 8.4 환경 변수 / 상수

```js
// src/shared/constants.js에 정의
const NUGGET_EXTENSION_ID = 'nugget-ai-chat-memory';  // ExtensionPay 등록 시 실제 ID로 교체
const MAX_FREE_ENTRIES = 500;
const FREE_ARCHIVE_WARNING_THRESHOLD = 400;  // 80%
const MAX_FREE_MD_COPIES_PER_MONTH = 20;
const MAX_FREE_NOTE_LENGTH = 200;
const PRO_CACHE_VALIDITY_DAYS = 7;
const TOAST_DURATION_MS = 1800;  // 1.5~2초 사이
const STREAMING_DEBOUNCE_MS = 1000;  // 스트리밍 완료 판단 debounce
const DEFAULT_TAGS = ['코딩', '글쓰기', '업무', '학습', '크리에이티브', '기타'];

// 플랫폼 식별자
const PLATFORM_CLAUDE = 'claude';
const PLATFORM_CHATGPT = 'chatgpt';
const PLATFORM_GEMINI = 'gemini';
```

---

## 9. 시그니처 사양

주요 모듈의 public 함수/클래스 시그니처를 정의한다.

### 9.1 src/shared/utils.js

```js
/**
 * CJK 문자 포함 여부 판별
 * @param {string} text
 * @returns {boolean}
 */
function isCJK(text) {}

/**
 * 잡담 여부 분류 (AC-5)
 * @param {string} question
 * @param {string} answer
 * @param {string[]} keywords - 잡담 키워드 목록
 * @returns {boolean} isJunk
 */
function classifyJunk(question, answer, keywords) {}

/**
 * 자동 태깅 (AC-8)
 * @param {string} question
 * @param {string} answer
 * @returns {string[]} tags - 매칭된 태그 배열
 */
function autoTag(question, answer) {}

/**
 * 중복 방지 해시 생성 (AC-4)
 * @param {string} question
 * @param {string} answer
 * @param {string} dateString - ISO 8601
 * @returns {string} hash
 */
function generateHash(question, answer, dateString) {}

/**
 * 마크다운 형식으로 엔트리 변환 (AC-12)
 * @param {NuggetEntry} entry
 * @returns {string} markdown
 */
function entryToMarkdown(entry) {}

/**
 * 검색 키워드 하이라이팅용 정규식 생성 (AC-11)
 * @param {string} query
 * @returns {RegExp}
 */
function buildHighlightRegex(query) {}
```

### 9.2 src/background/background.js

```js
/**
 * 엔트리 저장 (중복 체크 + 잡담 필터 + 태깅 + 한도 체크)
 * @param {{ question: string, answer: string, platform: string, sourceUrl: string }} data
 * @returns {Promise<{ success: boolean, entry?: NuggetEntry, error?: string }>}
 */
async function saveEntry(data) {}

/**
 * 엔트리 검색 (키워드 + 필터)
 * @param {string} query
 * @param {SearchFilters} [filters]
 * @returns {Promise<NuggetEntry[]>}
 */
async function searchEntries(query, filters) {}

/**
 * 엔트리 목록 조회 (필터 적용)
 * @param {SearchFilters} [filters]
 * @returns {Promise<NuggetEntry[]>}
 */
async function getEntries(filters) {}

/**
 * 별표 토글
 * @param {string} entryId
 * @returns {Promise<{ success: boolean, starred: boolean }>}
 */
async function toggleStar(entryId) {}

/**
 * 메모 업데이트 (AC-14, AC-15)
 * @param {string} entryId
 * @param {string} note
 * @returns {Promise<{ success: boolean, error?: string }>}
 */
async function updateNote(entryId, note) {}

/**
 * MD 복사 처리 — 한도 체크 후 마크다운 반환 (AC-13)
 * @param {string} entryId
 * @returns {Promise<{ success: boolean, markdown?: string, limitReached?: boolean }>}
 */
async function copyMarkdown(entryId) {}

/**
 * Pro 상태 확인 (캐시 + ExtensionPay, AC-24a)
 * @returns {Promise<{ isPro: boolean, cached: boolean, expired?: boolean }>}
 */
async function checkProStatus() {}

/**
 * 무료 한도 적용 — 아카이브 처리 (AC-23)
 * @param {NuggetEntry[]} entries
 * @param {boolean} isPro
 * @returns {NuggetEntry[]}
 */
function enforceFreeLimits(entries, isPro) {}

/**
 * JSON 내보내기 (AC-17)
 * @returns {Promise<{ entries: NuggetEntry[], settings: NuggetSettings, exportDate: string }>}
 */
async function exportJSON() {}

/**
 * JSON 가져오기 — 병합 (AC-17, AC-23a)
 * @param {{ entries: NuggetEntry[] }} data
 * @returns {Promise<{ success: boolean, imported: number, skipped: number }>}
 */
async function importJSON(data) {}

/**
 * 오늘의 너겟 조회 (AC-20)
 * @returns {Promise<NuggetEntry|null>}
 */
async function getTodaysNugget() {}
```

### 9.3 src/config/selectors.js

```js
/**
 * 플랫폼별 DOM 셀렉터 설정
 * 핫패치 가능: AI 사이트 DOM 변경 시 이 파일만 수정
 */
const SELECTORS = {
  claude: {
    /** 대화 컨테이너 (MutationObserver 타겟) */
    conversationContainer: 'div.font-claude-message',
    /** 사용자 질문 요소 */
    userMessage: 'div[data-is-streaming="false"] .font-user-message',
    /** AI 답변 요소 */
    assistantMessage: 'div.font-claude-message',
    /** 스트리밍 진행 중 표시자 */
    streamingIndicator: 'div[data-is-streaming="true"]'
  },
  chatgpt: {
    conversationContainer: 'main div.flex.flex-col',
    userMessage: 'div[data-message-author-role="user"]',
    assistantMessage: 'div[data-message-author-role="assistant"]',
    streamingIndicator: 'button[aria-label="Stop generating"]'
  },
  gemini: {
    conversationContainer: 'chat-window',
    userMessage: 'user-query',
    assistantMessage: 'model-response',
    streamingIndicator: '.loading-indicator'
  }
};
```

**주의:** 위 셀렉터는 초기 추정값이다. 실제 AI 사이트의 DOM 구조는 수시로 변경되므로, 개발 시점에 최신 DOM을 확인하여 업데이트해야 한다. 셀렉터 실패 시 `SELECTOR_FAILED` 메시지로 사용자에게 알림 (AC-3).

### 9.4 Content Script 공통 패턴 (claude.js / chatgpt.js / gemini.js)

각 Content Script는 동일한 구조를 따른다:

```js
/**
 * Content Script 초기화 — MutationObserver 설정 및 대화 감지 시작
 * @param {string} platform - "claude" | "chatgpt" | "gemini"
 */
function initContentScript(platform) {}

/**
 * 스트리밍 완료 감지 (debounce)
 * @param {MutationObserver} observer
 * @param {Function} onComplete - 완료 시 콜백
 */
function detectStreamingComplete(observer, onComplete) {}

/**
 * 질문+답변 쌍 추출
 * @param {string} platform
 * @returns {{ question: string, answer: string } | null}
 */
function extractQAPair(platform) {}

/**
 * 토스트 DOM 주입 및 표시 (AC-19)
 * @param {string} message
 */
function showToast(message) {}
```

---

## 10. 데이터 흐름 요약

### 10.1 대화 저장 흐름

```
사용자가 AI에게 질문
  → AI가 답변 스트리밍
  → Content Script: MutationObserver가 DOM 변화 감지
  → Content Script: debounce 1초 후 스트리밍 완료 판단
  → Content Script: 질문+답변 추출
  → Content Script: SAVE_ENTRY 메시지 전송
  → Background: 해시 생성 → 중복 체크
  → Background: 잡담 필터 적용 (isJunk 판정)
  → Background: 자동 태깅
  → Background: NuggetEntry 생성 → chrome.storage.local 저장
  → Background: 무료 한도 체크 → 필요 시 아카이브
  → Background: 응답 { success: true, entry }
  → Content Script: 토스트 표시 "Nugget이 저장했어요"
```

### 10.2 검색 흐름

```
사용자가 Popup에서 검색어 입력 + 필터 선택
  → Popup: SEARCH_ENTRIES 메시지 전송
  → Background: entries 로드 → 필터 적용 → 키워드 매칭
  → Background: 결과 반환
  → Popup: 카드 리스트 렌더링 (키워드 하이라이팅)
```

### 10.3 Pro 업그레이드 흐름

```
사용자가 "Pro로 업그레이드" 버튼 클릭
  → Popup/Options: OPEN_PAYMENT_PAGE 메시지 전송
  → Background: extpay.openPaymentPage() 호출
  → 새 탭에서 ExtensionPay 결제 페이지 열림
  → 결제 완료
  → extpay-content.js: onPaid 콜백 수신
  → extpay-content.js: PRO_STATUS_CHANGED 메시지 전송
  → Background: Pro 캐시 갱신 + settings.isPro = true
  → Background: enforceFreeLimits() 호출 → 모든 archived 해제
```

---

## 11. 설계 제약사항 (oracle_report.md 반영)

1. **ExtensionPay Extension ID 기반 인증**: API 키 불필요. `ExtPay('nugget-ai-chat-memory')`으로 초기화.
2. **MV3 Service Worker 콜백 내 ExtPay 재선언**: 콜백 내부에서 `const extpay = ExtPay('nugget-ai-chat-memory')` 재선언 필수. `startBackground()`는 재호출하지 않음.
3. **getUser() 오프라인 실패 대비**: 모든 `getUser()` 호출에 `.catch()` 필수.
4. **CSP**: `connect-src https://extensionpay.com` 추가 (AC-30).
5. **Content Script for ExtensionPay**: `extensionpay.com`에 Content Script 주입 필요 (`onPaid` 콜백용).
6. **번들러 미사용**: `dist/ExtPay.js`를 `src/lib/ExtPay.js`로 직접 복사.
7. **인라인 스크립트 금지 (AC-29)**: 모든 HTML 파일은 별도 JS 파일 참조.
8. **Service Worker 상태 금지 (AC-28)**: 메모리 변수에 상태 보관 금지. 모든 상태는 chrome.storage.local에 저장.

---

## 12. critique_report.md MINOR 사항 반영

- **MINOR-10 (archived 누적)**: 현재 버전에서는 상한선을 두지 않음. unlimitedStorage 권한으로 대응. 향후 v2에서 archived 정리 정책 고려.
- **MINOR-11 (오프라인 악용)**: AC-24a 정책 그대로 수용. 핵심 기능이 온라인 전제이므로 실질적 악용 가능성 낮음.
- **MINOR-9 (Pre-mortem 수치 불일치)**: 설계에서는 AC-24a(7일)를 정식 기준으로 채택. Pro 캐시 유효기간 = 7일.

---

## 13. [v1.1] API 가로채기 아키텍처 (AC-V11-1 ~ AC-V11-5)

### 13.1 개요

v1.0은 DOM 셀렉터(MutationObserver)로 대화를 감지했다. v1.1은 `window.fetch` 오버라이드를 통해 AI 플랫폼의 SSE 스트리밍 응답을 직접 캡처하는 방식을 **메인 캡처 경로**로 추가한다. 기존 DOM 셀렉터 방식은 **폴백**으로 유지한다.

**아키텍처 흐름:**

```
[페이지의 fetch 호출]
  → [interceptor.js (MAIN world)] window.fetch 오버라이드
    → ReadableStream.tee()로 스트림 복제
    → 복제된 스트림을 플랫폼별 SSE 파서로 파싱
    → 파싱 완료 시 CustomEvent('__nugget_api_capture__')로 데이터 전달
  → [bridge.js (ISOLATED world)] CustomEvent 리스너
    → chrome.runtime.sendMessage({ type: 'API_CAPTURE', payload })
  → [background.js] API_CAPTURE 메시지 수신
    → saveEntry() 동일 파이프라인 (해시, 잡담필터, 태깅, 한도)
    → 저장 성공 시 해시를 nugget_api_capture_hashes에 기록
    → 후속 SAVE_ENTRY가 같은 해시로 도착하면 무시 (중복 방지)
```

### 13.2 interceptor.js 상세 설계

**실행 환경:** MAIN world, `document_start`

**역할:** `window.fetch`를 오버라이드하여 AI 사이트의 SSE 스트리밍 응답을 가로챔.

**플랫폼 판별:**
```
const host = window.location.hostname;
if (host === 'claude.ai') → 'claude'
if (host === 'chatgpt.com' || host === 'chat.openai.com') → 'chatgpt'
if (host.endsWith('gemini.google.com')) → 'gemini'
```

**fetch 오버라이드 로직:**
```
1. 원본 fetch를 변수에 보관: const _originalFetch = window.fetch;
2. window.fetch를 새 함수로 교체:
   a. _originalFetch(url, options)를 호출하여 원본 Response 획득
   b. URL이 API 엔드포인트 패턴과 매칭되는지 확인
   c. 매칭되면:
      - response.body.tee()로 스트림 복제 (AC-V11-5: 원본 유지)
      - 복제된 스트림(stream2)을 플랫폼별 SSE 파서에 전달
      - 원본 스트림(stream1)으로 새 Response를 만들어 호출자에게 반환
   d. 매칭 안 되면: 원본 Response 그대로 반환
```

**API 엔드포인트 패턴:**
```js
const API_PATTERNS = {
  claude: /\/api\/.*\/completion/,         // claude.ai/api/.../completion
  chatgpt: /\/backend-api\/conversation/,  // chatgpt.com/backend-api/conversation
  gemini: /\/batchexecute\?/               // gemini.google.com/...batchexecute?...
};
```

> 이 패턴은 변경될 수 있으므로, interceptor.js 내부에 상수로 선언하여 핫패치 가능하게 한다. 향후 원격 셀렉터와 마찬가지로 원격 업데이트도 고려 가능하나 v1.1 범위에서는 로컬만.

### 13.3 플랫폼별 SSE 파서 (AC-V11-1a, 비판자 CRITICAL-1 해결)

interceptor.js 내부에 플랫폼별 파서 함수를 정의한다. 각 파서는 복제된 ReadableStream을 소비하고, 질문과 답변 텍스트를 추출한다.

**공통 시그니처:**
```js
/**
 * SSE 스트림을 파싱하여 답변 텍스트를 추출
 * @param {ReadableStream} stream - tee()로 복제된 응답 스트림
 * @param {string} requestBody - fetch 요청 body (질문 추출용)
 * @returns {Promise<{ question: string, answer: string } | null>}
 *   null 반환 시 = 파싱 실패 → DOM 셀렉터 폴백 (AC-V11-4)
 */
```

**Claude 파서 (`parseClaudeSSE`):**
```
SSE 형식: "event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}\n\n"
1. TextDecoderStream으로 스트림을 텍스트로 변환
2. 줄 단위로 파싱:
   - "event: content_block_delta" 이벤트 감지
   - 바로 다음 "data: " 줄에서 JSON 파싱 → delta.text 추출
   - 모든 delta.text를 이어붙임 → answer
3. 질문은 requestBody (JSON)에서 추출: body.prompt 또는 body.messages의 마지막 user 메시지
4. 스트림 끝까지 읽으면 { question, answer } 반환
5. 예외 또는 빈 answer → null 반환 (폴백)
```

**ChatGPT 파서 (`parseChatGPTSSE`):**
```
SSE 형식: "data: {"id":"...","message":{"content":{"parts":["..."]}}}\n\n"
1. TextDecoderStream으로 텍스트 변환
2. "data: " 접두사가 붙은 줄을 모두 수집
3. 마지막 유효한 data 줄의 JSON에서 message.content.parts[] 추출 → answer
   (ChatGPT SSE는 점진적으로 전체 텍스트를 보내므로 마지막 data의 parts가 최종 답변)
4. "data: [DONE]" 수신 시 스트림 종료
5. 질문은 requestBody에서 추출: body.messages의 마지막 user role content
6. 예외 또는 빈 answer → null 반환 (폴백)
```

**Gemini 파서 (`parseGeminiResponse`):**
```
Gemini는 표준 SSE가 아닌 JSON 배열 응답을 사용할 수 있음.
1. TextDecoderStream으로 텍스트 변환
2. 전체 응답 본문을 수집
3. JSON으로 파싱 시도 → 텍스트 청크 추출
4. 파싱 실패가 가장 빈번할 플랫폼이므로, 실패 시 조용히 null 반환 (폴백)
5. 질문은 requestBody에서 추출 시도, 실패 시 null
```

**"파싱 실패"의 정의 (AC-V11-4, 비판자 CRITICAL-2 해결):**
- API 데이터로 question + answer 추출을 완료하지 못한 **모든** 경우:
  - fetch 오버라이드 자체가 실행되지 않은 경우
  - URL 패턴이 매칭되지 않아 가로채기를 하지 않은 경우
  - SSE 파싱에서 빈 데이터(answer가 빈 문자열)가 나온 경우
  - 스트림 읽기 중 예외가 발생한 경우
  - ReadableStream.tee()가 지원되지 않는 경우
- 어떤 경우든 null을 반환하면, 기존 DOM 셀렉터 Content Script가 MutationObserver로 대화를 감지하여 SAVE_ENTRY를 보내는 **기존 폴백 경로**가 작동함.

### 13.4 bridge.js 상세 설계

**실행 환경:** ISOLATED world (기본), `document_start`

**역할:** interceptor.js(MAIN world)가 발생시키는 CustomEvent를 수신하여 `chrome.runtime.sendMessage`로 Background에 전달. **이 파일은 이 한 가지 역할만 수행** (비판자 MINOR-1 해결).

```
document.addEventListener('__nugget_api_capture__', (e) => {
  const data = e.detail;
  if (!data || !data.platform || !data.answer) return;
  chrome.runtime.sendMessage({
    type: 'API_CAPTURE',
    payload: {
      platform: data.platform,
      question: data.question || '',
      answer: data.answer,
      sourceUrl: window.location.href
    }
  });
});
```

**CustomEvent 데이터 형식 (interceptor → bridge):**
```js
document.dispatchEvent(new CustomEvent('__nugget_api_capture__', {
  detail: {
    platform: 'claude' | 'chatgpt' | 'gemini',
    question: string,
    answer: string
  }
}));
```

### 13.5 중복 저장 방지 메커니즘 (AC-V11-4a, 비판자 CRITICAL-5 해결)

API 가로채기(API_CAPTURE)와 DOM 셀렉터(SAVE_ENTRY)가 동일한 대화를 이중으로 저장하는 것을 방지한다.

**전략: Background에서 해시 기반 차단 + Content Script에서 지연 발송**

```
1. Background 측:
   - API_CAPTURE 메시지 수신 → saveEntry() 파이프라인 실행
   - 저장 성공 시, 해당 엔트리의 hash를 nugget_api_capture_hashes 배열에 추가
   - SAVE_ENTRY 메시지 수신 시, 해시 생성 후 nugget_api_capture_hashes에 존재하면 무시
   - nugget_api_capture_hashes는 최근 100개까지만 유지 (메모리/스토리지 절약)

2. Content Script 측 (claude.js, chatgpt.js, gemini.js):
   - MutationObserver의 SAVE_ENTRY 발송 전 500ms 지연을 추가 (기존 debounce 1초 + 추가 500ms)
   - 이 지연은 API_CAPTURE가 먼저 Background에 도달하여 해시를 기록할 여유를 줌
   - 총 지연: debounce 1초(스트리밍 완료 판단) + 500ms(중복 방지 대기) = 1.5초
```

**결정 이유:**
- Background에서 해시로 필터링하므로, API 캡처와 DOM 캡처의 텍스트가 미세하게 다르더라도(공백, 마크다운 등) answer 앞 200자 기준 해시가 동일하면 차단됨.
- Content Script를 완전히 비활성화하지 않는 이유: API 캡처가 실패할 경우(파싱 실패, URL 미매칭 등) DOM 셀렉터 폴백이 반드시 작동해야 하므로 MutationObserver는 항상 활성 상태를 유지해야 함.

---

## 14. [v1.1] 원격 셀렉터 핫패치 (AC-V11-6 ~ AC-V11-9)

### 14.1 개요

AI 사이트의 DOM 구조가 변경되면 `src/config/selectors.js`의 셀렉터가 깨진다. v1.1은 GitHub Raw JSON에서 최신 셀렉터를 주기적으로 가져와 로컬 셀렉터를 대체하는 메커니즘을 추가한다.

### 14.2 원격 셀렉터 fetch 로직 (background.js)

```
함수: fetchRemoteSelectors()

1. REMOTE_SELECTORS_URL (constants.js에 정의)에서 JSON fetch
2. 응답 검증:
   - HTTP 200 확인
   - JSON 파싱
   - 스키마 검증: { version: string, selectors: { claude: PlatformSelectors, chatgpt: PlatformSelectors, gemini: PlatformSelectors } }
   - 각 PlatformSelectors에 conversationContainer, userMessage, assistantMessage, streamingIndicator 키 존재 확인
   - 검증 실패 시 원격 데이터 무시 (로컬 유지)
3. 검증 통과 시:
   - nugget_remote_selectors에 저장: { version, selectors, fetchedAt: new Date().toISOString() }
```

### 14.3 RemoteSelectorsCache 스키마

```js
{
  version: string,              // 원격 셀렉터 버전 (예: "1.0.1")
  selectors: SelectorsConfig,   // { claude, chatgpt, gemini } 각각 PlatformSelectors
  fetchedAt: string             // 마지막 fetch 시각 (ISO 8601)
}
```

### 14.4 주기적 fetch (chrome.alarms)

```
- 알람 이름: 'fetch_remote_selectors'
- 주기: 24시간 (periodInMinutes: 1440)
- 등록 시점: chrome.runtime.onInstalled 및 Service Worker 시작 시
- 알람 트리거 시: fetchRemoteSelectors() 호출
- 최초 실행: 설치 직후 1회 즉시 실행 (delayInMinutes: 1)
```

### 14.5 셀렉터 우선순위 (selectors.js 수정)

기존 Content Script에서 `SELECTORS[platform]`으로 셀렉터를 가져올 때:

```
1. chrome.storage.local에서 nugget_remote_selectors 로드
2. 원격 셀렉터가 있고 fetchedAt이 유효하면 → 원격 셀렉터의 해당 플랫폼 사용
3. 없으면 → 로컬 SELECTORS 상수 사용 (기존 동작)
```

> 이 로직은 기존 Content Script(claude.js 등)에서 셀렉터를 사용하기 전에 수행한다. `selectors.js`에 `getSelectors(platform)` 비동기 헬퍼를 추가하여 원격/로컬 병합을 처리한다.

**결정 이유:** 원격 셀렉터가 로컬보다 우선 (AC-V11-8). API 캡처 폴백 시에도 원격 우선 적용 (비판자 MINOR-2 해결).

---

## 15. [v1.1] i18n 아키텍처 (AC-V11-10 ~ AC-V11-14)

### 15.1 개요

Chrome의 `chrome.i18n.getMessage()`는 런타임에 언어를 변경할 수 없으므로, 자체 i18n 시스템을 구현한다.

### 15.2 번역 파일 구조 (src/i18n/)

```json
// src/i18n/ko.json (예시)
{
  "popup_title": "Nugget",
  "popup_search_placeholder": "검색어를 입력하세요",
  "popup_filter_all": "전체",
  "popup_filter_today": "오늘",
  "popup_filter_week": "이번 주",
  "popup_filter_month": "이번 달",
  "popup_starred_only": "별표만",
  "popup_include_junk": "잡담 포함",
  "toast_saved": "Nugget이 저장했어요",
  "toast_star_added": "별표 추가됨",
  "toast_star_removed": "별표 해제됨",
  "toast_copied": "복사됨",
  "options_language": "언어",
  "options_theme": "테마",
  "options_toast": "토스트 알림",
  "options_junk_filter": "잡담 필터",
  "settings_language_auto": "자동 감지",
  "settings_theme_light": "라이트",
  "settings_theme_dark": "다크",
  "settings_theme_system": "시스템",
  "pro_upgrade": "Pro로 업그레이드",
  "pro_upgrade_hint": "Pro로 업그레이드하면 무제한으로 사용할 수 있어요",
  "...": "..."
}
```

```json
// src/i18n/en.json (예시)
{
  "popup_title": "Nugget",
  "popup_search_placeholder": "Search...",
  "toast_saved": "Saved by Nugget",
  "...": "..."
}
```

> Frontend가 ko.json과 en.json의 전체 키를 정의한다. 모든 사용자 표시 문자열에 대한 키를 포함해야 한다 (AC-V11-10).

### 15.3 src/utils/i18n.js 시그니처 사양

```js
/**
 * 현재 언어 설정을 resolve하여 실제 언어 코드 반환
 * 'auto'이면 navigator.language 기반으로 판별
 * @param {string} langSetting - 'ko' | 'en' | 'auto'
 * @returns {string} 'ko' | 'en'
 */
function resolveLanguage(langSetting) {}

/**
 * 번역 사전을 로드 (chrome.runtime.getURL로 JSON fetch)
 * 이미 로드된 언어면 캐시 반환
 * @param {string} lang - 'ko' | 'en'
 * @returns {Promise<Object>} 번역 키-값 객체
 */
async function loadTranslations(lang) {}

/**
 * 번역 키에 해당하는 텍스트 반환
 * 키가 없으면 폴백 언어(ko)에서 찾고, 그래도 없으면 키 자체를 반환
 * @param {string} key - 번역 키 (예: 'popup_title')
 * @param {Object} [params] - 치환 파라미터 (예: { count: 5 } → "{count}개" 에서 치환)
 * @returns {string} 번역된 문자열
 */
function t(key, params) {}

/**
 * 현재 로드된 언어 코드 반환
 * @returns {string} 'ko' | 'en'
 */
function getCurrentLang() {}

/**
 * i18n 초기화: 설정에서 언어 로드 → 번역 사전 로드
 * HTML에서 data-i18n 속성을 가진 요소의 textContent를 번역으로 교체
 * @returns {Promise<void>}
 */
async function initI18n() {}

/**
 * DOM의 data-i18n 속성을 기반으로 텍스트 업데이트
 * 언어 변경 시 호출하여 페이지 전체를 갱신
 * @param {Element} [root=document] - 탐색 루트 요소
 */
function applyI18nToDOM(root) {}
```

**사용 패턴 (HTML):**
```html
<span data-i18n="popup_title">Nugget</span>
<input data-i18n-placeholder="popup_search_placeholder" placeholder="검색어를 입력하세요">
```

**사용 패턴 (JS):**
```js
// 페이지 초기화 시
await initI18n();

// 동적으로 생성한 요소
toast.textContent = t('toast_saved');
```

### 15.4 언어 변경 반영 범위 (AC-V11-12, 비판자 CRITICAL-3 해결)

| 페이지 | 반영 시점 | 메커니즘 |
|--------|-----------|----------|
| Options | 즉시 | `applyI18nToDOM()` 직접 호출 (DOM 갱신) |
| Popup | 다음 열 때 | `initI18n()` 호출 시점에 최신 설정 적용 |
| Onboarding | 이미 닫혔을 가능성 높음 | 재방문 시 `initI18n()`으로 적용 |
| Content Script 토스트 | 다음 토스트 표시 시 | `chrome.storage.onChanged` 리스너로 언어 설정 감지 → `t()` 호출 시 최신 언어 사용 |

---

## 16. [v1.1] 테마 관리 아키텍처 (AC-V11-15 ~ AC-V11-20)

### 16.1 개요

CSS 커스텀 속성(변수)으로 라이트/다크/시스템 3가지 테마를 관리한다.

### 16.2 src/utils/theme.js 시그니처 사양

```js
/**
 * 테마 설정을 resolve하여 실제 테마 반환
 * 'system'이면 OS 다크모드 여부로 판별
 * @param {string} themeSetting - 'light' | 'dark' | 'system'
 * @returns {string} 'light' | 'dark'
 */
function resolveTheme(themeSetting) {}

/**
 * 테마 초기화: 설정 로드 → <html>에 data-theme 속성 설정
 * system 모드일 때 prefers-color-scheme 미디어쿼리 리스너 등록
 * @returns {Promise<void>}
 */
async function initTheme() {}

/**
 * 테마 변경 적용: <html>의 data-theme 속성 변경
 * @param {string} theme - 'light' | 'dark'
 */
function applyTheme(theme) {}

/**
 * 시스템 테마 변경 감지 리스너 등록
 * 'system' 설정일 때만 활성화
 * prefers-color-scheme 변경 시 applyTheme() 자동 호출
 * @param {string} themeSetting - 현재 테마 설정 ('light'|'dark'|'system')
 */
function watchSystemTheme(themeSetting) {}
```

### 16.3 CSS 커스텀 속성 구조 (AC-V11-15)

Frontend가 각 CSS 파일(popup.css, options.css, onboarding.css)에 정의:

```css
/* 라이트 테마 (기본) */
:root, [data-theme="light"] {
  --bg-primary: #FFFFFF;
  --bg-secondary: #F5F5F5;
  --bg-card: #FFFFFF;
  --text-primary: #1A1A1A;
  --text-secondary: #666666;
  --border-color: #E0E0E0;
  --nugget-gold: #E5A00D;          /* 브랜드 컬러 유지 (AC-V11-19) */
  --shadow: 0 2px 8px rgba(0,0,0,0.1);
  /* ... 기타 필요한 변수 ... */
}

/* 다크 테마 */
[data-theme="dark"] {
  --bg-primary: #1A1A1A;
  --bg-secondary: #2D2D2D;
  --bg-card: #2D2D2D;
  --text-primary: #E0E0E0;
  --text-secondary: #999999;
  --border-color: #404040;
  --nugget-gold: #F0B429;          /* 다크 배경에서 가독성 향상 변형 (AC-V11-19) */
  --shadow: 0 2px 8px rgba(0,0,0,0.4);
  /* ... 기타 필요한 변수 ... */
}
```

> UI디자이너가 정확한 색상 값을 결정한다. 위는 설계 가이드라인.

### 16.4 테마 적용 방식

```
1. 페이지 로드 시 theme.js의 initTheme() 호출
2. initTheme()가 nugget_settings.theme 값을 읽음
3. resolveTheme()로 실제 테마 결정 ('light' | 'dark')
4. <html data-theme="dark"> 또는 <html data-theme="light"> 설정
5. CSS가 [data-theme] 속성 셀렉터로 변수 값을 자동 전환
6. 'system' 모드: prefers-color-scheme 미디어쿼리 리스너 등록 → OS 변경 시 실시간 반영 (AC-V11-20)
```

---

## 17. [v1.1] 시그니처 사양 — 새 모듈

### 17.1 src/content/interceptor.js

```js
/**
 * MAIN world에서 실행. window.fetch를 오버라이드하여 AI 사이트의 SSE 응답을 캡처.
 * 캡처된 데이터는 CustomEvent('__nugget_api_capture__')로 bridge.js에 전달.
 */

/**
 * fetch 오버라이드 설치
 * document_start에서 자동 실행됨 (IIFE)
 */
(function installFetchInterceptor() {})();

/**
 * URL이 API 엔드포인트 패턴과 매칭되는지 확인
 * @param {string} url - fetch URL
 * @param {string} platform - 'claude' | 'chatgpt' | 'gemini'
 * @returns {boolean}
 */
function isApiEndpoint(url, platform) {}

/**
 * 복제된 ReadableStream에서 Claude SSE 데이터 파싱
 * @param {ReadableStream} stream - tee()로 복제된 스트림
 * @param {string} requestBody - 요청 body (질문 추출용)
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseClaudeSSE(stream, requestBody) {}

/**
 * 복제된 ReadableStream에서 ChatGPT SSE 데이터 파싱
 * @param {ReadableStream} stream
 * @param {string} requestBody
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseChatGPTSSE(stream, requestBody) {}

/**
 * 복제된 ReadableStream에서 Gemini 응답 데이터 파싱
 * @param {ReadableStream} stream
 * @param {string} requestBody
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseGeminiResponse(stream, requestBody) {}

/**
 * 파싱된 대화 데이터를 CustomEvent로 bridge.js에 전달
 * @param {string} platform
 * @param {string} question
 * @param {string} answer
 */
function dispatchCapture(platform, question, answer) {}
```

### 17.2 src/content/bridge.js

```js
/**
 * ISOLATED world에서 실행. interceptor.js의 CustomEvent를 수신하여
 * chrome.runtime.sendMessage로 Background에 전달.
 * 이 파일은 이 한 가지 역할만 수행.
 */

/**
 * CustomEvent 리스너 등록 및 API_CAPTURE 메시지 전달
 * document_start에서 자동 실행됨 (IIFE)
 */
(function initBridge() {})();
```

### 17.3 src/utils/i18n.js

> 섹션 15.3에서 상세 정의됨. 여기서는 요약.

```js
function resolveLanguage(langSetting) {}
async function loadTranslations(lang) {}
function t(key, params) {}
function getCurrentLang() {}
async function initI18n() {}
function applyI18nToDOM(root) {}
```

### 17.4 src/utils/theme.js

> 섹션 16.2에서 상세 정의됨. 여기서는 요약.

```js
function resolveTheme(themeSetting) {}
async function initTheme() {}
function applyTheme(theme) {}
function watchSystemTheme(themeSetting) {}
```

### 17.5 background.js 새 함수 (v1.1 추가)

```js
/**
 * API_CAPTURE 메시지 처리: saveEntry() 파이프라인 실행 + 해시 기록
 * @param {{ platform: string, question: string, answer: string, sourceUrl: string }} data
 * @returns {Promise<{ success: boolean, entry?: NuggetEntry, error?: string }>}
 */
async function handleApiCapture(data) {}

/**
 * API 캡처 해시 목록 로드
 * @returns {Promise<string[]>}
 */
async function loadApiCaptureHashes() {}

/**
 * API 캡처 해시 기록 (최근 100개까지 유지)
 * @param {string} hash
 * @returns {Promise<void>}
 */
async function recordApiCaptureHash(hash) {}

/**
 * SAVE_ENTRY 수신 시 API 캡처 해시와 비교하여 중복 여부 확인
 * @param {string} hash - 생성된 해시
 * @returns {Promise<boolean>} true이면 중복 (무시해야 함)
 */
async function isDuplicateOfApiCapture(hash) {}

/**
 * 원격 셀렉터 fetch 및 캐시 (AC-V11-6)
 * @returns {Promise<void>}
 */
async function fetchRemoteSelectors() {}

/**
 * 원격 셀렉터 JSON 스키마 검증 (AC-V11-9)
 * @param {Object} data - fetch된 JSON
 * @returns {boolean}
 */
function validateRemoteSelectors(data) {}
```

---

## 18. [v1.1] 데이터 흐름 요약

### 18.1 API 가로채기 저장 흐름 (v1.1 메인 경로)

```
사용자가 AI에게 질문
  → AI가 답변 스트리밍 (fetch 기반 SSE)
  → interceptor.js (MAIN world): window.fetch 오버라이드가 응답 가로챔
  → interceptor.js: ReadableStream.tee()로 스트림 복제
  → interceptor.js: 원본 스트림으로 Response를 만들어 페이지에 반환 (기능 영향 없음)
  → interceptor.js: 복제 스트림을 플랫폼별 SSE 파서로 파싱
  → interceptor.js: question + answer 추출 성공
  → interceptor.js: CustomEvent('__nugget_api_capture__')로 bridge.js에 전달
  → bridge.js (ISOLATED world): API_CAPTURE 메시지를 Background에 전송
  → Background: handleApiCapture() 실행
    → 해시 생성 → 중복 체크 (기존 entries)
    → 잡담 필터 적용
    → 자동 태깅
    → NuggetEntry 생성 → 저장
    → 해시를 nugget_api_capture_hashes에 기록
    → 무료 한도 체크 → 필요 시 아카이브
  → Background: 응답 { success: true }
```

### 18.2 DOM 셀렉터 폴백 흐름 (v1.1, API 캡처 실패 시)

```
API 캡처 실패 (파서 null 반환 / interceptor 미실행)
  → 기존 Content Script (claude.js 등): MutationObserver가 DOM 변화 감지 (기존 로직)
  → debounce 1초 후 스트리밍 완료 판단
  → 질문+답변 추출
  → 500ms 추가 지연 (API_CAPTURE 중복 방지 대기)
  → SAVE_ENTRY 메시지 전송
  → Background: 해시 생성 → nugget_api_capture_hashes 확인
    → 해시가 있으면 → 무시 (API_CAPTURE로 이미 저장됨)
    → 해시가 없으면 → 기존 saveEntry() 파이프라인 실행
  → Content Script: 성공 시 토스트 표시
```

### 18.3 원격 셀렉터 갱신 흐름

```
Service Worker 시작 또는 알람 트리거 (24시간 주기)
  → Background: fetchRemoteSelectors() 호출
  → GitHub Raw URL에서 JSON fetch
  → 스키마 검증 (validateRemoteSelectors)
    → 실패 시 → 무시 (로컬 셀렉터 유지)
    → 성공 시 → nugget_remote_selectors에 저장
  → 다음 Content Script 실행 시 원격 셀렉터 자동 적용
```

---

## 19. [v1.1] 통합 계약 업데이트

> v1.0 통합 계약(섹션 8)에 추가되는 항목. 기존 항목은 유지.

### 19.1 새 파일 이름과 경로

| 파일 | 경로 | 담당 |
|------|------|------|
| API 가로채기 (MAIN world) | `nugget/src/content/interceptor.js` | Backend |
| API 브릿지 (ISOLATED world) | `nugget/src/content/bridge.js` | Backend |
| i18n 유틸리티 | `nugget/src/utils/i18n.js` | Backend |
| 테마 유틸리티 | `nugget/src/utils/theme.js` | Backend |
| 한국어 번역 | `nugget/src/i18n/ko.json` | Frontend |
| 영어 번역 | `nugget/src/i18n/en.json` | Frontend |

### 19.2 새 Chrome 메시지 타입

```js
// bridge.js → Background (v1.1)
'API_CAPTURE'               // { platform, question, answer, sourceUrl }
```

### 19.3 새 Storage 키 이름

```js
'nugget_remote_selectors'    // RemoteSelectorsCache { version, selectors, fetchedAt }
'nugget_api_capture_hashes'  // string[] — 최근 100개 해시
```

### 19.4 새 상수 (constants.js)

```js
// v1.1 추가 상수
const SUPPORTED_LANGUAGES = ['ko', 'en'];
const DEFAULT_LANGUAGE = 'auto';
const FALLBACK_LANGUAGE = 'ko';
const SUPPORTED_THEMES = ['light', 'dark', 'system'];
const DEFAULT_THEME = 'system';
const REMOTE_SELECTORS_URL = 'https://raw.githubusercontent.com/{owner}/{repo}/main/selectors.json';
const REMOTE_SELECTORS_CACHE_HOURS = 24;
const REMOTE_SELECTORS_ALARM_NAME = 'fetch_remote_selectors';
const API_CAPTURE_HASH_MAX = 100;
const API_CAPTURE_EVENT_NAME = '__nugget_api_capture__';
const SAVE_ENTRY_DEDUP_DELAY_MS = 500;
```

### 19.5 manifest.json 변경 요약

| 변경 | 내용 |
|------|------|
| `version` | `"1.0.0"` → `"1.1.0"` |
| `permissions` | `"alarms"` 추가 |
| `content_scripts` | MAIN world `interceptor.js` 항목 추가 (document_start) |
| `content_scripts` | ISOLATED world `bridge.js` 항목 추가 (document_start) |
| 기존 content_scripts | 그대로 유지 (DOM 셀렉터 폴백) |

### 19.6 UPDATE_SETTINGS 허용 키 추가

background.js의 `ALLOWED_SETTINGS_KEYS` 배열에 `'language'`와 `'theme'`를 추가해야 한다:

```js
const ALLOWED_SETTINGS_KEYS = ['toastEnabled', 'junkFilterEnabled', 'shortcutKey', 'language', 'theme'];
```

---

## 20. [v1.1] critique_v1.1_report.md 반영

| 비판 항목 | 해결 방법 | 설계 섹션 |
|-----------|-----------|-----------|
| CRITICAL-1 (SSE 파서 AC 누락) | 섹션 13.3에서 플랫폼별 파서 시그니처와 파싱 로직을 상세 정의 | 13.3 |
| CRITICAL-2 (API 캡처 실패 정의 모호) | 섹션 13.3 하단에 "파싱 실패의 정의"를 명시 — API 데이터로 Q+A 추출을 완료하지 못한 모든 경우 | 13.3 |
| CRITICAL-5 (중복 저장 방지 메커니즘 누락) | 섹션 13.5에서 해시 기반 차단 + Content Script 500ms 지연 전략 상세 정의 | 13.5 |
| MINOR-1 (bridge.js 역할 분담) | 섹션 13.4에서 bridge.js의 역할을 "API 캡처 → Background 전달만"으로 명확히 한정 | 13.4 |
| MINOR-2 (원격 셀렉터 우선순위) | 섹션 14.5에서 폴백 시에도 원격 우선 적용 명시 | 14.5 |
| MINOR-3 (24시간 주기 기준) | 섹션 14.4에서 chrome.alarms 기반 periodInMinutes: 1440으로 명시 | 14.4 |
| MINOR-4 (원격 JSON 스키마) | 섹션 14.2에서 검증 기준을 상세 명시 (필수 키 존재 확인) | 14.2 |
| MINOR-5 ('auto' 언어 동작) | 섹션 5.3 NuggetSettings 하단에 'auto' 동작 명시 | 5.3 |
| MINOR-7 (document_start 타이밍) | Pre-mortem v1.1 4번으로 추가 (.plan.v1.1.md에 반영됨) | - |
| MINOR-8 (manifest 추가 방식) | 섹션 3에서 별도 항목으로 추가 명시 | 3 |
| MINOR-9 (src/shared 소유권 충돌) | `src/utils/`에 배치하여 Backend 소유권으로 해결 | 2 |
| MINOR-10 (v1.0→v1.1 마이그레이션) | 섹션 5.3에 마이그레이션 설명 추가 | 5.3 |

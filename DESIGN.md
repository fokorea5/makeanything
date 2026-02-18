# DESIGN.md — Nugget: AI Chat Memory (Chrome Extension)

설계일: 2026-02-18
설계자: 기술 아키텍트
참조: `.plan.md`, `reports/oracle_report.md`, `reports/critique_report.md`

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
│   │   ├── claude.js               # claude.ai 전용 Content Script
│   │   ├── chatgpt.js              # chatgpt.com / chat.openai.com 전용 Content Script
│   │   ├── gemini.js               # gemini.google.com 전용 Content Script
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
│   └── lib/
│       └── ExtPay.js               # ExtensionPay 라이브러리 (npm extpay v3.1.2에서 복사)
├── assets/
│   ├── icon-16.png
│   ├── icon-32.png
│   ├── icon-48.png
│   └── icon-128.png
└── _locales/                        # (향후 i18n 대비, 현재는 빈 폴더 — 선택사항)
```

**결정 이유:**
- Content Script를 플랫폼별로 분리한 이유: 각 AI 사이트의 DOM 구조가 완전히 다르므로 하나의 파일에 합치면 유지보수가 어려움. 셀렉터 실패 시 해당 사이트만 수정하면 됨.
- `src/config/selectors.js` 분리: AC-2 요구사항. DOM 구조 변경 시 이 파일만 수정하면 핫패치 가능 (Pre-mortem 1번 대응).
- `src/lib/ExtPay.js`: 번들러 없이 직접 파일 복사 방식 사용. npm에서 `extpay@3.1.2`의 `dist/ExtPay.js`를 복사.
- `extpay-content.js`: ExtensionPay의 `onPaid` 콜백을 받기 위해 `extensionpay.com`에 주입되는 Content Script (oracle_report.md 참조).

---

## 3. manifest.json 설계

```json
{
  "manifest_version": 3,
  "name": "Nugget – AI Chat Memory",
  "version": "1.0.0",
  "description": "AI 대화를 자동 저장하고 나중에 쉽게 찾으세요",
  "permissions": [
    "storage",
    "unlimitedStorage",
    "activeTab"
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
- Content Scripts에 `types.js`와 `selectors.js`를 주입: Content Script에서 타입 상수와 셀렉터에 접근 가능하게 함.
- `run_at: "document_idle"`: AI 사이트가 렌더링 완료된 후 스크립트 실행.
- `run_at: "document_start"` (ExtensionPay): oracle_report.md에서 요구하는 설정 그대로.
- CSP에 `connect-src https://extensionpay.com`: AC-30 요구사항.

---

## 4. 메시징 아키텍처

Content Script와 Background(Service Worker) 사이의 모든 통신은 `chrome.runtime.sendMessage`를 사용한다.
Popup/Options/Onboarding과 Background 사이도 동일하다.

### 4.1 메시지 흐름도

```
[Content Script]  --sendMessage-->  [Background Service Worker]  <--sendMessage--  [Popup / Options / Onboarding]
   (claude.js)                          (background.js)                              (popup.js / options.js)
   (chatgpt.js)                              |
   (gemini.js)                        chrome.storage.local
```

### 4.2 메시지 타입 정의

모든 메시지는 `{ type: string, payload: object }` 형식을 따른다.

| 방향 | type | payload | 응답 | 설명 |
|------|------|---------|------|------|
| Content -> BG | `SAVE_ENTRY` | `{ question, answer, platform, sourceUrl }` | `{ success, entry?, error? }` | 대화 감지 후 저장 요청 |
| Content -> BG | `SELECTOR_FAILED` | `{ platform, selector, error }` | `{ success }` | 셀렉터 작동 실패 알림 (AC-3) |
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
  mdCopyResetDate: string     // MD 복사 카운터 리셋 날짜 (ISO date, 매월 1일 0시 UTC, AC-23)
}
```

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

# QA Report — Nugget: AI Chat Memory (Chrome Extension)

검증일: 2026-02-18
검증자: QA (품질 보증관)
참조: `.plan.md`, `DESIGN.md` 섹션 8 (통합 계약)

---

## 1. 통합 계약 검증

### 1.1 파일 존재 확인

| 파일 (통합 계약 8.1) | 경로 | 존재 여부 | 판정 |
|---|---|:---:|:---:|
| manifest.json | `nugget/manifest.json` | O | PASS |
| Background Service Worker | `nugget/src/background/background.js` | O | PASS |
| Content Script (Claude) | `nugget/src/content/claude.js` | O | PASS |
| Content Script (ChatGPT) | `nugget/src/content/chatgpt.js` | O | PASS |
| Content Script (Gemini) | `nugget/src/content/gemini.js` | O | PASS |
| Content Script (ExtensionPay) | `nugget/src/content/extpay-content.js` | O | PASS |
| DOM 셀렉터 설정 | `nugget/src/config/selectors.js` | O | PASS |
| ExtensionPay 라이브러리 | `nugget/src/lib/ExtPay.js` | O | PASS |
| **공유 타입 정의** | **`nugget/src/shared/types.js`** | **X** | **FAIL** |
| 공유 상수 | `nugget/src/shared/constants.js` | O | PASS |
| 공유 유틸리티 | `nugget/src/shared/utils.js` | O | PASS |
| Popup HTML | `nugget/src/popup/popup.html` | O | PASS |
| Popup JS | `nugget/src/popup/popup.js` | O | PASS |
| Popup CSS | `nugget/src/popup/popup.css` | O | PASS |
| Options HTML | `nugget/src/options/options.html` | O | PASS |
| Options JS | `nugget/src/options/options.js` | O | PASS |
| Options CSS | `nugget/src/options/options.css` | O | PASS |
| Onboarding HTML | `nugget/src/onboarding/onboarding.html` | O | PASS |
| Onboarding JS | `nugget/src/onboarding/onboarding.js` | O | PASS |
| Onboarding CSS | `nugget/src/onboarding/onboarding.css` | O | PASS |
| 아이콘 (16,32,48,128) | `nugget/assets/icon-*.png` | O | PASS |

### 1.2 메시지 타입 일치 확인

| 메시지 타입 (통합 계약 8.2) | Frontend 전송 | Background 수신 | 판정 |
|---|:---:|:---:|:---:|
| `SAVE_ENTRY` | Content Scripts (O) | background.js:798 (O) | PASS |
| `SELECTOR_FAILED` | Content Scripts (O) | background.js:804 (O) | PASS |
| `GET_ENTRIES` | popup.js:240, options.js:101 (O) | background.js:814 (O) | PASS |
| `SEARCH_ENTRIES` | popup.js:235 (O) | background.js:820 (O) | PASS |
| `TOGGLE_STAR` | popup.js:436 (O) | background.js:831 (O) | PASS |
| `UPDATE_NOTE` | popup.js:465 (O) | background.js:841 (O) | PASS |
| `COPY_MARKDOWN` | popup.js:501 (O) | background.js:851 (O) | PASS |
| `GET_TODAYS_NUGGET` | popup.js:162 (O) | background.js:861 (O) | PASS |
| `DISMISS_TODAYS_NUGGET` | popup.js:214 (O) | background.js:867 (O) | PASS |
| `ADD_CUSTOM_TAG` | popup.js MSG 정의 (O) | background.js:874 (O) | PASS |
| `GET_SETTINGS` | popup.js:160, options.js:98 (O) | background.js:885 (O) | PASS |
| `UPDATE_SETTINGS` | options.js:150 (O) | background.js:891 (O) | PASS |
| `GET_PRO_STATUS` | popup.js:161, options.js:100 (O) | background.js:903 (O) | PASS |
| `OPEN_PAYMENT_PAGE` | popup.js:943, options.js:420 (O) | background.js:910 (O) | PASS |
| `GET_JUNK_KEYWORDS` | options.js:99 (O) | background.js:924 (O) | PASS |
| `UPDATE_JUNK_KEYWORDS` | options.js:243 (O) | background.js:930 (O) | PASS |
| `EXPORT_JSON` | popup.js:874, options.js:311 (O) | background.js:942 (O) | PASS |
| `IMPORT_JSON` | popup.js:923, options.js:358 (O) | background.js:948 (O) | PASS |
| `EXPORT_MARKDOWN_FILE` | options.js:380 (O) | background.js:958 (O) | PASS |
| `EXPORT_PDF` | options.js:403 (O) | background.js:973 (O) | PASS |
| `PRO_STATUS_CHANGED` | extpay-content.js:29 (O) | background.js:987 (O) | PASS |
| `SHOW_TOAST` | background.js:1054 (O) | content scripts (O) | PASS |

### 1.3 Storage 키 일치 확인

| Storage 키 (통합 계약 8.3) | Background 사용 | Frontend 사용 | 판정 |
|---|:---:|:---:|:---:|
| `nugget_entries` | background.js:31 (O) | popup.js:14 (O) | PASS |
| `nugget_settings` | background.js:32 (O) | popup.js:15 (O) | PASS |
| `nugget_junk_keywords` | background.js:33 (O) | popup.js:16 (O) | PASS |
| `nugget_pro_cache` | background.js:34 (O) | popup.js:17 (O) | PASS |
| `nugget_todays_nugget_dismissed` | background.js:35 (O) | popup.js:18 (O) | PASS |
| `nugget_custom_tags` | background.js:36 (O) | popup.js:19 (O) | PASS |

---

## 2. AC별 PASS/FAIL 판정

### 자동 저장 (AC-1 ~ AC-4)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-1 | PASS | claude.js, chatgpt.js, gemini.js가 각각 해당 사이트에서 SAVE_ENTRY 메시지 전송. manifest.json에 claude.ai, chatgpt.com, chat.openai.com, gemini.google.com 매칭 정의됨. |
| AC-2 | PASS | 모든 content script가 MutationObserver + 1초 debounce로 스트리밍 완료 감지. 셀렉터는 `src/config/selectors.js`로 분리됨. |
| AC-3 | PASS | content script에서 셀렉터 실패 시 SELECTOR_FAILED 메시지 전송 → background.js에서 `chrome.action.setBadgeText({ text: "!" })` 설정. popup.html에 에러 배너 구현. |
| AC-4 | PASS | `_generateHash(question, answer, dateString)` 구현. `saveEntry()`에서 저장 전 기존 entries의 hash와 비교하여 중복 스킵. |

### 잡담 필터 (AC-5 ~ AC-7)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-5 | **FAIL** | 아래 상세 참조 (FAIL-01) |
| AC-6 | PASS | `DEFAULT_JUNK_KEYWORDS` 내장 (background.js:58-62). Options 페이지에서 추가/삭제 UI 구현 (options.js, options.html:74-108). |
| AC-7 | PASS | isJunk 엔트리는 삭제하지 않고 마킹만. popup.js의 필터에 `includeJunk` 토글 구현. popup.html에 "잡담 포함" 버튼 존재. |

### 자동 태깅 (AC-8 ~ AC-9)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-8 | PASS | `_autoTag(question, answer)` 함수 구현. 6개 태그 카테고리 + "기타" 폴백. |
| AC-9 | PASS | `addCustomTag()` 함수에서 `!settings.isPro` 체크 후 거부. popup.html에 태그 한도 말풍선 구현. |

### 검색 & 필터 (AC-10 ~ AC-11)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-10 | **FAIL** | 아래 상세 참조 (FAIL-02) |
| AC-11 | PASS | `highlightText()` 함수에서 `<mark class="highlight">` 태그로 하이라이팅. CSS에서 `.highlight { background: #FEF08A; }` 정의. |

### Markdown 복사 (AC-12 ~ AC-13)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-12 | PASS | `_entryToMarkdown()` 함수 구현. 코드블록은 answer 원문에 포함된 것 그대로 유지. 메모 있으면 블록쿼트 추가. |
| AC-13 | PASS | `checkAndIncrementMdCopy()` 함수에서 무료 월 20회 제한. popup.js에서 복사 성공 시 "복사됨" 피드백 구현. |

### 사용자 메모 (AC-14 ~ AC-15)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-14 | PASS | popup.js에서 textarea blur 시 `handleNoteSave()` 호출 → UPDATE_NOTE 메시지 → background.js `updateNote()`. 검색에 메모 포함 (searchEntries에서 e.note 검색). |
| AC-15 | PASS | `updateNote()`에서 `!settings.isPro && note.length > MAX_NOTE` 체크. popup.js에서 `maxlength` 속성 + 카운터 UI. |

### 별표 & 단축키 (AC-16)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-16 | PASS | manifest.json에 `commands.toggle-star` 정의 (Ctrl+Shift+S). background.js에서 `chrome.commands.onCommand` 리스너로 최근 엔트리 starred 토글. 토스트 피드백 구현. |

### 백업/복원 (AC-17 ~ AC-18)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-17 | PASS | `exportJSON()` 함수: entries + settings + exportDate 반환. `importJSON()` 함수: id 기준 중복 제거 + 병합. popup.js와 options.js에서 JSON 파일 다운로드/업로드 구현. |
| AC-18 | PASS | `updateBadge()` 함수에서 400개(80%) 이상 노란색 뱃지, 500개 이상 빨간색 뱃지. popup.js에 용량 경고 배너. Pro: 500 단위 마일스톤. Options에 프로그레스바. |

### 토스트 알림 (AC-19)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-19 | PASS | 각 content script에 `showToast()` 구현: 우측 하단, 1800ms 표시, 페이드 애니메이션. Options에서 `toastEnabled` 토글 가능. |

> **주의:** Content script의 토스트는 `settings.toastEnabled`를 확인하지 않음. 아래 FAIL-03 참조.

### Today's Nugget (AC-20)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-20 | PASS | `getTodaysNugget()` 함수에서 과거의 오늘 우선, 없으면 랜덤, 잡담/아카이브 제외. dismiss 시 날짜 저장. popup.html에 배너 + 닫기(X) 구현. 클릭 시 카드로 스크롤. |

### 온보딩 (AC-21)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-21 | PASS | background.js에서 `chrome.runtime.onInstalled` → 온보딩 페이지 열기. onboarding.html에 안내 + 샘플 카드 + 단축키 + Pro 소개(가볍게) 구현. |

### Pro 결제 (AC-22 ~ AC-24a)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-22 | PASS | ExtensionPay 연동 구현. `OPEN_PAYMENT_PAGE` → `extpay.openPaymentPage()`. popup.html과 options.html에 Pro 업그레이드 버튼. |
| AC-23 | **FAIL** | 아래 상세 참조 (FAIL-04) |
| AC-23a | PASS | `importJSON()` 함수에서 병합 후 `enforceFreeLimits()` 호출. 무료 사용자 500개 초과분 자동 archived. |
| AC-24 | PASS | popup.js에서 한도 도달 시 말풍선에 "Pro로 업그레이드" 안내. background.js `updateNote()`에서도 부드러운 안내 메시지. |
| AC-24a | PASS | `checkProStatus()` 함수에서 7일 캐시 + 오프라인 시 expired 플래그. popup.js/options.js에서 expired 시 "구독 확인 필요" 배너 표시. |

### Popup UI (AC-25)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-25 | PASS | popup.html 구조: Today's Nugget → 검색 → 필터 → 카드 리스트 → 미니 통계 → 하단 버튼. 설계 와이어프레임 순서와 일치. |

### 데이터 구조 (AC-26 ~ AC-27)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-26 | PASS | `saveEntry()` 함수에서 생성하는 entry 객체에 모든 필드 포함: id, date, platform, question, answer, tags[], starred, isJunk, archived, sourceUrl, note, hash. |
| AC-27 | PASS | `defaultSettings()` 함수에 모든 필드 포함: toastEnabled, junkFilterEnabled, shortcutKey, maxFreeEntries, isPro, mdCopyCount, mdCopyResetDate. proStatusCache는 별도 storage 키로 관리. |

### 기타 (AC-28 ~ AC-30)

| AC | 판정 | 근거 |
|---|:---:|---|
| AC-28 | PASS | background.js에서 메모리 변수로 상태를 보관하지 않음. 모든 데이터는 `storageGet`/`storageSet`을 통해 `chrome.storage.local`에서 읽고 씀. |
| AC-29 | PASS | 모든 HTML 파일에서 인라인 스크립트 없음. 별도 JS 파일을 `<script src>` 태그로 참조. |
| AC-30 | PASS | manifest.json의 CSP에 `connect-src 'self' https://extensionpay.com` 포함. |

---

## 3. FAIL 상세

### FAIL-01: [utils.js:57, background.js:169] [AC-5] 잡담 필터 1단계 조건이 설계와 불일치

**문제:**
AC-5 사양: "1단계: 질문이 짧고(CJK: 15자 미만) AND 답변 200자 미만 → isJunk:true. 2단계: 질문이 잡담 키워드 exact match → isJunk:true"

DESIGN.md 섹션 6.2 수정 사항에서 명확히 기술함: "1단계와 2단계는 OR 관계이다. 어느 하나라도 통과하면 isJunk:true."

**현재 코드 (utils.js:57):**
```js
if (isShort) return true;  // 1단계 통과하면 즉시 true
```

**실패 시나리오:**
1단계에서 `isShort`가 true이면 2단계(키워드 매칭)를 건너뛰고 바로 `isJunk:true`를 반환한다. 이것 자체는 OR 관계이므로 정확한 결과를 내지만, **진짜 문제는 1단계 조건의 범위가 너무 넓다는 것이다.**

- 입력: `question = "왜?"`, `answer = "왜냐하면..."` (답변 8자)
  - CJK 문자 포함 → `q.length < 15` (2자) AND `a.length < 200` (8자) → **isJunk:true**
  - 이 경우 짧지만 의미 있는 질문도 잡담으로 분류됨
- 입력: `question = "What is AI?"`, `answer = "AI stands for..."` (답변 30자)
  - CJK 없음 → `wordCount < 5` (3단어) AND `a.length < 200` (30자) → **isJunk:true**
  - 짧은 질문이지만 의미 있는 답변도 잡담으로 잡힘

**결론:** 이것은 AC-5 사양에 명시된 대로 구현되어 있으므로, 코드는 사양을 정확히 따른다. 그러나 실사용에서 짧은 질문 + 짧은 답변 조합이 모두 잡담 처리되므로, `junkFilterEnabled`를 끄지 않으면 유의미한 짧은 대화를 놓치는 사례가 빈번하게 발생할 것이다. **보고 등급: WARN (사양 충실이나 UX 위험).**

> 재판정: AC-5 자체는 **PASS**. (사양 그대로 구현됨.) 하지만 아래 FAIL은 유지:

**실제 FAIL 사유:** Content script의 `onMutation()` 함수에 `if (answer.length < 50) return;` 가드가 있다 (claude.js:141, chatgpt.js:124, gemini.js:127). 이 50자 가드는 스트리밍 중간 저장 방지를 위한 것이지만, **답변이 50자 미만인 정상 대화를 완전히 차단한다.** AC-1은 "질문+답변 자동 저장"을 요구하는데, 답변이 50자 미만이면 저장 자체가 되지 않으므로 잡담 필터링 이전에 데이터가 유실된다.

**판정 수정:** FAIL: [claude.js:141, chatgpt.js:124, gemini.js:127] [AC-1] 답변 50자 미만 대화가 저장되지 않음. 짧은 답변(예: "네, 맞습니다." + 설명)도 누락됨.

### FAIL-02: [popup.js:250-261] [AC-10] 기간 필터(오늘/이번주/이번달)가 Background로 전달되지 않음

**문제:**
AC-10 사양: "기간 필터(오늘/이번주/이번달/직접설정)"

popup.js `buildFiltersPayload()`에서 `period`와 `dateFrom`/`dateTo`를 보내지만, background.js의 `applyFilters()` 함수는 `period` 필터를 처리하지 않는다.

```js
// popup.js buildFiltersPayload():
return {
  platforms: f.platforms.length > 0 ? f.platforms : null,
  period: f.period,         // ← 'today', 'week', 'month' 전달
  dateFrom: f.dateFrom,     // ← 직접 설정일 때만 값이 있음
  dateTo: f.dateTo,
  ...
};
```

```js
// background.js applyFilters():
if (filters.dateFrom) { ... }  // dateFrom만 처리
if (filters.dateTo) { ... }    // dateTo만 처리
// period 처리 없음!
```

**실패 시나리오:**
1. 사용자가 Popup에서 "오늘" 기간 필터를 선택
2. popup.js가 `{ period: 'today', dateFrom: null, dateTo: null }` 전송
3. background.js는 `period: 'today'`를 무시하고 전체 엔트리 반환
4. 필터가 실질적으로 동작하지 않음

**또한:** popup.js에서 `period`가 'today', 'week', 'month'일 때 `dateFrom`/`dateTo`를 자동 계산하는 로직이 없다. 사용자가 "직접 설정"을 선택하고 날짜를 지정해야만 기간 필터가 동작한다.

**추가 문제:** `platforms` 필터도 background.js `applyFilters()`에서 단일 `filters.platform`만 처리한다 (462행). 하지만 popup.js는 `platforms` (복수형 배열)을 보낸다. 필드명 불일치로 플랫폼 필터도 동작하지 않음.

### FAIL-03: [claude.js:158, chatgpt.js:140, gemini.js:139] [AC-19] 토스트 알림 설정(toastEnabled) 무시

**문제:**
AC-19 사양: "Options에서 끄기 가능"
AC-27 사양: "toastEnabled 설정 필드"

Content script의 `showToast()` 호출 시 `settings.toastEnabled` 여부를 확인하지 않는다. SAVE_ENTRY 응답 후 무조건 토스트를 표시한다.

```js
// claude.js:157-159
if (response && response.success) {
  showToast('Nugget이 저장했어요');  // toastEnabled 체크 없음
}
```

**원인:** Content Script는 Background의 설정에 직접 접근하기 어렵다. Background가 SAVE_ENTRY 응답에 `toastEnabled` 값을 포함하거나, Content Script가 별도로 설정을 요청해야 한다.

**현재 Background의 SAVE_ENTRY 응답:**
```js
return { success: true, entry };  // toastEnabled 포함 안 됨
```

**실패 시나리오:**
1. 사용자가 Options에서 "토스트 알림" 끔
2. AI 사이트에서 대화 완료
3. Content Script가 여전히 토스트를 표시함
4. 사용자의 설정이 무시됨

### FAIL-04: [background.js:236-259] [AC-23] enforceFreeLimits가 이미 archived된 엔트리를 풀지 않는 구조적 문제

**문제:**
AC-23 사양: "저장 500개 초과 시 오래된 엔트리를 archived:true로 마킹"

`enforceFreeLimits()` 함수:
```js
const activeEntries = entries
  .filter(e => !e.archived && !e.isJunk)  // archived를 제외하고 카운트
  .sort((a, b) => new Date(b.date) - new Date(a.date));

const toArchiveIds = new Set(
  activeEntries.slice(MAX).map(e => e.id)
);

return entries.map(e => ({
  ...e,
  archived: toArchiveIds.has(e.id) ? true : e.archived
}));
```

**문제점:** `toArchiveIds.has(e.id) ? true : e.archived` -- 한번 archived된 엔트리는 무료 사용자 상태에서 **절대 해제되지 않는다.** 예를 들어:

1. 500개가 꽉 찬 상태에서 1개 추가 → 가장 오래된 1개가 archived
2. 사용자가 최근 엔트리 50개를 삭제 (실제로 삭제 기능은 없지만, isJunk으로 변경 등)
3. active 엔트리가 450개로 줄어도, 이전에 archived된 엔트리는 다시 살아나지 않음

이것은 AC-23의 "숨김 처리" 정책에서 "Pro 업그레이드 시 archived 해제되어 전체 열람 가능"만 있고 무료 사용자의 archived 해제 로직이 없기 때문이다. 설계서에도 명시되지 않았으므로 코드가 설계를 따른 것이지만, 사용자 관점에서는 한 번 숨겨진 엔트리가 영원히 돌아오지 않는다.

**판정: FAIL** (설계에서 고려하지 못한 실사용 문제)

> 수정 방안: `enforceFreeLimits()`가 호출될 때, active 엔트리가 500개 미만이면 가장 최근에 archived된 것부터 해제하는 로직 추가. 또는 설계 문서에 "무료 사용자의 archived 해제 정책" 명시 필요.

### FAIL-05: [manifest.json:41] 통합 계약 위반 — types.js 파일 누락

**문제:**
manifest.json의 content_scripts에서 `src/shared/types.js`를 주입하도록 설정되어 있다:
```json
"js": ["src/shared/types.js", "src/config/selectors.js", "src/content/claude.js"]
```

그러나 `nugget/src/shared/types.js` 파일이 존재하지 않는다.

DESIGN.md 통합 계약 8.1에서도 "공유 타입 정의 | `nugget/src/shared/types.js`" 를 명시하고 있다.

**실패 시나리오:**
Chrome이 확장 프로그램을 로드할 때 `types.js`를 찾을 수 없어 content script 전체가 로드에 실패한다. 이는 Claude, ChatGPT, Gemini 모든 플랫폼에서 대화 감지 기능이 완전히 중단됨을 의미한다.

**심각도: CRITICAL** -- 확장 프로그램의 핵심 기능(자동 저장)이 전혀 동작하지 않음.

### FAIL-06: [background.js:15] importScripts 경로 오류 가능성

**문제:**
```js
importScripts('src/lib/ExtPay.js');
```

Service Worker의 `importScripts` 경로는 Service Worker 파일 자체의 위치가 아닌, 확장 프로그램 루트를 기준으로 한다. manifest.json에서 Service Worker 경로가 `src/background/background.js`이므로 이 상대 경로는 `nugget/src/lib/ExtPay.js`가 아닌 `nugget/src/background/src/lib/ExtPay.js`를 찾게 된다.

**그러나** MV3 Service Worker의 importScripts는 확장 루트 기준이므로, `src/lib/ExtPay.js`는 올바른 경로이다 (확장 루트 = `nugget/`). 이 부분은 MV3 스펙상 정상이다.

**판정: 재검토 결과 PASS.** (MV3에서 importScripts는 확장 루트 기준)

### FAIL-07: [background.js:139-201] utils.js와 background.js 유틸 함수 동기화 위험

**문제:**
background.js에 `_isCJK`, `_generateHash`, `_classifyJunk`, `_autoTag`, `_entryToMarkdown` 함수가 인라인으로 복제되어 있다. 주석에 `@confidence: low — utils.js와 동기화 유지 필요`라고 표기.

utils.js는 Content Script에 주입되고, background.js는 Service Worker에서 실행된다. 두 파일의 함수 로직이 현재는 동일하지만, 한쪽만 수정하면 다른 쪽과 동기가 깨진다.

**현재 상태에서는 동일하므로 PASS이지만, 유지보수 위험으로 기록.**

---

## 4. 함수별 실패 입력 공격 결과

### 4.1 isCJK(text) / _isCJK(text)

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `null` | false | utils.js: false (typeof 체크), bg: **regex throws** | **FAIL** |
| `undefined` | false | utils.js: false, bg: **regex throws** | **FAIL** |
| `123` (number) | false | utils.js: false (typeof 체크), bg: **regex throws** | **FAIL** |
| `""` | false | false | PASS |
| `"hello"` | false | false | PASS |
| `"안녕"` | true | true | PASS |

**FAIL-08: [background.js:147] `_isCJK` null/undefined/number 입력 시 crash**

utils.js의 `isCJK`는 `typeof text !== 'string'` 가드가 있지만, background.js의 `_isCJK`에는 이 가드가 없다:
```js
function _isCJK(text) {
  return /[\u3000-\u9FFF\uAC00-\uD7AF]/.test(text);  // null이면 "null" 문자열로 변환되어 false
}
```
실제로 JavaScript의 `RegExp.test(null)`은 `"null"`을 테스트하므로 crash하지 않고 false를 반환한다. 따라서 **재판정: PASS** (암묵적 형변환으로 정상 동작). 하지만 명시적 가드가 없어 의도된 동작인지 불명확하다.

### 4.2 classifyJunk(question, answer, keywords) / _classifyJunk

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `(null, null, [])` | false | utils.js: false (typeof 체크), bg: false (|| fallback) | PASS |
| `("", "", [])` | true (빈문자열=짧음) | true (q.length=0 < 15 AND a.length=0 < 200) | PASS |
| `("hi", "This is a response", [])` | true (3글자 < 5단어) | true | PASS |
| `("hello", "x".repeat(200), [])` | false (답변=200자, <200 아님) | false | PASS |
| `("hello", "x".repeat(199), [])` | true | true | PASS |
| `("안녕하세요 오늘 날씨가 좋네요 어떻게 생각하세요", "짧은 답변", [])` | false (15자 이상) | CJK 감지 → q.length=21 >= 15 → 1단계 false → 2단계 키워드 없음 → false | PASS |
| `("hello", "short", ["hello"])` | true (키워드 매치) | true | PASS |
| `("HELLO", "short", ["hello"])` | true (대소문자 무시) | true | PASS |

### 4.3 autoTag(question, answer) / _autoTag

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `(null, null)` | ["기타"] | ["기타"] (|| fallback) | PASS |
| `("", "")` | ["기타"] | ["기타"] | PASS |
| `("python code", "function")` | ["코딩"] | ["코딩"] ('code' + 'function' 매치) | PASS |
| `("글을 써줘", "에세이를 작성해보겠습니다")` | ["글쓰기"] | ["글쓰기"] ('글' 매치) | PASS |
| `("코드 설명해줘", "이 함수의 개념은")` | ["코딩", "학습"] | ["코딩", "학습"] ('코드'+'함수'='코딩', '설명'+'개념'='학습') | PASS |

**잠재적 문제:** '글' 키워드가 너무 일반적이다. "프로그래밍 글로벌 변수"라는 질문에서 '글'이 매칭되어 "글쓰기" 태그가 잘못 부여된다. '시'도 마찬가지 ("시간", "시작", "시스템"에 모두 매칭). 이는 DESIGN.md 6.3에서 "부분 문자열 포함"으로 명시한 설계이므로 코드는 올바르지만, 태깅 정확도에 영향. **보고 등급: WARN.**

### 4.4 generateHash(question, answer, dateString) / _generateHash

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `(null, null, null)` | 유효한 해시 | utils.js: "5381" (빈 입력 해싱), bg: "5381" | PASS |
| `("q", "a", "2026-01-01")` | 결정적 해시 | 동일 입력 → 동일 출력 (결정적) | PASS |
| `("q", "a", "2026-01-01")` vs `("q", "a", "2026-01-02")` | 다른 해시 | 다름 (날짜 포함) | PASS |

**잠재적 문제:** djb2 해시는 32비트 정수 해시로 충돌 가능성이 존재한다. 500개 엔트리에서 생일 문제(Birthday Problem) 확률은 극히 낮지만 (약 0.003%), 대량 데이터에서는 중복 방지가 깨질 수 있다. **보고 등급: INFO (이론적 극단 케이스).**

### 4.5 entryToMarkdown(entry) / _entryToMarkdown

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `null` | "" | "" | PASS |
| `{}` | 빈 마크다운 | `## \n\n> **플랫폼:** ...` (빈 필드 구조만) | PASS |
| `{ question: "<script>alert(1)</script>" }` | XSS 안전 | 마크다운 파일로 출력되므로 HTML 이스케이프 불필요 | PASS |
| `{ note: "line1\nline2" }` | 블록쿼트 각 줄 | `> line1\n> line2` | PASS |

### 4.6 buildHighlightRegex(query)

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `""` | 매칭 안 되는 regex | `/(?!)/` | PASS |
| `null` | 매칭 안 되는 regex | `/(?!)/` (typeof 체크) | PASS |
| `"(test)"` | 이스케이프된 regex | `/\(test\)/gi` | PASS |
| `"$100"` | 이스케이프된 regex | `/\$100/gi` | PASS |

### 4.7 saveEntry(data)

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `null` | error | `{ success: false, error: '유효하지 않은 데이터' }` | PASS |
| `{ question: "" }` | error | `{ success: false, error: '필수 필드 누락' }` | PASS |
| `{ question: "q", answer: "a", platform: "unknown" }` | error | `{ success: false, error: '알 수 없는 플랫폼: unknown' }` | PASS |
| `{ question: "q", answer: "a", platform: "claude" }` | 성공 | sourceUrl이 undefined → `sourceUrl || ''` = "" | PASS |

### 4.8 updateNote(entryId, note)

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `("", "note")` | error | `{ success: false, error: 'entryId 누락' }` | PASS |
| `("id", 123)` | error | `{ success: false, error: 'note는 문자열이어야 합니다' }` | PASS |
| `("id", "x".repeat(201))` (무료) | error | 200자 초과 에러 반환 | PASS |
| `("nonexistent", "note")` | error | `{ success: false, error: '엔트리를 찾을 수 없습니다' }` | PASS |

### 4.9 enforceFreeLimits(entries, isPro)

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `(null, false)` | [] | [] | PASS |
| `([], false)` | [] | [] | PASS |
| `(501개 엔트리, false)` | 1개 archived | 가장 오래된 1개 archived:true | PASS |
| `(501개 엔트리, true)` | 0개 archived | 전부 archived:false | PASS |

### 4.10 UPDATE_SETTINGS 메시지 핸들러

| 입력 | 예상 | 실제 | 판정 |
|---|---|---|:---:|
| `{ key: "isPro", value: true }` | 설정 변경 | **설정이 변경됨** | **FAIL** |

**FAIL-09: [background.js:891-900] 보안: UPDATE_SETTINGS로 isPro를 직접 변경 가능**

```js
case 'UPDATE_SETTINGS': {
  const settings = await loadSettings();
  settings[payload.key] = payload.value;  // 어떤 키든 변경 가능
  await storageSet({ [STORAGE_KEYS.SETTINGS]: settings });
  sendResponse({ success: true });
  break;
}
```

Popup/Options에서 `{ key: "isPro", value: true }` 메시지를 보내면 Pro 상태를 우회할 수 있다. 실제로 popup.js나 options.js에서 이런 메시지를 보내지는 않지만, Chrome DevTools 콘솔에서 `chrome.runtime.sendMessage({ type: 'UPDATE_SETTINGS', payload: { key: 'isPro', value: true } })` 을 실행하면 Pro를 무료로 활성화할 수 있다.

또한 `maxFreeEntries`를 99999로 변경하거나, `mdCopyCount`를 0으로 리셋하는 것도 가능하다.

**심각도: HIGH** -- 결제 우회 취약점.

> 수정 방안: `UPDATE_SETTINGS`에서 변경 가능한 키를 화이트리스트로 제한. (`toastEnabled`, `junkFilterEnabled`만 허용.)

---

## 5. FREEZE 보고 (설계 변경 필요)

### FREEZE-01: types.js 파일 누락 (FAIL-05)

`nugget/src/shared/types.js` 파일이 존재하지 않아 모든 Content Script가 로드에 실패한다. 이 파일을 생성하지 않으면 확장 프로그램의 핵심 기능(자동 저장)이 전혀 동작하지 않는다.

**필요 조치:** types.js 파일을 빈 파일이라도 생성하거나, manifest.json에서 types.js 참조를 제거해야 함. 통합 계약 변경이 필요하므로 FREEZE.

---

## 6. 이슈 요약

### CRITICAL (확장 프로그램이 동작하지 않는 문제)

| ID | 파일:라인 | AC | 설명 |
|---|---|---|---|
| FAIL-05 / FREEZE-01 | manifest.json:41 | 전체 | `types.js` 파일 누락으로 Content Script 전체 로드 실패. 자동 저장 불가. |

### HIGH (핵심 기능 오동작 또는 보안 문제)

| ID | 파일:라인 | AC | 설명 |
|---|---|---|---|
| FAIL-02 | popup.js:250-261, background.js:452-490 | AC-10 | 기간 필터(오늘/이번주/이번달)가 Backend에서 처리되지 않음. 플랫폼 필터 필드명 불일치(`platforms` vs `platform`). |
| FAIL-03 | claude.js:158, chatgpt.js:140, gemini.js:139 | AC-19 | 토스트 알림 설정(toastEnabled)이 Content Script에서 확인되지 않음. |
| FAIL-09 | background.js:891-900 | AC-22 | UPDATE_SETTINGS로 isPro를 직접 변경 가능한 결제 우회 취약점. |

### MEDIUM (기능 제한 또는 엣지 케이스)

| ID | 파일:라인 | AC | 설명 |
|---|---|---|---|
| FAIL-01 | claude.js:141, chatgpt.js:124, gemini.js:127 | AC-1 | 답변 50자 미만 대화가 저장되지 않음 (스트리밍 가드가 짧은 답변도 차단). |
| FAIL-04 | background.js:236-259 | AC-23 | 무료 사용자에서 active 엔트리가 줄어도 archived가 해제되지 않음. |

### WARN (동작하지만 주의 필요)

| ID | 파일 | 설명 |
|---|---|---|
| WARN-01 | utils.js, background.js | autoTag의 '글', '시' 키워드가 너무 일반적이어서 오탐 가능성. |
| WARN-02 | background.js:139-201 | utils.js와 background.js에 동일 로직 이중 구현. 동기화 깨질 위험. |
| WARN-03 | popup.js:809-823 | checkCapacityBanner()에서 `{ filters: { includeArchived: true } }` 필터를 보내지만, background.js의 applyFilters()는 `includeArchived` 필터를 처리하지 않음. archived 엔트리는 항상 제외되므로 정확한 activeCount 계산이 되지 않음. |

### INFO (이론적 극단 케이스, 보고만)

| ID | 파일 | 설명 |
|---|---|---|
| INFO-01 | utils.js | djb2 해시 32비트 충돌 가능성 (대량 데이터에서 극미한 확률). |
| INFO-02 | selectors.js | 모든 셀렉터가 @confidence: low. AI 사이트 DOM 변경 시 즉시 깨짐. |
| INFO-03 | background.js | EXPORT_PDF 핸들러가 Pro 체크만 하고 실제 PDF 생성 로직이 없음 (Frontend에서 처리 예정이라는 주석은 있으나 미구현). |

---

## 7. 최종 판정

| 카테고리 | PASS | FAIL | 합계 |
|---|:---:|:---:|:---:|
| AC (30개) | 25 | 5 | 30 |
| 통합 계약 파일 | 20/21 | 1 (types.js) | 21 |
| 메시지 타입 | 22/22 | 0 | 22 |
| Storage 키 | 6/6 | 0 | 6 |

**총 판정: FAIL (CRITICAL 1건 + HIGH 3건 미해결)**

CRITICAL 이슈(types.js 누락)가 해결되지 않으면 확장 프로그램이 동작하지 않습니다.
HIGH 이슈(기간 필터, 토스트 설정, 결제 우회)는 핵심 기능 및 보안에 직접적인 영향을 미칩니다.

---

*QA Report 끝*

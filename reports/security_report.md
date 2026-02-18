# Nugget -- AI Chat Memory: 보안 검증 보고서

**검증일:** 2026-02-18
**검증 대상:** `nugget/src/` 전체 (Manifest V3 Chrome Extension)
**검증관:** 보안 & 품질 보증관 (Agent #6)

---

## 요약

| 분류 | 건수 |
|------|:---:|
| FAIL (수정 필수) | 4 |
| WARN (권장 수정) | 5 |
| FREEZE (설계 변경 필요) | 0 |
| PASS | 다수 |

전체적으로 CSP 준수, eval 미사용, 인라인 스크립트 미사용 등 MV3 보안 기본기는 잘 지켜져 있습니다.
주요 문제는 **innerHTML을 통한 XSS 취약점**, **UPDATE_SETTINGS 메시지의 키 검증 부재**, **Pro 상태 로컬 우회 가능성**입니다.

---

## 1. CSP 준수

### 1.1 manifest.json content_security_policy

**파일:** `/home/user/makeanything/nugget/manifest.json` (60~62행)

```json
"content_security_policy": {
  "extension_pages": "script-src 'self'; object-src 'self'; connect-src 'self' https://extensionpay.com"
}
```

- `script-src 'self'` -- 인라인 스크립트 차단, 외부 스크립트 차단. **적절함.**
- `object-src 'self'` -- Flash/Java 등 플러그인 차단. **적절함.**
- `connect-src` -- ExtensionPay 도메인만 허용. AC-30 충족. **적절함.**

**결과: PASS**

### 1.2 인라인 스크립트 사용 여부

모든 HTML 파일(popup.html, options.html, onboarding.html)에서 인라인 스크립트(`<script>` 태그 내 코드, `onclick` 등 인라인 핸들러) 사용이 없음을 확인했습니다. 모두 별도 `.js` 파일을 `<script src="...">` 형태로 로드합니다.

**결과: PASS** (AC-29 충족)

### 1.3 eval() 사용 여부

`nugget/src/` 전체에서 `eval()` 사용 없음 확인.

**결과: PASS**

---

## 2. 권한 최소화

**파일:** `/home/user/makeanything/nugget/manifest.json` (6~10행)

```json
"permissions": [
  "storage",
  "unlimitedStorage",
  "activeTab"
]
```

| 권한 | 필요성 | 판정 |
|------|--------|------|
| `storage` | chrome.storage.local 사용 (핵심 기능) | 필수 |
| `unlimitedStorage` | 대화 데이터 10MB 초과 가능성 (AC-27, Pre-mortem 2) | 필수 |
| `activeTab` | 단축키(Ctrl+Shift+S) 토스트 표시를 위해 활성 탭에 메시지 전송 | 필수 |

과도한 권한(`tabs`, `history`, `webRequest`, `<all_urls>` 등) 없음.
content_scripts의 `matches`도 AI 사이트 3개 + extensionpay.com으로 최소 범위.

**결과: PASS**

---

## 3. 입력 검증 / XSS 방어

### 3.1 [FAIL-01] popup.js createCard() -- innerHTML에 부분적 이스케이프 누락

**파일:** `/home/user/makeanything/nugget/src/popup/popup.js` (287~367행)

`createCard()` 함수에서 `card.innerHTML = ...` 를 사용합니다. `question`과 `answer`는 `escapeHtml()` 후 `highlightText()`를 거치므로 처리가 됩니다.

그러나 **`highlightText()` 함수에 XSS 취약점**이 있습니다:

```javascript
// popup.js 1030~1036행
function highlightText(html, query) {
  if (!query || !query.trim()) return html;
  const escaped = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return html.replace(regex, '<mark class="highlight">$1</mark>');
}
```

이 함수는 이미 이스케이프된 HTML 문자열(`&amp;`, `&lt;` 등)에 대해 정규식 치환을 수행합니다.
만약 사용자가 검색어에 `&amp;` 같은 문자열을 입력하면, 이스케이프된 엔티티 중간에 `<mark>` 태그가 삽입되어 엔티티가 깨질 수 있습니다.

예: 원본에 `<script>`가 있으면 `&lt;script&gt;`로 이스케이프됨.
검색어 `lt`를 입력하면 `&<mark>lt</mark>;script&gt;`가 되어 `&lt;`가 깨집니다.

이것 자체가 직접적인 스크립트 실행으로 이어지지는 않지만(CSP가 인라인 스크립트를 차단하므로), **HTML 구조 손상**과 **잠재적 DOM 조작 취약점**이 됩니다.

**심각도:** FAIL
**수정 방안:** `highlightText()`가 HTML 엔티티를 인식하도록 수정하거나, DOM API(`createTextNode` + `<mark>` 요소)로 안전하게 하이라이팅 처리. 또는 일반 텍스트 상태에서 하이라이팅한 후 innerHTML에 삽입.

### 3.2 [FAIL-02] popup.js createCard() -- entry.sourceUrl이 escapeAttr로만 처리됨

**파일:** `/home/user/makeanything/nugget/src/popup/popup.js` (353~354행)

```javascript
${entry.sourceUrl ? `<a class="card__source" href="${escapeAttr(entry.sourceUrl)}" target="_blank"
     title="${escapeAttr(entry.sourceUrl)}" rel="noopener noreferrer">원본</a>` : ''}
```

`escapeAttr()`은 `"` 와 `'`만 이스케이프합니다:

```javascript
function escapeAttr(str) {
  if (!str) return '';
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
```

`sourceUrl`은 Content Script에서 `window.location.href`로 수집되므로 정상적인 경우 AI 사이트 URL입니다. 그러나 **JSON 백업 복원 경로**로 악의적 데이터가 유입될 수 있습니다.

만약 복원된 데이터에 `sourceUrl: "javascript:alert(1)"` 이 포함되면, `escapeAttr`은 이를 통과시킵니다. 사용자가 "원본" 링크를 클릭하면 `javascript:` URL이 실행됩니다.

MV3 CSP는 extension page에서 `javascript:` URI를 차단하지만, 이는 **방어 계층을 CSP에만 의존하는 것**이므로 코드 수준에서도 검증이 필요합니다.

**심각도:** FAIL
**수정 방안:**
1. `sourceUrl`에 프로토콜 검증 추가: `https://`로 시작하는 URL만 허용
2. `importJSON()` 에서 `entry.sourceUrl`을 URL 형식 검증 (allowlist: `https://claude.ai`, `https://chatgpt.com`, `https://chat.openai.com`, `https://gemini.google.com`)

### 3.3 [WARN-01] popup.js renderTagsHtml() -- CSS 클래스에 사용자 입력 삽입

**파일:** `/home/user/makeanything/nugget/src/popup/popup.js` (1058~1065행)

```javascript
function renderTagsHtml(tags) {
  if (!tags || tags.length === 0) return '';
  return tags.map(tag => {
    const safeTag = escapeHtml(tag);
    const cls = tag.replace(/[^가-힣a-zA-Z0-9]/g, '') || 'other';
    return `<span class="tag-chip tag-chip--${safeTag}">${safeTag}</span>`;
  }).join('');
}
```

`safeTag`는 `escapeHtml()` 처리되었지만 **CSS 클래스명에 삽입**됩니다. `escapeHtml`의 결과에 `&amp;` 등의 엔티티가 포함되면 유효하지 않은 클래스명이 됩니다. 직접적 보안 위협은 아니지만, 예측 불가한 CSS 선택자 동작을 유발할 수 있습니다.

또한 `cls` 변수(정규식으로 필터링된 값)를 클래스명에 사용하는 게 아니라 `safeTag`를 사용하고 있어, 필터링 로직과 실제 삽입 로직이 불일치합니다.

**심각도:** WARN
**수정 방안:** 클래스명에는 `cls` 변수를 사용: `tag-chip--${cls}`

### 3.4 메모 입력 (AC-14)

`handleNoteSave()`는 textarea의 `.value`를 사용하며 이는 순수 텍스트입니다. `sendMsg()`로 Background에 전달되고 `chrome.storage`에 저장됩니다. 렌더링 시 `escapeHtml(entry.note || '')`로 이스케이프 후 `<textarea>` 내부에 삽입됩니다.

**결과: PASS**

### 3.5 검색어 입력 (AC-10)

검색어는 `state.searchQuery`에 저장되어 Background에 `payload.query`로 전달됩니다. Background의 `searchEntries()`는 `toLowerCase().includes()`로 검색하며 DOM에 삽입하지 않습니다. Popup에서의 하이라이팅은 3.1에서 별도 언급.

**결과: PASS** (3.1의 하이라이팅 문제 제외)

### 3.6 잡담 키워드 입력 (AC-6)

Options에서 키워드를 추가할 때 `els.keywordInput.value.trim().toLowerCase()`로 정규화합니다. Background의 `UPDATE_JUNK_KEYWORDS` 핸들러에서 `payload.keywords.filter(k => typeof k === 'string' && k.trim().length > 0)`으로 검증합니다. 렌더링 시 `text.textContent = keyword`로 순수 텍스트 삽입합니다.

**결과: PASS**

---

## 4. 저장 보안

### 4.1 민감 정보 평문 저장

`chrome.storage.local`에 저장되는 데이터:
- `nugget_entries`: 대화 내용 (질문, 답변, 메모, URL)
- `nugget_settings`: 설정값 (isPro, mdCopyCount 등)
- `nugget_pro_cache`: Pro 결제 상태 캐시 (paid, checkedAt)
- `nugget_junk_keywords`: 잡담 키워드 목록

API 키, 비밀번호, 인증 토큰 등 민감 정보는 저장하지 않습니다.
ExtensionPay는 Extension ID만으로 동작하며 API 키가 불필요합니다 (.plan.md 기술적 제약사항).

대화 내용 자체는 사용자의 개인 데이터이지만, 완전 로컬 저장이며 외부로 전송하지 않습니다.

**결과: PASS**

### 4.2 [WARN-02] Pro 캐시의 무결성

**파일:** `/home/user/makeanything/nugget/src/background/background.js` (583~625행)

`nugget_pro_cache`에 `{ paid: true/false, checkedAt: "..." }`가 평문으로 저장됩니다. 이 값은 `checkProStatus()`에서 캐시로 사용되며, 7일간 유효합니다.

기술적으로 사용자가 DevTools Console에서 `chrome.storage.local.set({ nugget_pro_cache: { paid: true, checkedAt: new Date().toISOString() } })` 를 실행하면 Pro 기능을 우회할 수 있습니다. 이 문제는 5.1에서 더 상세히 다룹니다.

**심각도:** WARN (5.1 참조)

---

## 5. 결제 보안 (ExtensionPay)

### 5.1 [FAIL-03] Pro 상태 로컬 우회 가능성

**파일:** `/home/user/makeanything/nugget/src/background/background.js`

Pro 기능 게이팅이 **로컬 설정값(`settings.isPro`)** 에만 의존합니다:

1. **MD 복사 한도 (AC-13):** `checkAndIncrementMdCopy()` -- `settings.isPro`로 무제한 여부 확인 (267행)
2. **커스텀 태그 (AC-9):** `addCustomTag()` -- `settings.isPro`로 Pro 전용 확인 (761행)
3. **Markdown 파일 내보내기:** `EXPORT_MARKDOWN_FILE` 핸들러 -- `settings.isPro` 확인 (962행)
4. **PDF 내보내기:** `EXPORT_PDF` 핸들러 -- `settings.isPro` 확인 (977행)
5. **아카이브 해제:** `enforceFreeLimits()` -- `isPro`로 무제한 저장 확인 (239행)

사용자가 DevTools에서 `chrome.storage.local`의 `nugget_settings.isPro = true`로 변경하면 모든 Pro 기능을 무료로 사용할 수 있습니다.

**그러나:** 이는 Chrome Extension + ExtensionPay 아키텍처의 근본적 한계입니다. 로컬 전용 앱에서 서버 없이 결제를 완벽하게 보호하는 것은 불가능합니다. ExtensionPay 자체도 `getUser()` API를 통해 서버 측 검증을 제공하며, 이미 구현되어 있습니다 (`checkProStatus()`).

현재 구현의 완화 조치:
- `checkProStatus()`가 온라인 시 ExtensionPay 서버에서 실제 결제 상태를 확인
- 캐시 유효 기간 7일 (무한정 우회 불가)
- `@risk: 결제` 태그가 관련 코드에 적절히 부여됨

**심각도:** FAIL -- 하지만 설계를 바꿔야 하는 문제는 아님 (서버 추가 없이 코드 변경으로 개선 가능)
**수정 방안:**
1. Pro 기능 실행 시 `settings.isPro`만 확인하지 말고 `checkProStatus()`를 호출하여 서버 측 검증을 병행
2. 최소한 `EXPORT_MARKDOWN_FILE`, `EXPORT_PDF`, `addCustomTag` 같은 핵심 Pro 기능에서는 `checkProStatus()`로 실시간 검증
3. 7일 캐시를 더 짧게 (예: 24시간) 설정하는 것도 고려

### 5.2 @risk 태그 부여 현황

| 위치 | @risk 태그 | 판정 |
|------|-----------|------|
| background.js 13행 | `@risk: 결제` | OK |
| background.js 18행 | `@risk: 결제 exception_policy: fail-open` | OK |
| background.js 581행 | `@risk: 결제 exception_policy: fail-open` | OK |
| background.js 602행 | `@risk: 결제` | OK |
| background.js 632행 | `@risk: 결제 exception_policy: fail-open` | OK |
| background.js 904행 | `@risk: 결제 exception_policy: fail-open` | OK |
| background.js 911행 | `@risk: 결제 exception_policy: fail-open` | OK |
| background.js 959행 | `@risk: 결제` (fail-closed) | OK |
| background.js 975행 | `@risk: 결제` (fail-closed) | OK |
| background.js 988행 | `@risk: 결제 exception_policy: fail-open` | OK |
| extpay-content.js 18행 | `@risk: 결제` | OK |
| popup.js 496행, 938행 | `@risk: md-copy-limit`, `@risk: payment` | OK |
| options.js 415행 | `@risk: payment` | OK |

**결과: PASS** -- @risk 태그가 결제 관련 코드에 빠짐없이 적절하게 부여됨

### 5.3 ExtensionPay fail-open / fail-closed 정책

- **fail-open 적용 (적절):** `startBackground()`, `getUser()`, `_refreshProCacheInBackground()`, `OPEN_PAYMENT_PAGE`, `PRO_STATUS_CHANGED` -- 실패 시 무료 기능은 계속 동작
- **fail-closed 적용 (적절):** `EXPORT_MARKDOWN_FILE`, `EXPORT_PDF` -- Pro 미검증 시 기능 거부

**결과: PASS**

---

## 6. 통신 보안 (메시지 검증)

### 6.1 [FAIL-04] UPDATE_SETTINGS 메시지 -- 임의 키 삽입 가능

**파일:** `/home/user/makeanything/nugget/src/background/background.js` (891~900행)

```javascript
case 'UPDATE_SETTINGS': {
  if (!payload || !payload.key) {
    sendResponse({ success: false, error: 'key 누락' });
    break;
  }
  const settings = await loadSettings();
  settings[payload.key] = payload.value;
  await storageSet({ [STORAGE_KEYS.SETTINGS]: settings });
  sendResponse({ success: true });
  break;
}
```

`payload.key`에 대한 **허용 목록(allowlist) 검증이 없습니다.** 어떤 키든 설정 객체에 삽입할 수 있습니다.

악의적 Content Script나 브라우저 확장이 `chrome.runtime.sendMessage()`를 호출할 수는 없지만(같은 Extension ID만 가능), 잠재적으로:
- `payload.key = 'isPro'`, `payload.value = true` 로 Pro 상태를 직접 변경 가능
- `payload.key = '__proto__'` 로 프로토타입 오염(Prototype Pollution) 공격 가능

**심각도:** FAIL
**수정 방안:**
```javascript
const ALLOWED_SETTINGS_KEYS = ['toastEnabled', 'junkFilterEnabled', 'shortcutKey'];

case 'UPDATE_SETTINGS': {
  if (!payload || !payload.key || !ALLOWED_SETTINGS_KEYS.includes(payload.key)) {
    sendResponse({ success: false, error: '허용되지 않은 설정 키' });
    break;
  }
  // ...
}
```

### 6.2 Content Script <-> Background 메시지 구조 검증

**파일:** `/home/user/makeanything/nugget/src/background/background.js` (785~789행)

```javascript
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || !message.type) {
    sendResponse({ success: false, error: '유효하지 않은 메시지 형식' });
    return false;
  }
```

기본적인 메시지 형식 검증(type 필드 존재 확인)은 구현되어 있습니다.
각 메시지 핸들러에서 payload 필드별 검증도 대부분 수행합니다.

**그러나:** `sender` 검증이 없습니다. MV3에서 `chrome.runtime.onMessage`는 같은 Extension의 메시지만 수신하므로 외부 Extension에서의 메시지 주입은 불가능합니다. Content Script의 메시지도 Extension 고유의 채널을 통하므로 웹 페이지에서 직접 `chrome.runtime.sendMessage()`를 호출할 수 없습니다.

**결과: PASS** -- MV3의 메시지 채널 격리로 충분히 보호됨

### 6.3 [WARN-03] SAVE_ENTRY의 platform 검증은 있으나 question/answer 길이 제한 없음

**파일:** `/home/user/makeanything/nugget/src/background/background.js` (335~347행)

```javascript
if (!['claude', 'chatgpt', 'gemini'].includes(platform)) {
  return { success: false, error: `알 수 없는 플랫폼: ${platform}` };
}
```

platform 검증은 훌륭합니다. 그러나 `question`과 `answer`에 길이 제한이 없습니다. AI의 답변은 수만 자가 될 수 있으며, 이것이 그대로 storage에 저장됩니다.

직접적 보안 위협은 아니지만, 극단적으로 긴 답변이 반복 저장되면 storage 사용량이 급증할 수 있습니다.

**심각도:** WARN
**수정 방안:** `answer`에 합리적 최대 길이 설정 (예: 100,000자) 또는 초과분 트림

---

## 7. DOM 조작 안전성 (Content Script)

### 7.1 토스트 UI -- XSS 안전

**파일:** `/home/user/makeanything/nugget/src/content/claude.js` (33~73행) (chatgpt.js, gemini.js 동일 패턴)

```javascript
function showToast(message) {
  const toast = document.createElement('div');
  toast.id = 'nugget-toast';
  toast.textContent = message;  // textContent 사용 -- XSS 안전
  // ...
}
```

`textContent`를 사용하므로 HTML 해석 없이 순수 텍스트로 삽입됩니다.

**결과: PASS**

### 7.2 SHOW_TOAST 메시지 수신 -- 메시지 출처 검증

**파일:** `/home/user/makeanything/nugget/src/content/claude.js` (172~177행)

```javascript
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === 'SHOW_TOAST' && message.payload) {
    showToast(message.payload.message);
  }
});
```

`chrome.runtime.onMessage`는 같은 Extension 내부 메시지만 수신합니다. 외부 웹 페이지에서 이 리스너를 트리거할 수 없습니다. `showToast()`는 `textContent`를 사용하므로 메시지 내용이 악의적이더라도 XSS는 불가능합니다.

**결과: PASS**

### 7.3 [WARN-04] Content Script가 AI 사이트에 주입하는 요소의 z-index

```javascript
zIndex: '2147483647',  // 최대 z-index
```

최대 z-index 사용은 AI 사이트의 UI 요소와 충돌할 수 있습니다. 보안 문제는 아니지만 사용자 경험에 영향을 줄 수 있습니다.

**심각도:** WARN (보안과 무관, UX 참고사항)

---

## 8. 에러 처리

### 8.1 에러 메시지의 내부 정보 노출

**파일:** `/home/user/makeanything/nugget/src/background/background.js`

```javascript
// 1019행
} catch (err) {
  console.error(`[Nugget] 메시지 처리 오류 (${type}):`, err);
  sendResponse({ success: false, error: err.message });
}
```

에러 메시지(`err.message`)가 응답에 포함됩니다. 이 응답은 Popup이나 Content Script에서 수신하며, 사용자에게 직접 표시되지는 않습니다(Popup/Options에서는 "실패" 메시지만 표시).

`console.error`로 스택 트레이스가 DevTools에 출력되지만, 이는 Chrome Extension의 Background DevTools에서만 볼 수 있으므로 일반 사용자에게 노출되지 않습니다.

**결과: PASS** -- 에러 메시지가 사용자 UI에 직접 노출되지 않음

### 8.2 [WARN-05] console.error에 상세 에러 로깅

여러 곳에서 `console.error('[Nugget]...', err)`로 전체 에러 객체를 로깅합니다. 개발 중에는 유용하지만, 프로덕션에서는 불필요한 정보를 남길 수 있습니다.

**심각도:** WARN
**수정 방안:** 프로덕션 빌드 시 `console.debug` 제거 또는 로그 레벨 제어 추가. 현재는 번들러가 없으므로 수동 관리 필요.

---

## 추가 발견 사항

### A.1 importJSON의 입력 검증

**파일:** `/home/user/makeanything/nugget/src/background/background.js` (673~709행)

`importJSON()`에서 각 엔트리의 기본 필드(`id`, `question`, `answer`, `platform`)만 확인합니다. 악의적 백업 파일에 의도적으로 조작된 `tags`, `note`, `sourceUrl` 등이 포함될 수 있습니다. `sourceUrl` 문제는 3.2에서 다뤘으며, `tags`에 HTML이 포함되면 3.3의 문제와 연결됩니다.

### A.2 MV3 Service Worker 생명주기 준수

Background Service Worker에서 메모리 변수에 상태를 보관하지 않고 `chrome.storage`만 사용합니다(AC-28). `const processedElements = new WeakSet()`는 Content Script에서만 사용되며 Service Worker와 무관합니다.

**결과: PASS**

### A.3 ExtPay MV3 재선언 패턴

Background에서 `checkProStatus()`와 `_refreshProCacheInBackground()`에서 `const extpayInner = ExtPay('nugget-ai-chat-memory')`을 재선언합니다. 이는 MV3 Service Worker의 컨텍스트 손실 문제에 대한 올바른 대응입니다.

**결과: PASS**

---

## 수정 우선순위 종합

| ID | 분류 | 항목 | 위치 | 위험도 |
|----|------|------|------|--------|
| FAIL-01 | FAIL | highlightText() HTML 엔티티 깨짐 | popup.js:1030 | 중 |
| FAIL-02 | FAIL | sourceUrl javascript: URI 허용 | popup.js:353 + background.js importJSON | 중 |
| FAIL-03 | FAIL | Pro 상태 로컬 설정값만으로 게이팅 | background.js 전반 | 중 |
| FAIL-04 | FAIL | UPDATE_SETTINGS 키 allowlist 없음 | background.js:891 | 높 |
| WARN-01 | WARN | renderTagsHtml 클래스명에 safeTag 사용 | popup.js:1063 | 낮 |
| WARN-02 | WARN | Pro 캐시 평문 저장 | background.js:583 | 낮 |
| WARN-03 | WARN | question/answer 길이 제한 없음 | background.js:335 | 낮 |
| WARN-04 | WARN | z-index 최대값 사용 | content/*.js | 정보 |
| WARN-05 | WARN | 프로덕션 console.error 로깅 | 전반 | 낮 |

---

## PASS 항목 정리

| 항목 | 근거 |
|------|------|
| CSP 정책 | script-src 'self', object-src 'self', connect-src 제한적 |
| 인라인 스크립트 | 미사용 (AC-29 충족) |
| eval() | 미사용 |
| 권한 최소화 | storage, unlimitedStorage, activeTab만 사용 |
| 토스트 XSS | textContent 사용 |
| 메시지 채널 격리 | MV3 고유 격리 |
| 민감 정보 평문 저장 | 해당 없음 (API 키 등 미저장) |
| @risk 태그 | 결제 관련 코드에 적절히 부여 |
| fail-open/fail-closed | 정책 적절 |
| MV3 생명주기 | chrome.storage만 사용 (AC-28) |
| 메모 입력 XSS | escapeHtml + textarea 내부 |
| 잡담 키워드 XSS | textContent 사용 |

---

*이 보고서에서 FREEZE (설계 변경 필요) 항목은 발견되지 않았습니다.*
*모든 FAIL 항목은 코드 변경으로 해결 가능합니다.*

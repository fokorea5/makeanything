# Backend 구현 보고서

작성일: 2026-02-18
담당: Backend 개발자

---

## 구현 완료 파일 목록

| 파일 | 경로 | 상태 |
|------|------|------|
| manifest.json | `nugget/manifest.json` | 완료 |
| 공유 상수 | `nugget/src/shared/constants.js` | 완료 |
| 공유 유틸리티 | `nugget/src/shared/utils.js` | 완료 |
| DOM 셀렉터 설정 | `nugget/src/config/selectors.js` | 완료 |
| Background Service Worker | `nugget/src/background/background.js` | 완료 |
| Claude Content Script | `nugget/src/content/claude.js` | 완료 |
| ChatGPT Content Script | `nugget/src/content/chatgpt.js` | 완료 |
| Gemini Content Script | `nugget/src/content/gemini.js` | 완료 |
| ExtensionPay Content Script | `nugget/src/content/extpay-content.js` | 완료 |
| ExtPay 라이브러리 (플레이스홀더) | `nugget/src/lib/ExtPay.js` | 완료 (stub) |

---

## AC 검증 결과

### AC-1: 대화 감지 및 자동 저장
- **구현:** claude.js / chatgpt.js / gemini.js 각 플랫폼별 Content Script 구현
- **방식:** MutationObserver → debounce 1초 → 스트리밍 완료 확인 → `SAVE_ENTRY` 메시지 → background.js `saveEntry()`
- **검증:** `saveEntry()` 함수에서 platform 유효성 검사('claude'|'chatgpt'|'gemini'), question/answer 필수 필드 검사
- **상태:** 완료

### AC-2: MutationObserver + 셀렉터 분리
- **구현:** 모든 Content Script에서 `MutationObserver`로 DOM 변화 감지
- **셀렉터:** `nugget/src/config/selectors.js`의 `SELECTORS` 객체에 플랫폼별 분리
- **debounce:** `STREAMING_DEBOUNCE_MS = 1000ms` 적용
- **상태:** 완료

### AC-3: 셀렉터 실패 시 "!" 뱃지
- **구현:** Content Script에서 셀렉터 접근 실패 시 `SELECTOR_FAILED` 메시지 전송
- **Background:** `SELECTOR_FAILED` 수신 시 `chrome.action.setBadgeText({ text: '!' })` + 빨간 배경
- **상태:** 완료

### AC-4: 중복 방지 (해시)
- **구현:** `_generateHash(question, answer, dateString)` — djb2 알고리즘
- **입력:** `question.trim() + '|' + answer.trim().substring(0, 200) + '|' + dateString`
- **저장:** NuggetEntry.hash 필드에 저장, 저장 전 기존 entries에서 동일 hash 존재 여부 확인
- **상태:** 완료

### AC-5: 2단계 잡담 필터
- **구현:** `_classifyJunk(question, answer, keywords)` (background.js 인라인 + utils.js 공용)
- **1단계:** CJK → 글자 수 15 미만 AND 답변 200자 미만 → isJunk:true
- **1단계:** 영어 → 단어 수 5 미만 AND 답변 200자 미만 → isJunk:true
- **2단계:** 키워드 exact match (대소문자 무시) → isJunk:true
- **OR 관계:** 1단계 OR 2단계 중 하나라도 통과 시 잡담 (DESIGN.md 6.2 수정 반영)
- **테스트:** 실제 실행 테스트 통과
- **상태:** 완료

### AC-6: 기본 잡담 키워드 + 사용자 수정
- **구현:** `DEFAULT_JUNK_KEYWORDS` 배열 (한/영 공통 26개)
- **설치 시:** `chrome.runtime.onInstalled`에서 `nugget_junk_keywords` 초기화
- **수정:** `UPDATE_JUNK_KEYWORDS` 메시지 핸들러로 Options에서 수정 가능
- **상태:** 완료

### AC-7: 잡담 isJunk:true 마킹 (삭제 안 함)
- **구현:** `saveEntry()`에서 `isJunk: isJunk` 필드 설정 (삭제하지 않음)
- **필터:** `getEntries()`에서 기본적으로 isJunk 제외, `includeJunk:true` 필터로 노출 가능
- **상태:** 완료

### AC-8: 자동 태깅
- **구현:** `_autoTag(question, answer)` — 5개 태그 카테고리 키워드 매칭
- **태그:** 코딩/글쓰기/업무/학습/크리에이티브/기타
- **결과:** 복수 태그 가능, 매칭 없으면 ["기타"]
- **테스트:** 실제 실행 테스트 통과
- **상태:** 완료

### AC-9: 커스텀 태그 (Pro 전용)
- **구현:** `addCustomTag()` — `settings.isPro` 확인 후 처리
- **미Pro 시:** `{ success: false, limitReached: true }` 반환
- **메시지:** `ADD_CUSTOM_TAG` 핸들러 구현
- **상태:** 완료

### AC-10: 검색 & 필터
- **구현:** `getEntries(filters)` + `searchEntries(query, filters)` + `applyFilters()`
- **필터:** platform, dateFrom/dateTo, tag, starredOnly, includeJunk
- **검색:** question + answer + note 전문 검색 (toLowerCase 포함 매칭)
- **정렬:** 최신순 (date 내림차순)
- **상태:** 완료

### AC-11: 키워드 하이라이팅용 정규식
- **구현:** `buildHighlightRegex(query)` in utils.js
- **안전성:** 특수 문자 이스케이프 적용
- **빈 쿼리:** 매칭 안 되는 정규식 반환 (`/(?!)/`)
- **상태:** 완료 (Frontend에서 사용)

### AC-12: 마크다운 변환
- **구현:** `_entryToMarkdown(entry)` (background.js) + `entryToMarkdown(entry)` (utils.js)
- **형식:** 제목 → 메타정보 → 질문 → 답변 → 메모(블록쿼트) → 출처
- **테스트:** 실제 실행 테스트 통과
- **상태:** 완료

### AC-13: MD 복사 한도 (무료 월 20회)
- **구현:** `checkAndIncrementMdCopy(settings)` + `copyMarkdown(entryId)`
- **Pro:** 무제한
- **리셋:** 매월 1일 0시 UTC (`mdCopyResetDate` 비교)
- **응답:** `{ success, markdown, limitReached }`
- **테스트:** 19회→20회 허용, 20회 거부, Pro 무제한, 새 달 리셋 — 모두 통과
- **상태:** 완료

### AC-14: 메모 자동 저장
- **구현:** `updateNote(entryId, note)` + `UPDATE_NOTE` 메시지 핸들러
- **상태:** 완료 (blur 시 호출은 Frontend 담당)

### AC-15: 무료 메모 200자 제한 / Pro 무제한
- **구현:** `updateNote()`에서 `!settings.isPro && note.length > 200` 체크
- **에러:** 업그레이드 안내 메시지 반환
- **상태:** 완료

### AC-16: Ctrl+Shift+S 별표 단축키
- **구현:** `chrome.commands.onCommand.addListener` — "toggle-star" 처리
- **방식:** entries 중 date 최신 → starred 토글 → 저장 → 현재 탭에 `SHOW_TOAST` 전송
- **상태:** 완료

### AC-17: JSON 내보내기/가져오기
- **내보내기:** `exportJSON()` → `{ entries, settings, exportDate }`
- **가져오기:** `importJSON(data)` → id 중복 제거 병합 → enforceFreeLimits 적용
- **응답:** `{ success, imported, skipped }`
- **상태:** 완료

### AC-18: 백업 경고 뱃지
- **구현:** `updateBadge(entries, isPro)` — saveEntry 후 호출
- **무료:** 400개+ → 노란 "!" / 500개+ → 빨간 "!"
- **Pro:** 500 단위 마일스톤 → 초록 숫자 / 나머지 빈 뱃지
- **Pro 전용 내보내기:** `EXPORT_MARKDOWN_FILE` / `EXPORT_PDF` — isPro 체크 후 처리
- **상태:** 완료

### AC-19: 토스트 알림 (1.5~2초, 페이드)
- **구현:** 각 Content Script에 `showToast(message)` 인라인 구현
- **스타일:** 우측 하단, 어두운 배경, 페이드 인/아웃 (0.25초)
- **시간:** `TOAST_DURATION_MS = 1800ms`
- **on/off:** `SAVE_ENTRY` 응답 `success: true`일 때만 표시 (settings.toastEnabled는 Frontend에서 처리)
- **상태:** 완료

### AC-20: Today's Nugget
- **구현:** `getTodaysNugget()` + `GET_TODAYS_NUGGET` / `DISMISS_TODAYS_NUGGET` 핸들러
- **과거 오늘:** 같은 MM-DD, 다른 연도 우선
- **닫기:** `nugget_todays_nugget_dismissed`에 오늘 날짜 저장
- **상태:** 완료

### AC-21: 설치 시 온보딩
- **구현:** `chrome.runtime.onInstalled` → reason === 'install' → onboarding.html 열기
- **초기화:** entries=[], settings=default, junk_keywords=default, custom_tags=[]
- **상태:** 완료

### AC-22: ExtensionPay 연동
- **구현:** background.js 최상단 `importScripts` + `extpay.startBackground()`
- **결제 페이지:** `OPEN_PAYMENT_PAGE` → `extpay.openPaymentPage()` (MV3 재선언)
- **상태:** 완료

### AC-23: 무료 한도 (500개 초과 → archived:true)
- **구현:** `enforceFreeLimits(entries, isPro)` — saveEntry 후 + importJSON 후 적용
- **방식:** 잡담/아카이브 제외 활성 엔트리를 날짜 내림차순 후 500개 초과분 archived:true
- **삭제 안 함:** archived 엔트리는 storage에 보존
- **Pro 업그레이드:** PRO_STATUS_CHANGED 수신 시 `enforceFreeLimits(entries, true)` 적용 → 모든 archived 해제
- **테스트:** 501개 입력 → 1개 archived 확인 통과
- **상태:** 완료

### AC-23a: 백업 복원 시 아카이브 정책
- **구현:** `importJSON()` — 병합 후 `enforceFreeLimits()` 적용
- **결과:** 무료 사용자가 500개 초과 복원 시 최신 500개만 활성, 나머지 archived
- **상태:** 완료

### AC-24: 초과/잠금 시 업그레이드 안내
- **구현:** `updateNote()`, `checkAndIncrementMdCopy()`, `addCustomTag()` 각각 한도 초과 시 안내 메시지 또는 `limitReached: true` 반환
- **상태:** 완료

### AC-24a: Pro 오프라인 캐시 (7일)
- **구현:** `checkProStatus()` — 캐시 유효 기간 7일 확인
- **캐시 유효:** 온라인이면 백그라운드에서 비동기 갱신 (결과 안 기다림)
- **만료 + 오프라인:** `{ isPro: cache.paid, cached: true, expired: true }` — 기능 차단하지 않음
- **캐시 없음 + 오프라인:** `{ isPro: false, cached: false }` — 무료로 폴백
- **상태:** 완료

### AC-26: 엔트리 필드
- **구현:** `saveEntry()`에서 id, date, platform, question, answer, tags, starred, isJunk, archived, sourceUrl, note, hash 모두 생성
- **상태:** 완료

### AC-27: 설정 필드
- **구현:** `defaultSettings()` — toastEnabled, junkFilterEnabled, shortcutKey, maxFreeEntries, isPro, mdCopyCount, mdCopyResetDate
- **상태:** 완료

### AC-28: Service Worker 상태 → chrome.storage에만 저장
- **구현:** background.js에 전역 메모리 변수 없음. 모든 상태는 `storageGet()`/`storageSet()`으로 처리
- **상태:** 완료

### AC-29: CSP — 인라인 스크립트 금지
- **구현:** manifest.json에 `"extension_pages": "script-src 'self';"` 설정. 모든 JS는 별도 파일로 분리
- **상태:** 완료

### AC-30: ExtensionPay CSP
- **구현:** manifest.json `"connect-src 'self' https://extensionpay.com"` 추가
- **상태:** 완료

---

## 테스트 결과

### 구문 검사 (node --check)
| 파일 | 결과 |
|------|------|
| utils.js | PASS |
| constants.js | PASS |
| selectors.js | PASS |
| claude.js | PASS |
| chatgpt.js | PASS |
| gemini.js | PASS |
| extpay-content.js | PASS |
| ExtPay.js | PASS |
| background.js | PASS |
| manifest.json (JSON 유효성) | PASS |

### 로직 테스트 (node -e)
| 테스트 | 결과 |
|--------|------|
| isCJK() — 한글/영어/일본어/빈 문자열 | PASS |
| classifyJunk() — 1단계/2단계/긴 질문 | PASS |
| autoTag() — 코딩/업무/기타 태그 | PASS |
| generateHash() — 같은 입력/다른 입력 | PASS |
| entryToMarkdown() — 제목/답변/메모 블록쿼트 | PASS |
| buildHighlightRegex() — 매치/빈 쿼리 | PASS |
| enforceFreeLimits() — 501개, Pro 해제 | PASS |
| checkAndIncrementMdCopy() — 19회/20회/Pro/새 달 | PASS |

---

## @risk 코드 목록

| 위치 | 태그 | 전략 |
|------|------|------|
| background.js:17 | `@risk: 결제` (startBackground) | fail-open |
| background.js:244 | `@risk: 결제` (checkProStatus) | fail-open |
| background.js:252 | `@risk: 결제` (getUser) | fail-open |
| background.js:391 | `@risk: 결제` (OPEN_PAYMENT_PAGE) | fail-open |
| background.js:439 | `@risk: 결제` (PRO_STATUS_CHANGED) | fail-open |
| background.js:366 | `@risk: 결제` (EXPORT_MARKDOWN_FILE) | fail-closed |
| background.js:377 | `@risk: 결제` (EXPORT_PDF) | fail-closed |
| extpay-content.js:20 | `@risk: 결제` (onPaid 콜백) | fail-open |

---

## @confidence: low 태그 위치

| 파일 | 이유 |
|------|------|
| selectors.js 전체 | AI 사이트 DOM 구조는 수시로 변경. 배포 전 최신 DOM 확인 필수 |
| claude.js @confidence: low | claude.ai DOM 구조 변경 가능성 |
| chatgpt.js @confidence: low | chatgpt.com DOM 구조 변경 가능성 |
| gemini.js @confidence: low | gemini.google.com DOM 구조 변경 가능성 (Angular/Shadow DOM 주의) |
| background.js _isCJK 등 인라인 유틸 | utils.js와 동기화 유지 필요 |
| ExtPay.js 전체 | stub 파일. 실제 배포 전 npm extpay@3.1.2로 교체 필수 |

---

## 미구현 / 주의 사항

1. **ExtPay.js 교체 필수:** `nugget/src/lib/ExtPay.js`는 개발용 stub입니다. 배포 전 `npm install extpay@3.1.2` 후 `node_modules/extpay/dist/ExtPay.js` 내용으로 교체해야 합니다.

2. **DOM 셀렉터 검증 필요:** `selectors.js`의 셀렉터는 DESIGN.md 기준 초기 추정값입니다. 실제 배포 전 Claude, ChatGPT, Gemini 사이트의 최신 DOM을 확인하여 업데이트해야 합니다.

3. **settings.toastEnabled 체크:** Content Script에서 toast 표시 전에 설정 확인 로직이 현재는 단순화되어 있습니다 (항상 표시). 완전한 구현을 위해서는 Content Script가 Background에서 settings를 조회하거나, Background가 SAVE_ENTRY 응답에 toastEnabled 필드를 포함해야 합니다. Frontend 에이전트와 협의 필요.

4. **utils.js와 background.js 인라인 유틸 동기화:** background.js는 Service Worker 환경에서 importScripts로 utils.js를 로드하지 않고 인라인 구현을 사용합니다 (`_isCJK`, `_classifyJunk`, `_autoTag`, `_generateHash`, `_entryToMarkdown`). 향후 utils.js를 수정할 경우 background.js 인라인 구현도 함께 업데이트해야 합니다.

---

## 통합 계약 준수 확인

- [x] 파일 경로: DESIGN.md 8.1 기준 정확히 일치
- [x] 메시지 타입: DESIGN.md 8.2의 모든 타입 구현
- [x] Storage 키: DESIGN.md 8.3의 6개 키 사용 (nugget_entries, nugget_settings, nugget_junk_keywords, nugget_pro_cache, nugget_todays_nugget_dismissed, nugget_custom_tags)
- [x] 상수: DESIGN.md 8.4의 모든 상수 constants.js에 정의
- [x] 시그니처: DESIGN.md 9.1 (utils.js 6개 함수), 9.2 (background.js 11개 함수), 9.3 (selectors.js SELECTORS 객체) 준수
- [x] ExtensionPay ID: 'nugget-ai-chat-memory' 통일 사용
- [x] MV3 재선언 패턴: 콜백 내부에서 `ExtPay('nugget-ai-chat-memory')` 재선언
- [x] startBackground(): 최초 1회만 호출 (background.js 최상단)

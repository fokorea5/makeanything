# Backend v1.1 작업 보고서

작성일: 2026-02-18
담당: Backend 에이전트

---

## 완료된 작업 목록

### 1. manifest.json 수정
- 파일: `nugget/manifest.json`
- 변경: version "1.1.0", permissions에 "alarms" 추가
- MAIN world content_scripts 추가 (interceptor.js, 3개 AI 사이트, document_start)
- ISOLATED world content_scripts 추가 (bridge.js, 3개 AI 사이트, document_start)
- 기존 ISOLATED world content_scripts 유지 (claude.js, chatgpt.js, gemini.js)

### 2. interceptor.js 신규 구현
- 파일: `nugget/src/content/interceptor.js`
- MAIN world에서 window.fetch 오버라이드
- 플랫폼 판별 (claude.ai, chatgpt.com/chat.openai.com, gemini.google.com)
- API 엔드포인트 패턴 매칭 (/api/.*/completion, /backend-api/conversation, /batchexecute?)
- ReadableStream.tee()로 스트림 복제 (원본 보존)
- 플랫폼별 SSE 파서 구현:
  - parseClaudeSSE: content_block_delta 이벤트에서 delta.text 추출
  - parseChatGPTSSE: data 라인에서 message.content.parts[] 또는 delta.content 추출
  - parseGeminiResponse: JSON 배열 응답 파싱 (XSSI prefix 처리)
- 질문은 requestBody에서 messages 배열 마지막 user 메시지로 추출
- CustomEvent(API_CAPTURE_EVENT_NAME)로 bridge에 전달
- 파싱 실패 시 null 반환 → DOM 셀렉터 폴백 자동 작동

### 3. bridge.js 신규 구현
- 파일: `nugget/src/content/bridge.js`
- ISOLATED world, document_start 실행
- CustomEvent('__nugget_api_capture__') 리스너 등록
- 수신 데이터 유효성 검사 (platform, answer 필수)
- chrome.runtime.sendMessage({ type: 'API_CAPTURE', payload }) 전달
- 이 한 가지 역할만 수행 (비판자 MINOR-1 반영)

### 4. i18n.js 신규 구현
- 파일: `nugget/src/utils/i18n.js`
- resolveLanguage(): 'auto' → navigator.language 감지 → ko/en 결정 (미지원 언어 ko 폴백)
- loadTranslations(): chrome.runtime.getURL로 src/i18n/{lang}.json 로드, 캐시 지원
- t(key, params): 번역 키 → 문자열 반환, 현재 언어 → ko 폴백 → 키 자체 반환
- getCurrentLang(): 현재 언어 코드 반환
- applyI18nToDOM(): data-i18n, data-i18n-placeholder, data-i18n-title, data-i18n-aria-label 속성 일괄 적용
- initI18n(): storage에서 언어 설정 로드 → 번역 사전 로드 → DOM 적용
- changeLanguage(): Options 페이지 즉시 반영용
- onLanguageChange(): storage.onChanged 리스너로 Content Script 토스트 언어 변경 감지

### 5. theme.js 신규 구현
- 파일: `nugget/src/utils/theme.js`
- resolveTheme(): 'system' → prefers-color-scheme 감지, 'light'/'dark' 직접 반환
- applyTheme(): document.documentElement에 data-theme 속성 설정
- watchSystemTheme(): prefers-color-scheme 미디어 쿼리 리스너 등록/해제 (system 모드만)
- initTheme(): storage에서 테마 설정 로드 → resolveTheme → applyTheme → watchSystemTheme
- changeTheme(): Options 페이지 즉시 반영용
- onThemeChange(): storage.onChanged 리스너로 페이지 간 테마 동기화

### 6. background.js 수정
- STORAGE_KEYS에 REMOTE_SELECTORS, API_CAPTURE_HASHES 추가
- defaultSettings()에 language: 'auto', theme: 'system' 추가 (v1.0→v1.1 마이그레이션 자동 처리)
- _generateContentHash(): question + answer앞200자 기반 날짜 독립 해시 (중복 방지용)
- API 캡처 해시 관리 함수: loadApiCaptureHashes, recordApiCaptureHash, isDuplicateOfApiCapture
- handleApiCapture(): saveEntry() 동일 파이프라인 + content hash 기록
- validateRemoteSelectors(): 원격 셀렉터 스키마 검증 (version, 3 platforms, 4 required keys)
- fetchRemoteSelectors(): GitHub Raw URL fetch, 검증 통과 시 nugget_remote_selectors 저장
- SAVE_ENTRY 케이스: content hash 기반 API 캡처 중복 체크 추가
- API_CAPTURE 케이스: handleApiCapture() 호출
- UPDATE_SETTINGS 허용 키: language, theme 추가
- chrome.alarms.onAlarm: fetch_remote_selectors 알람 핸들러
- onInstalled: 알람 등록 (delayInMinutes: 1, periodInMinutes: 1440)
- Service Worker 시작 시 알람 존재 확인 및 재등록

### 7. Content Scripts 수정
- claude.js: SAVE_ENTRY_DEDUP_DELAY_MS(500ms) 상수 추가, sendMessage 전 500ms 지연
- chatgpt.js: 동일
- gemini.js: 동일

### 8. selectors.js 수정
- getSelectors(platform): 원격 셀렉터 우선, 없으면 로컬 SELECTORS 폴백 (async)

---

## AC 검증

### API 가로채기 (메인 캡처)

- [x] **AC-V11-1**: interceptor.js가 MAIN world, document_start에서 window.fetch 오버라이드. ReadableStream.tee()로 스트림 복제. claude.ai, chatgpt.com, gemini.google.com 지원.
  - 구현 위치: `nugget/src/content/interceptor.js`, `installFetchInterceptor()` IIFE

- [x] **AC-V11-1a**: 플랫폼별 SSE 파서 구현.
  - Claude: `parseClaudeSSE` — event: content_block_delta + data: json.delta.text 추출
  - ChatGPT: `parseChatGPTSSE` — data 라인에서 message.content.parts[] / delta.content 추출
  - Gemini: `parseGeminiResponse` — JSON 배열 파싱, XSSI prefix 처리
  - 파싱 실패(null 반환) 시 DOM 셀렉터 폴백 자동 작동

- [x] **AC-V11-2**: bridge.js가 CustomEvent 리스너로 interceptor 데이터 수신 → chrome.runtime.sendMessage({ type: 'API_CAPTURE' }) 전달. bridge.js는 이 역할만 수행.
  - 구현 위치: `nugget/src/content/bridge.js`

- [x] **AC-V11-3**: interceptor.js는 `"world": "MAIN"`, `"run_at": "document_start"`로 manifest에 등록. bridge.js는 `"run_at": "document_start"` ISOLATED world. 기존 content_scripts 유지.
  - 구현 위치: `nugget/manifest.json`

- [x] **AC-V11-4**: API 캡처 성공 시 CustomEvent 발송 → bridge → Background API_CAPTURE → 저장. 파싱 실패(question+answer 미추출) 시 null 반환 → DOM 셀렉터 폴백 자동 작동.
  - "파싱 실패" 정의: fetch 오버라이드 미실행, URL 패턴 미매칭, SSE 파싱 빈 데이터, 스트림 중단 모두 null 반환으로 처리.

- [x] **AC-V11-4a**: 중복 저장 방지 메커니즘 구현.
  - Background: API_CAPTURE 저장 성공 시 content hash (question + answer앞200자)를 nugget_api_capture_hashes에 기록
  - SAVE_ENTRY 수신 시 동일 content hash 존재 여부 확인 → 있으면 무시
  - Content Script: SAVE_ENTRY 발송 전 500ms 지연 (SAVE_ENTRY_DEDUP_DELAY_MS)
  - nugget_api_capture_hashes 최대 100개 유지 (recordApiCaptureHash slicing)

- [x] **AC-V11-5**: tee()로 스트림을 2개로 복제. stream1으로 원본 Response 재생성하여 페이지에 반환. 원본 페이지 기능에 영향 없음.
  - 구현 위치: `interceptor.js` fetch 오버라이드 로직

### 원격 셀렉터 핫패치 (백업)

- [x] **AC-V11-6**: Background에서 REMOTE_SELECTORS_URL에서 24시간 주기로 셀렉터 fetch. chrome.alarms 사용.
  - 구현 위치: `background.js`, `fetchRemoteSelectors()`, `chrome.alarms.create()`

- [x] **AC-V11-7**: 원격 셀렉터를 nugget_remote_selectors에 캐시. 오프라인 시 fetch 실패 → 기존 캐시 유지 (조용히 실패).
  - 구현 위치: `background.js`, `fetchRemoteSelectors()` catch 블록

- [x] **AC-V11-8**: getSelectors(platform)에서 nugget_remote_selectors 먼저 확인, 없으면 로컬 SELECTORS 사용.
  - 구현 위치: `selectors.js`, `getSelectors()` 함수

- [x] **AC-V11-9**: validateRemoteSelectors()가 JSON 스키마 검증. version(string), selectors(3 platforms × 4 required keys) 검증. 실패 시 로컬 유지.
  - 구현 위치: `background.js`, `validateRemoteSelectors()`

### 다국어 (i18n) — Backend 담당 부분

- [x] **AC-V11-11**: 지원 언어 ko/en, FALLBACK_LANGUAGE = 'ko'. resolveLanguage()에서 처리.
  - 구현 위치: `i18n.js`

- [x] **AC-V11-12** (Backend 부분): onLanguageChange()로 chrome.storage.onChanged 리스너 등록 → 번역 사전 재로드 → 콜백 호출. Content Script 토스트는 이 리스너로 반영.
  - 구현 위치: `i18n.js`, `onLanguageChange()`

- [x] **AC-V11-13**: resolveLanguage(): 'auto' → navigator.language 확인 → 'ko'로 시작하면 ko, 'en'으로 시작하면 en, 그 외 ko 폴백.
  - 구현 위치: `i18n.js`, `resolveLanguage()`

- [x] **AC-V11-14** (Backend 부분): i18n.js의 onLanguageChange() + t() 함수로 토스트 언어 변경 지원. Content Script에서 t('toast_saved') 호출 시 최신 언어 사용.

### 다크모드 — Backend 담당 부분

- [x] **AC-V11-16** (Backend 부분): initTheme()가 nugget_settings.theme 읽어 applyTheme() 호출. theme.js는 data-theme 속성 관리.

- [x] **AC-V11-17** (Backend 부분): defaultSettings()에 theme: 'system' 추가. UPDATE_SETTINGS에 'theme' 키 허용.
  - 구현 위치: `background.js`, `defaultSettings()`

- [x] **AC-V11-20**: watchSystemTheme()가 prefers-color-scheme 미디어 쿼리 리스너 등록. OS 변경 시 applyTheme() 자동 호출.
  - 구현 위치: `theme.js`, `watchSystemTheme()`

### v1.0→v1.1 마이그레이션

- [x] **AC-V11-21**: defaultSettings()에 language: 'auto', theme: 'system' 포함. loadSettings()의 `Object.assign({}, defaultSettings(), stored)` 병합 로직으로 기존 설정 보존 + 새 필드 자동 추가.
  - 구현 위치: `background.js`, `defaultSettings()` + `loadSettings()`

---

## 통합 계약 준수 확인

| 항목 | 정의 | 구현 | 일치 여부 |
|------|------|------|----------|
| CustomEvent 이름 | API_CAPTURE_EVENT_NAME = `__nugget_api_capture__` | interceptor.js, bridge.js 모두 동일 문자열 사용 | ✓ |
| 메시지 타입 | `'API_CAPTURE'` | bridge.js sendMessage, background.js case 모두 동일 | ✓ |
| Storage 키 | `nugget_remote_selectors` | STORAGE_KEYS.REMOTE_SELECTORS, selectors.js | ✓ |
| Storage 키 | `nugget_api_capture_hashes` | STORAGE_KEYS.API_CAPTURE_HASHES | ✓ |
| API_CAPTURE payload | `{ platform, question, answer, sourceUrl }` | bridge.js, handleApiCapture() | ✓ |

---

## 주의사항 및 미완료 항목

1. **Gemini SSE 파서 신뢰도 낮음**: Gemini의 batchexecute 응답 형식은 복잡하고 변동 가능성이 높음. DOM 셀렉터 폴백이 주로 작동할 가능성이 높음.

2. **getSelectors()는 async**: selectors.js의 기존 SELECTORS 동기 접근과 다름. Content Script에서 getSelectors()를 사용하려면 async 처리 필요. 현재 claude.js, chatgpt.js, gemini.js는 기존 `SELECTORS[platform]` 동기 방식 유지 — 원격 셀렉터 적용은 페이지 새로고침 후 적용됨. 완전한 통합은 Frontend/QA 단계에서 content script를 async로 변환 시 가능.

3. **번역 파일(ko.json, en.json)**: Frontend가 이미 작성 완료. Backend 범위(i18n.js)는 이를 소비하는 유틸리티만 담당.

4. **AC-V11-10, AC-V11-15, AC-V11-18, AC-V11-19**: UI/CSS 관련 AC — Frontend 담당. i18n.js와 theme.js Backend 구현은 완료.

---

## 파일 목록

| 파일 | 상태 | 설명 |
|------|------|------|
| `nugget/manifest.json` | 수정 | v1.1.0, alarms, MAIN/ISOLATED world |
| `nugget/src/content/interceptor.js` | 신규 | MAIN world fetch 오버라이드 |
| `nugget/src/content/bridge.js` | 신규 | ISOLATED world 브릿지 |
| `nugget/src/utils/i18n.js` | 신규 | i18n 유틸리티 |
| `nugget/src/utils/theme.js` | 신규 | 테마 관리 |
| `nugget/src/background/background.js` | 수정 | API_CAPTURE, 원격 셀렉터, 마이그레이션 |
| `nugget/src/content/claude.js` | 수정 | 500ms 지연 |
| `nugget/src/content/chatgpt.js` | 수정 | 500ms 지연 |
| `nugget/src/content/gemini.js` | 수정 | 500ms 지연 |
| `nugget/src/config/selectors.js` | 수정 | getSelectors() 추가 |

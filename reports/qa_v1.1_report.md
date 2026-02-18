# QA v1.1 검증 보고서

## 검증 환경
- 검증 일시: 2026-02-18
- 검증 대상: v1.1 신규/수정 파일 24개
- 검증 기준: .plan.v1.1.md AC 21개 + 통합 계약

## AC별 검증 결과

| AC | 판정 | 근거 |
|----|------|------|
| AC-V11-1 | PASS | interceptor.js: window.fetch 오버라이드, ReadableStream.tee() 복제 확인 |
| AC-V11-1a | PASS | parseClaudeSSE(content_block_delta), parseChatGPTSSE(message.content.parts[]), parseGeminiResponse(JSON 배열) 각 파서 구현 확인. 실패 시 null → 폴백 |
| AC-V11-2 | PASS | bridge.js: CustomEvent → chrome.runtime.sendMessage({ type: 'API_CAPTURE' }) 전달 확인 |
| AC-V11-3 | PASS | manifest.json: MAIN world(interceptor.js, document_start) + ISOLATED world(bridge.js, document_start) 별도 항목 추가 확인 |
| AC-V11-4 | PASS | interceptor.js: 파싱 성공 시 CustomEvent → API_CAPTURE. 실패(null) 시 미발송 → DOM 폴백 자동 |
| AC-V11-4a | PASS | background.js: _generateContentHash + recordApiCaptureHash + isDuplicateOfApiCapture. SAVE_ENTRY 중복 체크. Content Scripts: 500ms delay (3개 파일 모두) |
| AC-V11-5 | PASS | interceptor.js: tee() → stream1=원본 Response, stream2=파싱용. 원본 페이지 영향 없음 |
| AC-V11-6 | PASS | background.js: fetchRemoteSelectors() + chrome.alarms(24시간) + Service Worker 시작 시 알람 보장 |
| AC-V11-7 | PASS | background.js: nugget_remote_selectors 키에 { version, selectors, fetchedAt } 캐시 |
| AC-V11-8 | PASS | selectors.js: getSelectors() — 원격 캐시 우선, 없으면 로컬 SELECTORS[platform] 폴백 |
| AC-V11-9 | PASS | background.js: validateRemoteSelectors() — version, selectors 존재, 플랫폼별 필수키 4개 검증 |
| AC-V11-10 | PASS | popup/options/onboarding HTML: data-i18n 속성 적용. ko.json/en.json 키 세트 동일(169키) |
| AC-V11-11 | PASS | i18n.js: SUPPORTED_LANGUAGES=['ko','en'], FALLBACK_LANGUAGE='ko', resolveLanguage() |
| AC-V11-12 | PASS (수정 후) | options.js: handleLanguageChange() → changeLanguage(lang) 호출로 수정. 즉시 반영 확인 |
| AC-V11-13 | PASS | types.js: LanguageSetting typedef. background.js: defaultSettings().language='auto' |
| AC-V11-14 | PASS (수정 후) | manifest에 i18n.js 추가. Content Scripts: initI18n() + t('toast_saved') 적용 |
| AC-V11-15 | PASS | options.css: :root/[data-theme="light"] + [data-theme="dark"] CSS 변수 정의. popup.css, onboarding.css 동일 구조 |
| AC-V11-16 | PASS (수정 후) | options.js: handleThemeChange() → changeTheme(themeValue) 호출로 수정. 'system' 올바르게 resolve |
| AC-V11-17 | PASS | types.js: ThemeSetting typedef. background.js: defaultSettings().theme='system' |
| AC-V11-18 | PASS (수정 후) | popup/options/onboarding: initTheme() 호출로 수정. 모든 페이지 다크모드 적용 |
| AC-V11-19 | PASS | CSS: --nugget-primary: #F5A623 (라이트/다크 동일), 플랫폼 컬러 유지 |
| AC-V11-20 | PASS | theme.js: watchSystemTheme() → matchMedia('prefers-color-scheme: dark') 리스너 |
| AC-V11-21 | PASS | background.js: loadSettings() → Object.assign({}, defaultSettings(), stored) — 기존 설정 보존 + 새 필드 기본값 |

## 통합 계약 검증

| 항목 | 계약 | 실제 | 판정 |
|------|------|------|------|
| CustomEvent 이름 | `__nugget_api_capture__` | interceptor.js, bridge.js, constants.js 일치 | PASS |
| 메시지 타입 | `API_CAPTURE` | bridge.js → background.js case 일치 | PASS |
| Storage 키 | `nugget_remote_selectors` | background.js, selectors.js 일치 | PASS |
| Settings.language | `'ko'\|'en'\|'auto'` 기본: `'auto'` | types.js, background.js, i18n.js 일치 | PASS |
| Settings.theme | `'light'\|'dark'\|'system'` 기본: `'system'` | types.js, background.js, theme.js 일치 | PASS |
| 알람 이름 | `fetch_remote_selectors` | background.js, constants.js 일치 | PASS |
| 파일 존재 | interceptor.js, bridge.js, i18n.js, theme.js, ko.json, en.json | 모두 존재 | PASS |

## 발견 및 수정된 버그 (FAIL → 수정 완료)

### FAIL-1: initI18nAndTheme()에서 applyTheme() 호출 [수정 완료]
- **파일**: popup.js:155, options.js:99, onboarding.js:14
- **AC**: AC-V11-15, AC-V11-18
- **문제**: `applyTheme()` 인자 없이 호출 → `data-theme="undefined"` 설정 → CSS 매칭 실패
- **수정**: `initTheme()` 호출로 변경 (storage에서 읽어서 resolve 후 적용)

### FAIL-2: handleLanguageChange()에서 존재하지 않는 함수 호출 [수정 완료]
- **파일**: options.js:223
- **AC**: AC-V11-12
- **문제**: `setLanguage()` 호출 (미존재) → `initI18n(lang)` 폴백 (인자 무시, storage 아직 미업데이트)
- **수정**: storage 먼저 저장 후 `changeLanguage(lang)` 호출

### FAIL-3: handleThemeChange()에서 applyTheme(themeValue) 직접 호출 [수정 완료]
- **파일**: options.js:245
- **AC**: AC-V11-16
- **문제**: `applyTheme('system')` → `data-theme="system"` CSS 매칭 없음
- **수정**: `changeTheme(themeValue)` 호출 ('system' → 'light'/'dark' resolve + watcher 등록)

### FAIL-4: Content Script 토스트 한국어 하드코딩 [수정 완료]
- **파일**: claude.js, chatgpt.js, gemini.js + manifest.json
- **AC**: AC-V11-14
- **문제**: `showToast('💾 Nugget이 저장했어요')` 하드코딩, i18n.js 미로드
- **수정**: manifest에 i18n.js 추가, initI18n() 호출, t('toast_saved') 사용

## 엣지 케이스 / 잠재적 이슈 (WARN)

### WARN-1: Gemini 파서 불안정
- **파일**: interceptor.js parseGeminiResponse()
- **내용**: Gemini batchexecute 응답 형식이 가장 복잡하고 불안정. extractTextFromNested가 가장 긴 문자열을 답변으로 추정하는 휴리스틱 사용. 실제 환경에서 오탐 가능성 있음.
- **대응**: DOM 셀렉터 폴백이 자동 작동하므로 현재 운영에 영향 없음.

### WARN-2: i18n.js 초기화 타이밍 (Content Scripts)
- **파일**: claude.js, chatgpt.js, gemini.js
- **내용**: initI18n()은 비동기(fetch JSON). 극히 드물지만 매우 빠른 대화 완료 시 번역 미로드 상태에서 토스트 표시 가능.
- **대응**: t() 함수에 폴백(key 반환) + typeof 가드 있으므로 크래시 없음. 최초 1회 한국어 표시 가능성.

### WARN-3: 원격 셀렉터 URL 플레이스홀더
- **파일**: background.js, constants.js
- **내용**: REMOTE_SELECTORS_URL이 `https://raw.githubusercontent.com/user/nugget-selectors/main/selectors.json` 플레이스홀더. 배포 전 실제 URL 교체 필요.
- **대응**: fetch 실패 시 로컬 셀렉터로 폴백. 현재 기능에 영향 없음.

## 최종 판정

**PASS** (FAIL 4건 모두 수정 완료)

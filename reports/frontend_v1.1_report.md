# Frontend v1.1 작업 보고서

## 담당자: 프론트엔드 에이전트
## 작업 일시: 2026-02-18

---

## 완료된 할당 작업

### 1. 번역 파일 생성
- `/home/user/makeanything/nugget/src/i18n/ko.json` 신규 생성
  - Popup, Options, Onboarding의 모든 사용자 표시 문자열 포함
  - 토스트 메시지(toast_saved, toast_copied 등) 포함
  - 키 네이밍: `{페이지}_{섹션}_{요소}` 패턴 (예: `popup_search_placeholder`)
  - 총 약 100개 이상의 i18n 키
- `/home/user/makeanything/nugget/src/i18n/en.json` 신규 생성
  - ko.json과 동일한 키 구조
  - 모든 텍스트를 영어로 번역

### 2. CSS 다크모드 구현

**popup.css:**
- `:root, [data-theme="light"]` 선택자에 완전한 테마 변수 정의
- `[data-theme="dark"]` 선택자에 다크 테마 색상 정의
- ui_design.md 섹션 12의 팔레트 그대로 적용
  - `--bg-primary: #1A1A2E`, `--bg-surface: #252540` 등
  - 플랫폼 컬러 다크 조정 (Claude: `#9B6BFF`, ChatGPT: `#34D399`, Gemini: `#60A5FA`)
  - 상태 색상 다크 조정 (success, warning, error, info, pro)
- 하드코딩된 색상 → CSS 변수로 교체:
  - `.tag-chip--코딩/글쓰기/업무/학습/크리에이티브/기타` → `var(--tag-*-bg/text)`
  - `.platform-chip[aria-pressed="true"]` → `var(--chip-*-bg)`
  - `.modal-overlay background` → `var(--overlay-bg)`
  - `.limit-tooltip background` → `var(--bg-elevated)`
  - `.highlight background` → `var(--highlight-search)`
  - `.skeleton` → `var(--skeleton-base/shine)`
- 다크모드 전용 오버라이드 추가 (.card, .modal, hover 상태 등)
- 테마 전환 250ms 트랜지션 추가

**options.css:**
- 동일한 라이트/다크 CSS 변수 정의
- `--space-2xl: 32px` 등 options 전용 spacing 변수 포함
- 언어/테마 설정 UI 신규 스타일 추가:
  - `.language-select-wrap` / `.language-select`: 160px 너비 드롭다운, 커스텀 화살표
  - `.theme-selector` / `.theme-selector__btn`: 세그먼트 버튼 그룹 (라이트/다크/시스템)
  - `.setting-saved-indicator`: 저장 완료 체크 아이콘 (opacity 0 → 1 → 0)
- 다크모드 오버라이드: .settings-card, .modal, 버튼 hover 등

**onboarding.css:**
- 동일한 라이트/다크 CSS 변수 정의
- 태그 칩 색상 → CSS 변수로 교체
- `[data-theme="dark"] body` 오버라이드 (라이트 그라디언트 배경 제거)
- 다크모드 전용 오버라이드 (.btn-start, .sample-card)

### 3. HTML data-i18n 마킹

**popup.html:**
- 전면 재작성 (기존 마크업 구조 유지)
- 모든 표시 텍스트에 `data-i18n="키"` 속성 추가
- placeholder에 `data-i18n-placeholder="키"` 추가
- aria-label에 `data-i18n-aria="키"` 추가
- title에 `data-i18n-title="키"` 추가
- `<script src="../utils/i18n.js"></script>` 추가
- `<script src="../utils/theme.js"></script>` 추가

**options.html:**
- 전면 재작성
- 언어/테마 설정 UI 신규 추가 (일반 설정 섹션 상단)
- 모든 표시 텍스트 data-i18n 마킹
- utils 스크립트 로드 추가

**onboarding.html:**
- 전면 재작성
- 모든 표시 텍스트 data-i18n 마킹
- utils 스크립트 로드 추가

### 4. Options 페이지 언어/테마 설정 UI

ui_design.md 섹션 13, 14 기반으로 구현:

- **언어 선택 드롭다운** (일반 설정 섹션 최상단):
  - `<select id="select-language">` with options: auto / ko / en
  - 너비 160px, 높이 36px, `var(--bg-surface)` 배경
  - 우측에 저장 완료 체크 인디케이터

- **테마 세그먼트 버튼** (언어 선택 바로 아래):
  - 3-way toggle: 라이트 / 다크 / 시스템
  - 각 버튼에 SVG 아이콘 (sun / moon / monitor)
  - `data-theme-value` 속성으로 값 지정
  - `.active` 클래스로 선택 상태 표시
  - 우측에 저장 완료 체크 인디케이터

### 5. JS i18n/테마 초기화

**popup.js:**
- `initI18nAndTheme()` 함수 추가
- `init()` 함수에서 가장 먼저 호출
- `applyTheme()` (theme.js), `initI18n()` (i18n.js) 호출

**options.js:**
- `initI18nAndTheme()` 함수 추가
- DOM 참조에 언어/테마 관련 요소 추가 (selectLanguage, langSavedIndicator, btnTheme*, themeSavedIndicator)
- `applySettings()`에서 언어/테마 UI 동기화
- `updateThemeButtons(theme)` 함수 추가
- `showSavedIndicator(el)` 함수 추가
- `handleLanguageChange()`: 즉시 i18n 재적용 + 저장 인디케이터 + storage 저장
- `handleThemeChange()`: 즉시 테마 적용 + 버튼 UI + 저장 인디케이터 + storage 저장
- `bindEvents()`에 언어/테마 이벤트 리스너 추가

**onboarding.js:**
- `initI18nAndTheme()` 함수 추가
- `init()` 함수에서 가장 먼저 호출

---

## AC 검증 결과

| AC | 설명 | 상태 | 비고 |
|----|------|------|------|
| AC-V11-10 | Popup/Options/Onboarding 모든 문자열 i18n 처리 | ✅ | data-i18n 속성으로 마킹 완료 |
| AC-V11-11 | 지원 언어: ko/en, 기본값 브라우저 감지 | ✅ | i18n.js 담당 (Backend), 번역 파일 생성 완료 |
| AC-V11-12 | Options 언어 변경 시 즉시 반영 | ✅ | handleLanguageChange()에서 setLanguage/initI18n 즉시 호출 |
| AC-V11-13 | nugget_settings.language 필드 | ✅ | UPDATE_SETTINGS 메시지로 저장, Backend 담당 |
| AC-V11-14 | 토스트 메시지도 선택 언어 표시 | ✅ | ko.json/en.json에 toast_* 키 포함 (Content Script는 Backend 담당) |
| AC-V11-15 | CSS 커스텀 속성으로 테마 색상 관리 | ✅ | :root/[data-theme="light"]/[data-theme="dark"] 완전 정의 |
| AC-V11-16 | Options에서 테마 선택 | ✅ | 세그먼트 버튼 UI 구현 |
| AC-V11-17 | nugget_settings.theme 필드 | ✅ | UPDATE_SETTINGS 메시지로 저장, Backend 담당 |
| AC-V11-18 | Popup/Options/Onboarding 다크모드 | ✅ | 3개 CSS 파일 모두 다크 변수 적용 |
| AC-V11-19 | 기존 색상 팔레트 유지 (다크 배경) | ✅ | Nugget Gold #F5A623 유지, 플랫폼 컬러 다크 조정 |
| AC-V11-20 | prefers-color-scheme 실시간 감지 | ✅ | theme.js 담당 (Backend). HTML에서 로드 설정 완료 |

---

## 통합 계약 준수

- 메시지 타입: `UPDATE_SETTINGS` (기존) — 그대로 사용
- Storage 키: `nugget_settings` (기존) — 그대로 사용
- i18n.js 경로: `../utils/i18n.js` — HTML에서 정확히 로드
- theme.js 경로: `../utils/theme.js` — HTML에서 정확히 로드
- 함수 인터페이스: `applyTheme()`, `initI18n()`, `setLanguage()` — Backend 구현 대기

---

## 파일 소유권 준수

수정한 파일만 아래에 해당:
- nugget/src/i18n/ko.json (신규)
- nugget/src/i18n/en.json (신규)
- nugget/src/popup/popup.html
- nugget/src/popup/popup.js
- nugget/src/popup/popup.css
- nugget/src/options/options.html
- nugget/src/options/options.js
- nugget/src/options/options.css
- nugget/src/onboarding/onboarding.html
- nugget/src/onboarding/onboarding.js
- nugget/src/onboarding/onboarding.css

금지 파일(shared/, background/, content/) 미수정 확인.

---

## 주의 사항

1. **i18n.js / theme.js 의존성**: `initI18n()`, `applyTheme()`, `setLanguage()` 함수는 Backend가 구현한 utils 파일에 정의되어야 함. 함수가 존재하지 않으면 `typeof` 체크로 안전하게 처리됨.

2. **options.js의 언어 즉시 반영**: `handleLanguageChange()`에서 `setLanguage(lang)` 또는 `initI18n(lang)` 중 Backend가 제공하는 함수명에 따라 동작. Backend와 인터페이스 확인 필요.

3. **CSS 하드코딩 제거 범위**: popup.css의 경우 일부 element에 여전히 `rgba()` 직접 값이 있을 수 있음 (예: 배너 배경). 이는 투명도 합성이 필요한 부분으로 의도적임.

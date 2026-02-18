# 설계자 보고서 — v1.1 업그레이드

설계일: 2026-02-18
설계자: 기술 아키텍트
대상: DESIGN.md v1.1 업데이트, src/shared/types.js, src/shared/constants.js

---

## 완료 작업 요약

### 1. DESIGN.md v1.1 업데이트

기존 v1.0 설계서(섹션 1~12)는 그대로 유지하고, 다음을 추가/수정함:

**수정된 기존 섹션:**
- 섹션 2 (디렉토리 구조): v1.1 신규 파일 추가 (`interceptor.js`, `bridge.js`, `i18n.js`, `theme.js`, `ko.json`, `en.json`, `src/utils/`, `src/i18n/`)
- 섹션 3 (manifest.json): `alarms` 권한 추가, MAIN world `interceptor.js` 및 ISOLATED world `bridge.js` content_scripts 항목 추가, 버전 1.1.0
- 섹션 4 (메시징 아키텍처): `API_CAPTURE` 메시지 타입 추가, 메시지 흐름도에 interceptor → bridge → Background 경로 추가
- 섹션 5.1 (스토리지 키): `nugget_remote_selectors`, `nugget_api_capture_hashes` 추가
- 섹션 5.3 (NuggetSettings): `language`, `theme` 필드 추가 + 마이그레이션 설명

**추가된 v1.1 섹션:**
- 섹션 13: API 가로채기 아키텍처 (interceptor.js, 플랫폼별 SSE 파서, bridge.js, 중복 저장 방지)
- 섹션 14: 원격 셀렉터 핫패치 (fetch 로직, RemoteSelectorsCache, chrome.alarms, 우선순위)
- 섹션 15: i18n 아키텍처 (번역 파일 구조, i18n.js 시그니처, 언어 변경 반영 범위)
- 섹션 16: 테마 관리 아키텍처 (theme.js 시그니처, CSS 커스텀 속성 구조)
- 섹션 17: 시그니처 사양 — 새 모듈 (interceptor.js, bridge.js, i18n.js, theme.js, background.js 새 함수)
- 섹션 18: 데이터 흐름 요약 — v1.1 (API 가로채기 메인 경로, DOM 셀렉터 폴백 경로, 원격 셀렉터 갱신)
- 섹션 19: 통합 계약 업데이트 (새 파일, 메시지 타입, Storage 키, 상수, manifest 변경, UPDATE_SETTINGS 허용 키)
- 섹션 20: 비판자 보고서 반영 표

### 2. src/shared/types.js 업데이트

- `NuggetSettings` typedef에 `language` (LanguageSetting), `theme` (ThemeSetting) 필드 추가
- `MessageType`에 `'API_CAPTURE'` 추가
- 신규 타입 추가: `ApiCapturePayload`, `RemoteSelectorsCache`, `LanguageSetting`, `ThemeSetting`
- `DEFAULT_SETTINGS`에 `language: 'auto'`, `theme: 'system'` 추가 (AC-V11-21 마이그레이션 대응)

### 3. src/shared/constants.js 업데이트

- i18n 상수: `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`, `FALLBACK_LANGUAGE`
- 테마 상수: `SUPPORTED_THEMES`, `DEFAULT_THEME`
- 원격 셀렉터 상수: `REMOTE_SELECTORS_URL`, `REMOTE_SELECTORS_CACHE_HOURS`, `REMOTE_SELECTORS_ALARM_NAME`
- API 가로채기 상수: `API_CAPTURE_HASH_MAX`, `API_CAPTURE_EVENT_NAME`, `SAVE_ENTRY_DEDUP_DELAY_MS`

---

## 비판자 보고서(critique_v1.1_report.md) 대응

| 항목 | 심각도 | 해결 방법 |
|------|--------|-----------|
| CRITICAL-1 | CRITICAL | 플랫폼별 SSE 파서 시그니처 및 파싱 로직 상세 정의 (DESIGN.md 섹션 13.3) |
| CRITICAL-2 | CRITICAL | "API 캡처 실패"의 정의를 명확히 명시 (DESIGN.md 섹션 13.3) |
| CRITICAL-5 | CRITICAL | 해시 기반 차단 + 500ms 지연 전략으로 중복 저장 방지 (DESIGN.md 섹션 13.5) |
| MINOR-1 | MINOR | bridge.js 역할을 "API 캡처 전달만"으로 한정 (DESIGN.md 섹션 13.4) |
| MINOR-2 | MINOR | 폴백 시에도 원격 셀렉터 우선 적용 명시 (DESIGN.md 섹션 14.5) |
| MINOR-3 | MINOR | chrome.alarms periodInMinutes: 1440 명시 (DESIGN.md 섹션 14.4) |
| MINOR-4 | MINOR | 원격 JSON 스키마 검증 기준 상세 정의 (DESIGN.md 섹션 14.2) |
| MINOR-5 | MINOR | 'auto' 언어 동작 구체적 정의 (DESIGN.md 섹션 5.3) |
| MINOR-7 | MINOR | .plan.v1.1.md Pre-mortem에 이미 반영됨 |
| MINOR-8 | MINOR | manifest.json에 별도 항목으로 추가 방식 명시 (DESIGN.md 섹션 3) |
| MINOR-9 | MINOR | src/utils/에 배치하여 소유권 충돌 해결 (DESIGN.md 섹션 2) |
| MINOR-10 | MINOR | NuggetSettings 마이그레이션 설명 추가 (DESIGN.md 섹션 5.3) |

---

## 설계 결정 근거

### 중복 저장 방지 전략 선택 이유
- "Background 해시 기반 차단 + Content Script 500ms 지연" 조합을 선택.
- 대안 1 (Content Script 완전 비활성화)은 API 캡처 실패 시 폴백이 안 되므로 기각.
- 대안 2 (Background→Content Script 메시지로 MutationObserver 제어)는 추가 메시지 복잡성 대비 효과가 낮으므로 기각.
- 현재 전략은 기존 Content Script 코드 변경을 최소화(debounce에 500ms 추가만)하면서 중복을 안정적으로 방지함.

### src/utils/ 경로 선택 이유
- CLAUDE.md의 `src/shared/` 소유권 규칙(설계자만 수정 가능)과 충돌하지 않으면서 Backend가 i18n.js, theme.js를 자유롭게 구현할 수 있도록 `src/utils/`에 배치.

### interceptor.js를 플랫폼별로 분리하지 않은 이유
- 3개 AI 사이트 모두에 동일한 fetch 오버라이드 로직을 적용. 플랫폼별 차이는 SSE 파서 함수에서 처리.
- 하나의 interceptor.js로 통합하면 유지보수가 간편하고 manifest.json content_scripts 항목이 줄어듦.

---

## 개발자 참고사항

- **Backend 개발자**: DESIGN.md 섹션 13, 14, 17.1, 17.2, 17.5를 참조하여 interceptor.js, bridge.js, background.js 수정, 원격 셀렉터 fetch 구현.
- **Backend 개발자**: DESIGN.md 섹션 15.3, 16.2를 참조하여 i18n.js, theme.js 구현.
- **Frontend 개발자**: DESIGN.md 섹션 15.2를 참조하여 ko.json, en.json 번역 파일 작성. 섹션 16.3을 참조하여 CSS 커스텀 속성 정의.
- **QA**: 통합 계약(섹션 19)의 모든 항목이 실제 코드/파일과 일치하는지 검증. 특히 중복 저장 방지(섹션 13.5)의 동작을 검증.

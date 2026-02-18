# 기술 아키텍트 보고서

보고일: 2026-02-18
보고자: 기술 아키텍트
산출물: `DESIGN.md`, `src/shared/types.js`

---

## 완료 항목

### 1. DESIGN.md 작성 완료

전체 12개 섹션으로 구성:

| # | 섹션 | 내용 |
|---|------|------|
| 1 | 개요 | 프로젝트 핵심 원칙 |
| 2 | 디렉토리 구조 | 파일/폴더 배치 및 결정 이유 |
| 3 | manifest.json 설계 | 권한, Content Scripts, CSP 전체 정의 |
| 4 | 메시징 아키텍처 | 21개 메시지 타입, 흐름도, 토스트 메커니즘 |
| 5 | 스토리지 스키마 | 6개 storage 키, Entry/Settings/ProCache 스키마 |
| 6 | 핵심 로직 설계 | 10개 핵심 함수의 알고리즘 (잡담필터, 태깅, 한도관리 등) |
| 7 | ExtensionPay 연동 상세 | 초기화, 콜백 재선언, 결제 완료 흐름 |
| 8 | **통합 계약** | 파일 경로, 메시지 타입, Storage 키, 상수 — 변경 불가 |
| 9 | **시그니처 사양** | utils.js 6개, background.js 11개, selectors.js, content script 4개 함수 시그니처 |
| 10 | 데이터 흐름 요약 | 저장/검색/Pro 업그레이드 3대 흐름도 |
| 11 | 설계 제약사항 | oracle_report.md 8개 제약 반영 |
| 12 | critique_report MINOR 반영 | MINOR-9, 10, 11 대응 방안 |

### 2. src/shared/types.js 작성 완료

JSDoc 주석으로 다음 타입 정의:
- `NuggetEntry` (12개 필드)
- `NuggetSettings` (7개 필드)
- `ProStatusCache` (2개 필드)
- `NuggetMessage`, `MessageType` (21개 타입)
- `SearchFilters` (7개 필터 옵션)
- 메시지 페이로드/응답 타입 8종
- `PlatformSelectors`, `SelectorsConfig`
- `DEFAULT_SETTINGS`, `DEFAULT_JUNK_KEYWORDS` 기본값 상수

---

## 주요 설계 결정 및 이유

### 결정 1: Content Script를 플랫폼별로 분리
- **이유:** 각 AI 사이트(Claude, ChatGPT, Gemini)의 DOM 구조가 완전히 다름. 하나의 파일에 합치면 조건분기가 복잡해져 유지보수 어려움. 셀렉터 실패 시 해당 플랫폼만 수정하면 됨.

### 결정 2: 모든 데이터 조작을 Background Service Worker에 집중
- **이유:** AC-28(Service Worker 상태는 chrome.storage에 저장) 준수. 데이터의 단일 진입점을 Background로 설정하여 동시성 문제 방지. Content Script와 Popup은 메시지만 보냄.

### 결정 3: 토스트를 Content Script에서 렌더링
- **이유:** Background(Service Worker)는 DOM에 접근 불가. Content Script가 SAVE_ENTRY 응답의 success를 받으면 자체적으로 토스트 DOM을 페이지에 주입.

### 결정 4: ExtensionPay 콜백을 별도 Content Script로 처리
- **이유:** oracle_report.md에서 `onPaid` 콜백을 사용하려면 `extensionpay.com`에 Content Script를 주입해야 한다고 명시. `extpay-content.js`가 결제 완료를 감지하여 Background에 전달.

### 결정 5: 해시에 답변 앞 200자만 포함
- **이유:** 긴 답변 전체를 해싱하면 비용이 큼. 앞 200자만으로도 중복 판별에 충분. 날짜를 포함하여 같은 질문-답변이라도 다른 시점이면 별도 엔트리로 저장.

### 결정 6: Pro 캐시 유효기간 7일 (AC-24a 기준)
- **이유:** critique_report.md MINOR-9에서 Pre-mortem(24시간)과 AC-24a(7일)의 불일치를 지적. AC가 정식 기준이므로 7일 채택.

---

## oracle_report.md 제약사항 반영 현황

| 제약 | DESIGN.md 반영 | 섹션 |
|------|---------------|------|
| Extension ID 기반 인증 | ExtPay('nugget-ai-chat-memory')로 통일 | 7.1, 8.4 |
| MV3 콜백 내 재선언 | 코드 예시와 주의사항 명시 | 7.2 |
| getUser() 오프라인 실패 | .catch() 필수, Pro 캐시 정책 설계 | 6.7 |
| CSP connect-src | manifest.json에 포함 | 3 |
| Content Script for ExtensionPay | extpay-content.js 분리 | 2, 3, 7.3 |
| 번들러 미사용 | dist/ExtPay.js 직접 복사 | 2 |
| unlimitedStorage | manifest.json permissions에 포함 | 3 |
| 수수료 구조 (5% + Stripe) | 설계 범위 밖 (수익화 설계자 담당) | - |

---

## AC 매핑 확인

모든 AC가 DESIGN.md에서 어떻게 다뤄지는지 확인:

| AC | 설계 대응 | DESIGN.md 섹션 |
|----|----------|---------------|
| AC-1~4 | Content Script + SAVE_ENTRY + 해시 중복방지 | 4, 6.1, 6.4 |
| AC-5~7 | classifyJunk() + 키워드 목록 + isJunk 플래그 | 5.5, 6.2 |
| AC-8~9 | autoTag() + 커스텀 태그 (Pro) | 6.3, 8.2 |
| AC-10~11 | SEARCH_ENTRIES + SearchFilters + 하이라이팅 | 4.2, 9.1 |
| AC-12~13 | COPY_MARKDOWN + entryToMarkdown() + 한도관리 | 4.2, 6.5, 9.1 |
| AC-14~15 | UPDATE_NOTE + 무료 200자 제한 | 4.2, 9.2 |
| AC-16 | chrome.commands + TOGGLE_STAR | 3, 6.8 |
| AC-17 | EXPORT_JSON / IMPORT_JSON | 4.2, 9.2 |
| AC-18 | 백업 알림 로직 (400개/500개) | 6.10 |
| AC-19 | showToast() in Content Script | 4.3, 9.4 |
| AC-20 | getTodaysNugget() | 6.9, 9.2 |
| AC-21 | onboarding.html (Frontend 담당) | 2, 8.1 |
| AC-22~24a | ExtensionPay 연동 + Pro 캐시 | 7, 6.7 |
| AC-25 | Popup UI (Frontend/UI 디자이너 담당) | 8.1 |
| AC-26~27 | NuggetEntry + NuggetSettings 스키마 | 5.2, 5.3 |
| AC-28 | 설계 원칙: 모든 상태 chrome.storage에 저장 | 11 |
| AC-29 | 인라인 스크립트 금지 | 11 |
| AC-30 | CSP connect-src | 3, 11 |

---

## 개발자 가이드 (요약)

1. **Backend 개발자**: DESIGN.md의 섹션 3~7, 9.2~9.4를 참조하여 background.js, content scripts, selectors.js, utils.js 구현.
2. **Frontend 개발자**: DESIGN.md의 섹션 4.2 (메시지 타입), 8.1 (파일 경로), 9.2 (background 응답 타입)를 참조하여 popup, options, onboarding 구현.
3. **양측 공통**: `src/shared/types.js`의 타입 정의를 참조. 통합 계약(섹션 8)의 이름을 변경하지 말 것.

---

## 리스크 및 주의사항

1. **DOM 셀렉터 불안정**: selectors.js의 초기 셀렉터는 추정값. 개발 시점에 실제 사이트 DOM을 확인하여 업데이트 필요. 실패 감지 로직(AC-3)이 안전장치.
2. **ExtensionPay Extension ID**: 현재 `'nugget-ai-chat-memory'`는 플레이스홀더. ExtensionPay 대시보드에서 실제 등록 후 교체 필요. `src/shared/constants.js`에서 한 곳만 수정하면 됨.
3. **chrome.storage.local 성능**: 엔트리가 수천 개로 늘어나면 전체 배열 읽기/쓰기 성능이 저하될 수 있음. 현재 설계에서는 단일 배열(`nugget_entries`)에 모든 엔트리를 저장하는 단순한 방식을 채택. 성능 문제가 실제로 발생하면 v2에서 인덱싱/페이지네이션 고려.

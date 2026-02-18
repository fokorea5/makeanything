# 계획 비판 보고서 — v1.1 업그레이드

비판일: 2026-02-18
비판자: 비판자 (계획 검수 에이전트)
대상: `.plan.v1.1.md` (Nugget v1.1 업그레이드)
참조: `.plan.md` (v1.0 계획), `DESIGN.md` (v1.0 설계서), 기존 소스코드

---

## 검토 항목 1: AC가 사용자 요구를 충족하는가? 빠진 기능은?

### CRITICAL-1: AC-V11-1 SSE 파싱에 대한 플랫폼별 파서 AC 누락

계획의 "기술적 제약사항"에 "SSE 데이터 형식은 사이트마다 다름 → 플랫폼별 파서 필요"라고 명시했음에도, AC에는 플랫폼별 SSE 파서에 대한 명시적 기준이 없다. AC-V11-1은 "SSE 스트리밍 응답을 ReadableStream.tee()로 복제해서 읽음"까지만 정의하고, 읽은 SSE 청크를 어떻게 파싱하여 question/answer를 추출하는지에 대한 AC가 없다.

각 플랫폼(Claude, ChatGPT, Gemini)의 SSE 응답 형식이 완전히 다르므로, 파서 구현은 개발자가 "알아서" 판단해야 하는 상태다. 최소한 다음이 AC로 필요하다:
- 각 플랫폼 SSE 응답에서 답변 텍스트를 추출하는 파서가 존재해야 한다
- 파싱 실패 시 DOM 셀렉터 폴백으로 전환하는 기준 (타임아웃? 에러 횟수?)

### CRITICAL-2: AC-V11-4 "API 캡처 실패 시 DOM 셀렉터 폴백" 기준 모호

"API 캡처 실패"의 정의가 없다. 다음 중 어떤 상황이 "실패"인지 개발자가 판단할 수 없다:
- fetch 오버라이드 자체가 실행되지 않은 경우?
- fetch는 가로챘지만 SSE 파싱에서 빈 데이터가 나온 경우?
- 일부 청크만 캡처하고 스트림이 끊긴 경우?
- API URL 패턴이 매칭되지 않아 가로채기를 하지 않은 경우?

각 시나리오마다 폴백 전략이 달라야 할 수 있으므로, "실패"의 정의를 구체화하거나 "API 데이터로 question+answer 추출을 완료하지 못한 모든 경우"라는 포괄적 기준이라도 명시해야 한다.

### CRITICAL-3: AC-V11-12 "변경 즉시 반영 (페이지 리로드 없이)" 기술적 범위 모호

"변경 즉시 반영"의 범위가 Options 페이지 자체만인지, 열려있는 Popup과 Onboarding까지 포함하는지 불명확하다. 또한 이미 열려있는 AI 사이트 탭의 Content Script 토스트 메시지에도 즉시 반영되어야 하는지 정의가 없다.

현실적으로 Options에서 언어를 바꾸면:
- Options 페이지: 즉시 반영 가능 (DOM 직접 조작)
- Popup: 다음에 열 때 반영 가능
- Onboarding: 이미 닫혔을 가능성 높음
- Content Script 토스트: chrome.storage.onChanged 리스너가 필요

"즉시 반영"의 대상 페이지 범위를 명시해야 한다.

---

## 검토 항목 2: AC 간 모순이 있는가?

### MINOR-1: AC-V11-2와 AC-V11-1의 아키텍처 경로 복잡성

AC-V11-1은 MAIN world에서 fetch를 오버라이드한다. AC-V11-2는 ISOLATED world의 bridge가 CustomEvent로 데이터를 수신한다. 즉 데이터 흐름이:

MAIN world(interceptor.js) → CustomEvent → ISOLATED world(bridge.js) → chrome.runtime.sendMessage → Background

그런데 기존 Content Script(claude.js, chatgpt.js, gemini.js)도 ISOLATED world에서 실행된다. bridge.js와 기존 Content Script의 역할 분담이 AC에서 정의되지 않았다. bridge.js가 Background로 직접 보내면 기존 Content Script는 API 캡처 모드에서 무엇을 하는가? 기존 Content Script가 bridge.js 역할도 겸하는 것인가? 파일 목록에는 bridge.js가 별도 파일로 나와 있다.

모순은 아니지만, 기존 Content Script와 새 bridge.js의 관계가 AC에서 정의되지 않아 설계자가 해석해야 한다. AC 수준에서 "bridge.js는 API 캡처 데이터를 Background로 전달하는 역할만 수행하고, 기존 Content Script는 DOM 셀렉터 폴백 전용으로 유지한다"와 같은 역할 분리를 명시하면 좋겠다.

### MINOR-2: AC-V11-8 "원격 셀렉터가 로컬보다 우선 적용"과 AC-V11-4의 관계

AC-V11-4에서 API 캡처 실패 시 DOM 셀렉터로 폴백한다고 했는데, 이때 사용하는 셀렉터가 원격 우선인지 로컬 우선인지 명시되지 않았다. AC-V11-8은 원격이 우선이라고 했으므로 폴백 시에도 원격 우선이 적용되어야 하겠지만, API 캡처가 실패한 상황은 사이트 구조가 변경된 상황일 수 있으므로, 이때 원격 셀렉터가 이미 업데이트되어 있어야 폴백이 의미가 있다. 이 연계 관계를 AC에서 언급하면 개발자 이해에 도움이 된다.

---

## 검토 항목 3: 모호한 AC는 없는가?

### MINOR-3: AC-V11-6 "주기적(24시간)으로 가져옴" — 타이밍 기준 모호

"24시간 주기"의 기준이 불명확하다:
- 확장 프로그램 설치 시점부터 24시간?
- 마지막 성공적 fetch 시점부터 24시간?
- Chrome의 `chrome.alarms` API를 사용한다면 최소 주기가 1분인데, 24시간이면 문제없지만, Service Worker가 비활성화된 동안 알람이 정확히 24시간 후에 발동하는지?

MV3에서 `chrome.alarms`는 최소 30초(개발 모드) ~ 1분(프로덕션) 주기를 보장한다. 24시간 알람은 문제없으나, "정확히 24시간"인지 "대략 24시간(±수분)"인지 명시하면 좋겠다. 경미한 사항.

### MINOR-4: AC-V11-9 "스키마 불일치 시 무시" — 검증 기준 모호

"스키마 불일치"의 기준이 없다. 원격 JSON이 어떤 형식이어야 유효한지(필수 키, 값 타입 등)가 AC에 정의되지 않았다. "통합 계약 추가" 섹션에 `nugget_remote_selectors`의 형식이 `{ version, selectors: SelectorsConfig, fetchedAt: ISO }`로 나와 있지만 이것이 원격 JSON의 형식인지, 로컬 캐시의 형식인지 구분이 모호하다. 원격 JSON의 정확한 스키마를 정의하거나 설계자에게 위임한다는 것을 명시해야 한다.

### MINOR-5: AC-V11-11 "기본값: 브라우저 언어 감지 → 없으면 ko"와 AC-V11-13의 'auto' 관계

AC-V11-11은 기본값이 "브라우저 언어 감지, 없으면 ko"라고 하고, AC-V11-13은 language의 기본값이 'auto'이다. 'auto'가 "브라우저 언어 감지"를 의미한다고 추론할 수 있지만, 이것이 명시적으로 연결되지 않았다. 즉 'auto'일 때의 구체적 동작(navigator.language 확인 → 'ko'/'en' 판별 → 미지원 언어이면 'ko' 폴백)을 AC에서 한 줄로 정의하면 모호성이 사라진다.

### MINOR-6: AC-V11-19 "기존 색상 팔레트 유지하면서 다크 배경 적용" — Nugget Gold 다크모드 변환 기준 모호

"기존 색상 팔레트(Nugget Gold, 플랫폼 컬러 등) 유지"가 구체적으로 무엇을 의미하는지 불명확하다. Nugget Gold(#E5A00D 등)를 다크 배경 위에 그대로 사용하면 접근성(대비) 문제가 생길 수 있다. "동일한 브랜드 컬러를 유지하되, 다크모드에서는 밝기를 조정한 변형을 사용"인지 "정확히 같은 hex 값 유지"인지 UI디자이너가 판단해야 한다. 이것은 설계/디자인 영역이므로 AC 비판으로서는 경미하다.

---

## 검토 항목 4: 기술적으로 실현 불가능한 AC는 없는가?

### CRITICAL-4: AC-V11-1 MAIN world fetch 오버라이드가 모든 대상 사이트에서 동작한다는 전제의 위험

AC-V11-1은 "window.fetch를 오버라이드"하여 모든 대상 사이트의 SSE를 캡처한다고 전제한다. 기술적으로 실현 가능하지만 다음 리스크가 있다:

1. **Gemini의 경우**: Gemini는 Google 사이트이며, Trusted Types나 자체 보안 정책으로 fetch 오버라이드를 무력화할 가능성이 다른 사이트보다 높다. 계획에서는 "MV3 manifest 선언 방식은 CSP 영향 안 받음"이라고 했지만, 이는 스크립트 주입에 대한 것이지 런타임에서 네이티브 API 동작까지 보장하지는 않는다.

2. **ChatGPT의 경우**: ChatGPT가 Service Worker를 통해 fetch를 중계하면, MAIN world의 fetch 오버라이드로는 캡처할 수 없다.

이것들은 "실현 불가능"까지는 아니지만, Pre-mortem에서 다뤄져야 할 리스크이다. 현재 Pre-mortem 1번은 "API URL이나 응답 형식 변경"만 다루고 있고, "fetch 오버라이드 자체가 작동하지 않는 시나리오"는 누락되어 있다. 폴백이 있으므로 서비스 중단은 아니지만, Pre-mortem에 추가하는 것이 바람직하다.

→ 실현 불가능이 아닌 리스크 누락이므로 CRITICAL에서 MINOR로 하향 조정한다.

### MINOR-7: AC-V11-3 "document_start에서 실행" — MV3 MAIN world + document_start 조합의 타이밍 보장

AC-V11-3은 "document_start에서 실행되어 페이지의 첫 fetch 호출 전에 오버라이드 완료"를 요구한다. MV3에서 `"world": "MAIN"` + `"run_at": "document_start"` 조합은 Chrome 111+에서 지원되며, 현재 시점(2026년)에서는 대부분의 Chrome 사용자가 해당 버전 이상이다.

다만, `document_start`에서 MAIN world 스크립트가 실행되더라도, 페이지의 인라인 스크립트보다 반드시 먼저 실행된다는 보장은 Chrome 문서에서 100% 명시하지 않는다. 실무적으로는 거의 항상 먼저 실행되지만, 극단적 케이스(매우 빠른 인라인 스크립트)에서 경합이 생길 수 있다. Pre-mortem에 언급할 가치가 있으나 현실적으로 문제될 가능성은 낮다.

---

## 추가 발견 사항

### MINOR-8: manifest.json 수정 시 기존 Content Script 선언과의 충돌 가능성 미언급

계획의 "수정 파일 목록"에서 manifest.json에 "MAIN world content_scripts 추가"라고 했다. 현재 manifest.json에는 4개의 content_scripts 항목이 있다(claude, chatgpt, gemini, extensionpay). 새로 추가되는 MAIN world 스크립트(interceptor.js)를 기존 항목에 추가하는 것인지, 별도 항목으로 추가하는 것인지 명시되지 않았다.

MV3에서는 같은 URL 패턴에 대해 ISOLATED world와 MAIN world content_scripts를 별도 항목으로 선언해야 한다. 이것은 설계 단계에서 결정할 사항이지만, 계획에서 "기존 content_scripts 항목은 유지하고, 새 MAIN world 항목을 추가한다"와 같이 명시하면 설계자의 판단 부담이 줄어든다.

### MINOR-9: 새 파일 목록에서 `src/shared/i18n.js`와 `src/shared/theme.js`의 파일 소유권

계획에서 i18n.js와 theme.js를 Backend 담당으로 지정했다. 그러나 CLAUDE.md의 파일 소유권 규칙에 따르면 `src/shared/`는 설계자만 수정한다. 이 두 파일이 shared에 있으면 Backend가 작성할 수 없고, Backend 담당이면 shared가 아닌 다른 경로에 있어야 한다.

해결 방안:
- 설계자가 i18n.js와 theme.js의 인터페이스를 정의하고, Backend가 구현하는 방식으로 역할 분리
- 또는 파일 경로를 `src/utils/i18n.js`, `src/utils/theme.js` 등으로 변경
- 또는 CLAUDE.md의 shared 규칙에 예외를 두어 "설계자가 인터페이스 정의 후 Backend가 구현 가능" 명시

### MINOR-10: v1.0 NuggetSettings에 language, theme 필드 추가 시 하위 호환성

v1.0에서 v1.1로 업데이트 시, 기존 사용자의 `nugget_settings`에는 `language`와 `theme` 필드가 없다. background.js의 `loadSettings()`가 `Object.assign({}, defaultSettings(), stored)`로 기본값과 병합하므로 새 필드가 자동으로 추가될 것이다. 그러나 이 병합이 v1.1의 새 기본값(`language: 'auto'`, `theme: 'system'`)을 올바르게 적용하려면, `defaultSettings()` 함수가 업데이트되어야 한다.

계획에는 이 마이그레이션 로직에 대한 AC가 없다. 기존 코드의 병합 로직으로 자연스럽게 처리되긴 하지만, "v1.0에서 v1.1 업데이트 시 기존 설정은 보존되고 새 설정은 기본값으로 추가된다"라는 AC가 있으면 QA 검증 기준이 명확해진다.

### MINOR-11: API 가로채기 성공 시 SAVE_ENTRY 메시지의 발신자 변경

v1.0에서 SAVE_ENTRY는 기존 Content Script(claude.js 등)가 발신했다. v1.1에서 API 캡처 성공 시에는 bridge.js가 API_CAPTURE 메시지를 Background에 보내고, Background가 저장한다. 이때 기존 Content Script의 SAVE_ENTRY 로직과 bridge.js의 API_CAPTURE 로직이 동시에 실행되면 중복 저장이 발생할 수 있다.

AC-V11-4에 "API 캡처 성공 시 DOM 셀렉터 방식 대신 API 데이터 사용"이라고 했으므로 둘이 동시에 동작하면 안 된다. 그러나 "API 캡처 성공 여부를 기존 Content Script가 어떻게 아는가?"에 대한 메커니즘이 AC에 없다. Background가 Content Script에 "API 캡처 성공했으니 DOM 감시 중지하라"는 메시지를 보내는 것인지, Content Script가 bridge.js의 상태를 확인하는 것인지, 아예 Content Script의 MutationObserver를 등록하지 않는 것인지 — 이 핵심 연동 로직이 누락되어 있다.

→ 중복 저장 방지는 데이터 무결성에 관련되므로 중요도를 높인다.

### CRITICAL-5: API 캡처와 DOM 셀렉터 간 중복 저장 방지 메커니즘 AC 누락

위 MINOR-11에서 서술한 문제를 CRITICAL로 격상한다.

API 가로채기(interceptor.js → bridge.js → Background)와 기존 DOM 셀렉터(claude.js 등 → Background)가 동일한 대화를 이중으로 캡처할 수 있다. AC-V11-4는 "API 캡처 성공 시 DOM 셀렉터 대신 사용"이라고만 했을 뿐, 두 경로의 동시 실행을 방지하는 구체적 메커니즘이 없다.

가능한 해결 방향:
1. Content Script에서 API 캡처 성공 여부 플래그를 공유하여 MutationObserver 등록/해제 제어
2. Background에서 해시 기반 중복 체크로 이중 저장 방지 (현재 v1.0에 해시 중복 체크가 있으나, API 캡처와 DOM 캡처가 미세하게 다른 텍스트를 추출하면 해시가 달라질 수 있음)
3. API 캡처 모드에서는 기존 Content Script의 DOM 감시를 완전히 비활성화

이 중 하나를 AC로 명시해야 한다.

---

## 종합 판정

### 치명적 결함 (CRITICAL): 3건

| # | 내용 |
|---|------|
| CRITICAL-1 | 플랫폼별 SSE 파서에 대한 AC 누락. 기술적 제약사항에서 필요성을 인정하면서 AC를 정의하지 않음 |
| CRITICAL-2 | AC-V11-4 "API 캡처 실패"의 정의가 모호. 개발자가 판단할 수 없음 |
| CRITICAL-5 | API 캡처와 DOM 셀렉터 간 중복 저장 방지 메커니즘 AC 누락. 데이터 무결성 위험 |

### 경미한 결함 (MINOR): 11건

| # | 내용 |
|---|------|
| MINOR-1 | bridge.js와 기존 Content Script의 역할 분담 미정의 |
| MINOR-2 | API 캡처 폴백 시 원격/로컬 셀렉터 우선순위 연계 미언급 |
| MINOR-3 | 원격 셀렉터 24시간 주기의 타이밍 기준 모호 |
| MINOR-4 | 원격 JSON 스키마 검증 기준 미정의 |
| MINOR-5 | 'auto' 언어 설정의 구체적 동작 미연결 |
| MINOR-6 | 다크모드에서 기존 색상 팔레트 "유지"의 해석 모호 |
| MINOR-7 | MAIN world + document_start 타이밍 보장에 대한 Pre-mortem 누락 |
| MINOR-8 | manifest.json MAIN world content_scripts 추가 방식 미명시 |
| MINOR-9 | src/shared/ 내 신규 파일 소유권과 CLAUDE.md 규칙 충돌 |
| MINOR-10 | v1.0→v1.1 설정 마이그레이션 AC 누락 |
| MINOR-11 | (CRITICAL-5로 격상됨) |

### 권고

CRITICAL 3건을 해결한 후 설계 단계로 진행할 것을 권고한다.
- CRITICAL-1, 2, 5는 모두 API 가로채기 기능의 핵심 동작에 관한 것으로, 설계자와 개발자가 각자 다른 해석을 할 위험이 크다.
- MINOR 사항은 설계 단계에서 자연스럽게 해소 가능하다.

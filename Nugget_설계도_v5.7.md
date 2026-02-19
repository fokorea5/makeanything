# Nugget 에이전트팀 설계도 v5.7

> 이 문서는 Nugget 프로젝트의 전체 설계 자료를 한 파일로 통합한 것입니다.
> 다른 세션에서 에이전트 팀을 기동할 때 이 파일을 참조하세요.

---

# PART 1: 실행 계획 (v1.0)

# .plan.md

## 프로젝트명
Nugget – AI Chat Memory (Chrome Extension)

## 요구사항 요약
AI 대화(Claude, ChatGPT, Gemini)를 자동 저장하고, 잡담은 걸러내고, 나중에 쉽게 찾는 크롬 확장 프로그램.
완전 로컬 저장 (서버 없음). Manifest V3 기반. Freemium 모델 (무료 500개 / Pro 무제한).

## AC (Acceptance Criteria)

### 자동 저장
- [ ] AC-1: Claude(claude.ai), ChatGPT(chatgpt.com, chat.openai.com), Gemini(gemini.google.com)에서 대화 완료 감지 후 질문+답변 자동 저장
- [ ] AC-2: MutationObserver로 스트리밍 완료 감지. DOM 셀렉터는 `src/config/selectors.js`로 분리
- [ ] AC-3: 셀렉터 작동 실패 시 확장 아이콘에 "!" 뱃지 + 팝업에서 "저장 안 됨" 안내
- [ ] AC-4: 복수 탭 독립 저장. 질문+답변+시간 조합 해시로 중복 방지

### 잡담 필터
- [ ] AC-5: 2단계 필터 — 1단계: 질문이 짧고(CJK 문자 포함: 15자 미만, 라틴 문자만: 5단어 미만) AND 답변 200자 미만 → isJunk:true. 2단계: 질문이 잡담 키워드 exact match → isJunk:true. 언어 판별: 질문 텍스트에 CJK 유니코드 범위(U+3000~U+9FFF, U+AC00~U+D7AF) 문자가 1개 이상 → 글자 수 기준, 아니면 단어 수 기준
- [ ] AC-6: 기본 키워드 목록 내장 + Options에서 사용자 추가/삭제 가능
- [ ] AC-7: 잡담은 삭제하지 않고 isJunk:true 마킹. "잡담 포함" 토글로 언제든 노출 가능

### 자동 태깅
- [ ] AC-8: 질문+답변 텍스트에서 키워드 매칭으로 복수 태그 자동 부여 (코딩/글쓰기/업무/학습/크리에이티브/기타)
- [ ] AC-9: 커스텀 태그 추가는 Pro 전용

### 검색 & 필터
- [ ] AC-10: 키워드 검색 (질문+답변+메모 전문), 플랫폼 필터, 기간 필터(오늘/이번주/이번달/직접설정), 태그 필터, 별표만, 잡담 포함/제외
- [ ] AC-11: 검색 결과에서 키워드 하이라이팅 (노란색)

### Markdown 복사
- [ ] AC-12: 각 카드 [MD] 버튼 → 클립보드에 마크다운 형식 복사. 코드블록 유지. 메모 있으면 블록쿼트 추가
- [ ] AC-13: 복사 시 "✓ 복사됨" 피드백. 무료 월 20회 / Pro 무제한

### 사용자 메모
- [ ] AC-14: 각 카드 메모 아이콘 → 텍스트 입력 → blur 시 자동 저장. 검색에 포함
- [ ] AC-15: 무료: 카드당 1개 200자 제한 / Pro: 무제한

### 별표 & 단축키
- [ ] AC-16: Ctrl+Shift+S로 가장 최근 엔트리에 별표 토글. 토스트 피드백

### 백업/복원
- [ ] AC-17: JSON 1클릭 내보내기. JSON 불러오기 (기존 데이터 병합, id 중복 제거)
- [ ] AC-18: 무료 사용자: 400개(80%) 도달 시 "백업 권장" 뱃지 + 500개 도달 시 "한도 도달 — 새 대화는 오래된 것을 숨김 처리합니다" 안내. Pro: 500개 단위 마일스톤 알림. Pro 전용: PDF/Markdown 내보내기

### 토스트 알림
- [ ] AC-19: 대화 저장 시 우측 하단 토스트 1.5~2초 "💾 Nugget이 저장했어요". 페이드 애니메이션. Options에서 끄기 가능

### Today's Nugget
- [ ] AC-20: 팝업 상단에 과거 대화 랜덤 1개 표시. "과거의 오늘" 우선. 클릭 시 이동. 닫기(X) 가능

### 온보딩
- [ ] AC-21: 설치 시 onboarding 페이지 열기. 안내 + 샘플 카드 + 단축키 + Pro 소개 (가볍게)

### Pro 결제 (ExtensionPay)
- [ ] AC-22: ExtensionPay 연동. Popup/Options에서 "Pro로 업그레이드" 버튼 → 결제 페이지 → isPro=true
- [ ] AC-23: 무료 한도 정책 — 저장 500개 초과 시 오래된 엔트리를 **삭제하지 않고 archived:true로 마킹** (숨김 처리). 아카이브된 엔트리는 Popup에서 보이지 않지만 storage에 보존됨. Pro 업그레이드 시 archived 해제되어 전체 열람 가능. MD 복사 월 20회 (매월 1일 0시 UTC 리셋), 커스텀 태그 잠금, 메모 200자
- [ ] AC-23a: 백업 복원 시 — 무료 사용자가 500개 초과 데이터를 복원하면 최신 500개만 활성, 나머지는 자동 archived:true. 데이터 손실 없음
- [ ] AC-24: 초과/잠금 시 부드러운 안내 "Pro로 업그레이드하면 무제한으로 사용할 수 있어요"
- [ ] AC-24a: Pro 상태 오프라인 정책 — ExtensionPay getUser() 결과를 로컬 캐싱 (7일 유효). 캐시 유효 기간 내 오프라인이면 캐시된 Pro 상태 유지. 캐시 만료 + 오프라인이면 Pro 기능 유지하되 "구독 확인 필요" 배너 표시 (기능 차단하지 않음)

### Popup UI
- [ ] AC-25: 설계서의 UI 와이어프레임 대로 구현: Today's Nugget → 검색 → 필터 → 카드 리스트 → 미니 통계 → 하단 버튼

### 데이터 구조
- [ ] AC-26: 엔트리 필드: id, date, platform, question, answer, tags[], starred, isJunk, archived, sourceUrl, note
- [ ] AC-27: 설정 필드: toastEnabled, junkFilterEnabled, shortcutKey, maxFreeEntries, isPro, proStatusCache:{paid, checkedAt}, mdCopyCount, mdCopyResetDate

### 기타
- [ ] AC-28: Service Worker 상태는 반드시 chrome.storage에 저장 (메모리 보관 금지 — MV3 생명주기)
- [ ] AC-29: CSP 준수: 인라인 스크립트 금지, 별도 JS 파일 사용
- [ ] AC-30: ExtensionPay CSP: connect-src에 https://extensionpay.com 추가

## 기술적 제약사항 (오라클 보고서 기반)
- ExtensionPay: Extension ID만으로 초기화 (API 키 불필요). npm `extpay` v3.1.2 안정판 사용
- MV3 서비스 워커에서 콜백 내부 extpay 재선언 필요 (컨텍스트 손실 문제)
- 오프라인 시 `getUser()` 실패 가능 → `.catch()` 필수
- ExtensionPay 수수료: 거래당 5% + Stripe 2.9%+$0.30
- chrome.storage.local 기본 10MB. unlimitedStorage 권한 고려

## 세포 분화 (에이전트 편성)
- 유형: 풀스택 + 결제/보안 포함 (8명)
- 코어: 설계자, UI디자이너, backend, frontend, QA
- On-Demand: 비판자 (PLAN 비판), 보안 (결제 포함이므로 필수), DevOps (패키징)

## 기술 스택
- Manifest V3 Chrome Extension
- 저장: chrome.storage.local (+ unlimitedStorage 권한)
- 결제: ExtensionPay (extpay npm v3.1.2)
- UI: Vanilla JS + CSS (경량화 우선, 의존성 최소화)
- 빌드: 없음 (번들러 불필요 — Vanilla JS)
- 구조: Content Script (플랫폼별) + Background Service Worker + Popup + Options + Onboarding

## 작업 순서
1. 설계자 → DESIGN.md + src/shared/ ∥ UI디자이너 → ui_design.md (병렬)
2. backend(Service Worker + Content Scripts) ∥ frontend(Popup + Options + Onboarding) (병렬)
3. QA + 보안 (병렬)
4. 투기적: DevOps (Chrome Web Store 패키징 가이드)

## 전달 방식
소스코드 (Chrome Extension 디렉토리). 개발자 대상이 아닌 최종 사용자용이므로 README에 로드 방법 안내.

## Pre-mortem
1. 실패 시나리오: AI 사이트 DOM 구조 변경으로 셀렉터 깨짐 → 대응: 셀렉터를 config로 분리하여 핫패치 가능. 셀렉터 실패 시 사용자에게 즉시 알림
2. 실패 시나리오: chrome.storage.local 10MB 한도 초과 → 대응: unlimitedStorage 권한 요청. 무료 500개 제한으로 실질적 부담 낮음. 답변 길이 극단적 케이스 대비 압축 고려
3. 실패 시나리오: ExtensionPay 서비스 중단 또는 결제 오류 → 대응: Pro 상태 로컬 캐싱 (7일, AC-24a 참조). 최악의 경우 graceful degradation (무료 기능은 항상 동작, Pro 기능도 차단하지 않고 확인 배너만 표시)


---

# PART 2: 실행 계획 (v1.1 업그레이드)

# .plan.v1.1.md — Nugget v1.1 업그레이드

## 사용자 원문
> 응 그리고 근데 이거 ui가 언어를 선택할수있는 설정도 있어야하고 다크모드도 설정으로 넣으면 좋을거 같네.

(이전 대화에서 API 가로채기 + 원격 셀렉터 핫패치도 요청됨)

## 요구사항 요약
Nugget v1.0 (기존 완성본)에 4가지 핵심 개선 사항 추가:
1. **API 가로채기** — DOM 셀렉터 대신 fetch monkey-patch로 AI 응답 직접 캡처 (메인)
2. **원격 셀렉터 핫패치** — GitHub Raw JSON으로 셀렉터 원격 업데이트 (백업)
3. **다국어 (i18n)** — 한국어/영어 선택 가능한 UI 언어 설정
4. **다크모드** — 라이트/다크/시스템 테마 설정

## AC (Acceptance Criteria) — v1.1

### API 가로채기 (메인 캡처)
- [ ] AC-V11-1: MAIN world에서 `window.fetch`를 오버라이드하여 claude.ai, chatgpt.com, gemini.google.com의 SSE 스트리밍 응답을 `ReadableStream.tee()`로 복제해서 읽음
- [ ] AC-V11-1a: 플랫폼별 SSE 파서 구현. Claude: `content_block_delta` 이벤트에서 `delta.text` 추출. ChatGPT: `data:` 라인에서 `message.content.parts[]` 추출. Gemini: 응답 본문에서 텍스트 청크 추출. 파싱 실패(빈 데이터 또는 예외) 시 해당 대화는 DOM 셀렉터 폴백으로 전환
- [ ] AC-V11-2: ISOLATED world의 bridge 스크립트가 CustomEvent로 데이터를 수신하여 `chrome.runtime.sendMessage`로 Background에 전달. bridge.js는 API 캡처 데이터를 Background로 전달하는 역할만 수행. 기존 Content Script(claude.js 등)는 DOM 셀렉터 폴백 전용으로 유지
- [ ] AC-V11-3: `document_start`에서 실행되어 페이지의 첫 fetch 호출 전에 오버라이드 완료. manifest.json에 기존 ISOLATED world content_scripts는 유지하고, 새 MAIN world 항목(interceptor.js)과 ISOLATED world 항목(bridge.js)을 별도 항목으로 추가
- [ ] AC-V11-4: API 캡처 성공 시 DOM 셀렉터 방식 대신 API 데이터 사용. "API 캡처 실패"의 정의: API 데이터로 question+answer 추출을 완료하지 못한 모든 경우 (fetch 오버라이드 미실행, SSE 파싱 빈 데이터, 스트림 중단, URL 패턴 미매칭 포함). 실패 시 기존 DOM 셀렉터로 자동 폴백
- [ ] AC-V11-4a: 중복 저장 방지: Background가 API_CAPTURE로 대화 저장 성공 시, 해당 대화의 해시를 기록. 기존 Content Script의 SAVE_ENTRY가 동일 해시로 도착하면 무시. 추가로, 기존 Content Script는 API 캡처가 활성화된 탭에서 MutationObserver의 SAVE_ENTRY 발송 전 500ms 지연을 두어 API_CAPTURE가 먼저 처리될 여지를 줌
- [ ] AC-V11-5: 원본 페이지의 기능에 영향 없음 (tee()로 스트림 복제하므로 원본 유지)

### 원격 셀렉터 핫패치 (백업)
- [ ] AC-V11-6: Background에서 GitHub Raw JSON URL로부터 최신 셀렉터를 주기적(24시간)으로 가져옴
- [ ] AC-V11-7: 원격 셀렉터를 `nugget_remote_selectors` 스토리지 키에 캐시. 오프라인 시 캐시 사용
- [ ] AC-V11-8: 원격 셀렉터가 있으면 로컬 `selectors.js`보다 우선 적용
- [ ] AC-V11-9: 원격 JSON 형식 검증 후 적용 (스키마 불일치 시 무시)

### 다국어 (i18n)
- [ ] AC-V11-10: Popup, Options, Onboarding의 모든 사용자 표시 문자열을 i18n 처리
- [ ] AC-V11-11: 지원 언어: 한국어(ko), 영어(en). 기본값: 브라우저 언어 감지 → 없으면 ko
- [ ] AC-V11-12: Options 설정에서 언어 수동 선택 가능. 변경 시 Options 페이지는 즉시 반영 (DOM 직접 조작). Popup은 다음 열 때 반영. Content Script 토스트는 chrome.storage.onChanged로 반영
- [ ] AC-V11-13: `nugget_settings.language` 필드 추가 ('ko' | 'en' | 'auto'). 'auto'일 때: navigator.language로 감지 → 'ko'로 시작하면 ko, 'en'으로 시작하면 en, 그 외 미지원 언어는 ko 폴백
- [ ] AC-V11-14: 토스트 메시지도 선택 언어에 따라 표시

### 다크모드
- [ ] AC-V11-15: CSS 커스텀 속성(변수)으로 테마 색상 관리. 라이트/다크/시스템 3가지 모드
- [ ] AC-V11-16: Options 설정에서 테마 선택. 기본값: 'system' (OS 다크모드 따라감)
- [ ] AC-V11-17: `nugget_settings.theme` 필드 추가 ('light' | 'dark' | 'system')
- [ ] AC-V11-18: Popup, Options, Onboarding 모든 페이지에 다크모드 적용
- [ ] AC-V11-19: 기존 색상 팔레트(Nugget Gold, 플랫폼 컬러 등) 유지하면서 다크 배경 적용
- [ ] AC-V11-20: `prefers-color-scheme` 미디어 쿼리로 시스템 테마 변경 실시간 감지

## 기술적 제약사항

### API 가로채기
- MV3 `"world": "MAIN"` + `"run_at": "document_start"` 조합 사용
- CSP 영향 없음 (manifest 선언 방식이므로)
- ChatGPT, Claude.ai 모두 native EventSource 아닌 fetch 기반 SSE 사용
- SSE 데이터 형식은 사이트마다 다름 → 플랫폼별 파서 필요

### 원격 셀렉터
- GitHub Raw는 무료. CDN 캐시 5분. 충분함
- Rate limit: IP당 60req/hour → 24시간 주기이면 문제 없음

### i18n
- Chrome 확장의 `chrome.i18n.getMessage()`는 런타임 언어 변경 불가
- 따라서 자체 i18n 시스템 구현 (JSON 사전 + JS 헬퍼)
- `_locales/`는 manifest의 `default_locale` 용도로만 사용

## 세포 분화 (에이전트 편성)
- 유형: 풀스택 업데이트 (6명)
- 비판자 — PLAN 비판
- 설계자 — DESIGN.md v1.1 업데이트 (새 파일, 타입, 메시지 계약)
- UI디자이너 — 다크모드 테마 + 설정 UI 디자인 (설계자와 병렬)
- backend — API 가로채기, 원격 셀렉터, i18n 백엔드, 테마 관리
- frontend — 다국어 UI 적용, 다크모드 CSS, 설정 페이지 업데이트
- QA — 전체 검증

## 작업 순서
1. 설계자 → DESIGN.md v1.1 업데이트 ∥ UI디자이너 → 다크모드 테마/설정 UI (병렬)
2. backend(API 가로채기 + 원격 셀렉터 + i18n 백엔드) ∥ frontend(다국어 UI + 다크모드 CSS + 설정) (병렬)
3. QA 전체 검증

### v1.0→v1.1 마이그레이션
- [ ] AC-V11-21: v1.0에서 v1.1 업데이트 시 기존 설정은 보존되고, 새 설정(language: 'auto', theme: 'system')은 기본값으로 추가됨. DEFAULT_SETTINGS에 새 필드 반영 필수

## 새 파일 목록
| 파일 | 담당 | 설명 |
|------|------|------|
| `src/content/interceptor.js` | Backend | MAIN world fetch 오버라이드 |
| `src/content/bridge.js` | Backend | ISOLATED world 브릿지 |
| `src/utils/i18n.js` | Backend | i18n 유틸리티 (shared가 아닌 utils 경로 — 설계자 소유권 충돌 방지) |
| `src/utils/theme.js` | Backend | 테마 관리 유틸리티 |
| `src/i18n/ko.json` | Frontend | 한국어 번역 |
| `src/i18n/en.json` | Frontend | 영어 번역 |

## 수정 파일 목록
| 파일 | 담당 | 변경 내용 |
|------|------|----------|
| `manifest.json` | Backend | MAIN world content_scripts 추가 |
| `src/shared/types.js` | Architect | NuggetSettings에 language, theme 추가 |
| `src/shared/constants.js` | Architect | i18n, theme 관련 상수 추가 |
| `src/background/background.js` | Backend | API_CAPTURE 메시지 처리, 원격 셀렉터 fetch |
| `src/content/claude.js` | Backend | API 캡처 폴백 로직 |
| `src/content/chatgpt.js` | Backend | API 캡처 폴백 로직 |
| `src/content/gemini.js` | Backend | API 캡처 폴백 로직 |
| `src/config/selectors.js` | Backend | 원격 셀렉터 머지 로직 |
| `src/popup/popup.html` | Frontend | i18n data 속성, 테마 클래스 |
| `src/popup/popup.js` | Frontend | i18n 적용, 테마 초기화 |
| `src/popup/popup.css` | Frontend | CSS 변수 기반 다크모드 |
| `src/options/options.html` | Frontend | 언어/테마 설정 UI, i18n |
| `src/options/options.js` | Frontend | 언어/테마 설정 로직 |
| `src/options/options.css` | Frontend | CSS 변수 기반 다크모드 |
| `src/onboarding/onboarding.html` | Frontend | i18n, 테마 |
| `src/onboarding/onboarding.js` | Frontend | i18n, 테마 초기화 |
| `src/onboarding/onboarding.css` | Frontend | CSS 변수 기반 다크모드 |

## 통합 계약 추가 (v1.1)

### 새 메시지 타입
```
Content(MAIN→bridge) → Background
'API_CAPTURE'         // { platform, question, answer, sourceUrl, rawChunks? }

Background 내부
'FETCH_REMOTE_SELECTORS'  // 주기적 알람
```

### 새 Storage 키
```
'nugget_remote_selectors'  // { version, selectors: SelectorsConfig, fetchedAt: ISO }
```

### NuggetSettings 추가 필드
```
language: 'ko' | 'en' | 'auto'   // 기본: 'auto'
theme: 'light' | 'dark' | 'system'  // 기본: 'system'
```

## Pre-mortem (v1.1)
1. **API 엔드포인트 변경**: AI 사이트가 API URL이나 응답 형식을 변경하면 캡처 실패 → 대응: DOM 셀렉터 폴백이 자동 작동. 엔드포인트 패턴을 config로 분리하여 핫패치 가능
2. **fetch 오버라이드 자체 무력화**: Gemini(Google)의 Trusted Types, ChatGPT의 Service Worker 중계 등으로 MAIN world fetch 패치가 작동하지 않을 수 있음 → 대응: DOM 셀렉터 폴백이 자동 작동. 플랫폼별 독립적이므로 하나가 실패해도 나머지는 정상
3. **i18n 번역 누락**: 새 기능 추가 시 번역 키 누락 가능 → 대응: 폴백 언어(ko) 자동 사용. QA에서 전수 검증
4. **MAIN world + document_start 타이밍 경합**: 극히 드물지만 페이지 인라인 스크립트가 먼저 실행될 가능성 → 대응: 이 경우 DOM 셀렉터 폴백 사용. Chrome 111+ 대부분 정상 동작

## 전달 방식
기존 v1.0 소스코드에 업데이트 적용 (Chrome Extension 디렉토리).


---

# PART 3: 설계서 (DESIGN.md)

# DESIGN.md — Nugget: AI Chat Memory (Chrome Extension)

설계일: 2026-02-18 (v1.0) / 2026-02-18 (v1.1 업데이트)
설계자: 기술 아키텍트
참조: `.plan.md`, `.plan.v1.1.md`, `reports/oracle_report.md`, `reports/critique_report.md`, `reports/critique_v1.1_report.md`

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
│   │   ├── interceptor.js          # [v1.1] MAIN world fetch 오버라이드 (API 가로채기)
│   │   ├── bridge.js               # [v1.1] ISOLATED world 브릿지 (CustomEvent → sendMessage)
│   │   ├── claude.js               # claude.ai 전용 Content Script (DOM 셀렉터 폴백)
│   │   ├── chatgpt.js              # chatgpt.com / chat.openai.com 전용 Content Script (DOM 셀렉터 폴백)
│   │   ├── gemini.js               # gemini.google.com 전용 Content Script (DOM 셀렉터 폴백)
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
│   ├── utils/                       # [v1.1] 유틸리티 (Backend 소유)
│   │   ├── i18n.js                  # [v1.1] 자체 i18n 시스템
│   │   └── theme.js                 # [v1.1] 테마 관리
│   ├── i18n/                        # [v1.1] 번역 파일 (Frontend 소유)
│   │   ├── ko.json                  # [v1.1] 한국어 번역
│   │   └── en.json                  # [v1.1] 영어 번역
│   └── lib/
│       └── ExtPay.js               # ExtensionPay 라이브러리 (npm extpay v3.1.2에서 복사)
├── assets/
│   ├── icon-16.png
│   ├── icon-32.png
│   ├── icon-48.png
│   └── icon-128.png
└── _locales/                        # manifest default_locale 용도 (런타임 i18n은 src/utils/i18n.js 사용)
```

**결정 이유:**
- Content Script를 플랫폼별로 분리한 이유: 각 AI 사이트의 DOM 구조가 완전히 다르므로 하나의 파일에 합치면 유지보수가 어려움. 셀렉터 실패 시 해당 사이트만 수정하면 됨.
- `src/config/selectors.js` 분리: AC-2 요구사항. DOM 구조 변경 시 이 파일만 수정하면 핫패치 가능 (Pre-mortem 1번 대응).
- `src/lib/ExtPay.js`: 번들러 없이 직접 파일 복사 방식 사용. npm에서 `extpay@3.1.2`의 `dist/ExtPay.js`를 복사.
- `extpay-content.js`: ExtensionPay의 `onPaid` 콜백을 받기 위해 `extensionpay.com`에 주입되는 Content Script (oracle_report.md 참조).
- **[v1.1]** `interceptor.js` + `bridge.js` 분리: MAIN world와 ISOLATED world는 별도 실행 컨텍스트이므로 파일을 분리해야 함. interceptor는 MAIN world에서 fetch를 패치하고, bridge는 ISOLATED world에서 chrome.runtime API에 접근하여 Background로 전달.
- **[v1.1]** `src/utils/` vs `src/shared/`: CLAUDE.md 규칙상 `src/shared/`는 설계자만 수정 가능. i18n.js와 theme.js는 Backend가 구현해야 하므로 `src/utils/`에 배치 (비판자 MINOR-9 반영).
- **[v1.1]** `src/i18n/`: 번역 JSON 파일. Chrome의 `chrome.i18n.getMessage()`는 런타임 언어 변경이 불가하므로, 자체 i18n 시스템에서 이 JSON을 직접 로드하여 사용.

---

## 3. manifest.json 설계

> **v1.1 변경사항:** `"alarms"` 권한 추가, MAIN world `interceptor.js`와 ISOLATED world `bridge.js` content_scripts 항목 추가, 버전 `1.1.0`으로 변경.

```json
{
  "manifest_version": 3,
  "name": "Nugget – AI Chat Memory",
  "version": "1.1.0",
  "description": "AI 대화를 자동 저장하고 나중에 쉽게 찾으세요",
  "permissions": [
    "storage",
    "unlimitedStorage",
    "activeTab",
    "alarms"
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
      "matches": ["https://claude.ai/*", "https://chatgpt.com/*", "https://chat.openai.com/*", "https://gemini.google.com/*"],
      "js": ["src/content/interceptor.js"],
      "run_at": "document_start",
      "world": "MAIN"
    },
    {
      "matches": ["https://claude.ai/*", "https://chatgpt.com/*", "https://chat.openai.com/*", "https://gemini.google.com/*"],
      "js": ["src/content/bridge.js"],
      "run_at": "document_start"
    },
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
- **[v1.1]** `alarms`: 원격 셀렉터 24시간 주기 fetch용 `chrome.alarms` API 권한 (AC-V11-6).
- Content Scripts에 `types.js`와 `selectors.js`를 주입: Content Script에서 타입 상수와 셀렉터에 접근 가능하게 함.
- `run_at: "document_idle"`: AI 사이트가 렌더링 완료된 후 스크립트 실행.
- `run_at: "document_start"` (ExtensionPay): oracle_report.md에서 요구하는 설정 그대로.
- CSP에 `connect-src https://extensionpay.com`: AC-30 요구사항.
- **[v1.1]** `interceptor.js` (`world: "MAIN"`, `run_at: "document_start"`): 페이지의 첫 fetch 호출 전에 오버라이드를 완료하기 위해 `document_start`에서 MAIN world로 주입 (AC-V11-3). 3개 AI 사이트 모두에 동일한 interceptor를 주입하고, 내부에서 URL 패턴으로 플랫폼을 판별한다.
- **[v1.1]** `bridge.js` (기본 ISOLATED world, `run_at: "document_start"`): interceptor.js가 발생시키는 CustomEvent를 수신하여 `chrome.runtime.sendMessage`로 Background에 전달. `document_start`에서 실행해야 interceptor보다 먼저 이벤트 리스너를 등록할 수 있다. ISOLATED world이므로 `chrome.runtime` API 접근 가능.
- **[v1.1]** 기존 ISOLATED world content_scripts(claude.js, chatgpt.js, gemini.js)는 그대로 유지. DOM 셀렉터 폴백 전용 (비판자 MINOR-1, MINOR-8 반영).

---

## 4. 메시징 아키텍처

Content Script와 Background(Service Worker) 사이의 모든 통신은 `chrome.runtime.sendMessage`를 사용한다.
Popup/Options/Onboarding과 Background 사이도 동일하다.

### 4.1 메시지 흐름도

> **v1.1 업데이트:** API 가로채기 경로 추가. interceptor.js는 MAIN world에서 CustomEvent로 bridge.js에 전달하고, bridge.js가 `chrome.runtime.sendMessage`로 Background에 전달한다.

```
[interceptor.js]  --CustomEvent-->  [bridge.js]  --sendMessage-->  [Background Service Worker]
  (MAIN world)                     (ISOLATED)        |                  (background.js)
                                                     |                       |
[Content Script]  --sendMessage--> (DOM 셀렉터 폴백)--+   <--sendMessage--  [Popup / Options / Onboarding]
   (claude.js)                                                               (popup.js / options.js)
   (chatgpt.js)                                                               |
   (gemini.js)                                                          chrome.storage.local
```

### 4.2 메시지 타입 정의

모든 메시지는 `{ type: string, payload: object }` 형식을 따른다.

| 방향 | type | payload | 응답 | 설명 |
|------|------|---------|------|------|
| Content -> BG | `SAVE_ENTRY` | `{ question, answer, platform, sourceUrl }` | `{ success, entry?, error? }` | 대화 감지 후 저장 요청 |
| Content -> BG | `SELECTOR_FAILED` | `{ platform, selector, error }` | `{ success }` | 셀렉터 작동 실패 알림 (AC-3) |
| **[v1.1]** bridge -> BG | `API_CAPTURE` | `{ platform, question, answer, sourceUrl }` | `{ success, entry?, error? }` | API 가로채기로 캡처한 대화 저장 (AC-V11-2) |
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
- **[v1.1]** `API_CAPTURE`: bridge.js가 interceptor.js로부터 수신한 API 캡처 데이터를 Background에 전달. Background는 `saveEntry()`와 동일한 파이프라인(해시, 잡담필터, 태깅, 한도체크)을 수행하되, 저장 성공 시 해시를 `nugget_api_capture_hashes`에 기록하여 후속 SAVE_ENTRY 중복을 방지 (비판자 CRITICAL-5 해결).

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
| **[v1.1]** `nugget_remote_selectors` | `RemoteSelectorsCache` | 원격 셀렉터 캐시 (AC-V11-7) |
| **[v1.1]** `nugget_api_capture_hashes` | `string[]` | API 캡처로 저장된 엔트리 해시 목록 — 중복 저장 방지용 (AC-V11-4a) |

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
  mdCopyResetDate: string,    // MD 복사 카운터 리셋 날짜 (ISO date, 매월 1일 0시 UTC, AC-23)
  language: string,           // [v1.1] UI 언어 ('ko' | 'en' | 'auto') (기본: 'auto') (AC-V11-13)
  theme: string               // [v1.1] 테마 ('light' | 'dark' | 'system') (기본: 'system') (AC-V11-17)
}
```

> **[v1.1] 마이그레이션 (AC-V11-21):** v1.0 사용자가 v1.1로 업데이트하면 기존 `nugget_settings`에 `language`, `theme` 필드가 없다. `loadSettings()`의 `Object.assign({}, defaultSettings(), stored)` 병합 로직에 의해 새 필드가 기본값(`language: 'auto'`, `theme: 'system'`)으로 자동 추가된다. `defaultSettings()` 함수에 이 두 필드를 반드시 포함해야 한다.

> **[v1.1] `language: 'auto'` 동작 (AC-V11-13, 비판자 MINOR-5 해결):** 'auto'일 때 `navigator.language`를 확인하여, 'ko'로 시작하면 `'ko'`, 'en'으로 시작하면 `'en'`, 그 외 미지원 언어이면 `'ko'` 폴백.

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

---

## 13. [v1.1] API 가로채기 아키텍처 (AC-V11-1 ~ AC-V11-5)

### 13.1 개요

v1.0은 DOM 셀렉터(MutationObserver)로 대화를 감지했다. v1.1은 `window.fetch` 오버라이드를 통해 AI 플랫폼의 SSE 스트리밍 응답을 직접 캡처하는 방식을 **메인 캡처 경로**로 추가한다. 기존 DOM 셀렉터 방식은 **폴백**으로 유지한다.

**아키텍처 흐름:**

```
[페이지의 fetch 호출]
  → [interceptor.js (MAIN world)] window.fetch 오버라이드
    → ReadableStream.tee()로 스트림 복제
    → 복제된 스트림을 플랫폼별 SSE 파서로 파싱
    → 파싱 완료 시 CustomEvent('__nugget_api_capture__')로 데이터 전달
  → [bridge.js (ISOLATED world)] CustomEvent 리스너
    → chrome.runtime.sendMessage({ type: 'API_CAPTURE', payload })
  → [background.js] API_CAPTURE 메시지 수신
    → saveEntry() 동일 파이프라인 (해시, 잡담필터, 태깅, 한도)
    → 저장 성공 시 해시를 nugget_api_capture_hashes에 기록
    → 후속 SAVE_ENTRY가 같은 해시로 도착하면 무시 (중복 방지)
```

### 13.2 interceptor.js 상세 설계

**실행 환경:** MAIN world, `document_start`

**역할:** `window.fetch`를 오버라이드하여 AI 사이트의 SSE 스트리밍 응답을 가로챔.

**플랫폼 판별:**
```
const host = window.location.hostname;
if (host === 'claude.ai') → 'claude'
if (host === 'chatgpt.com' || host === 'chat.openai.com') → 'chatgpt'
if (host.endsWith('gemini.google.com')) → 'gemini'
```

**fetch 오버라이드 로직:**
```
1. 원본 fetch를 변수에 보관: const _originalFetch = window.fetch;
2. window.fetch를 새 함수로 교체:
   a. _originalFetch(url, options)를 호출하여 원본 Response 획득
   b. URL이 API 엔드포인트 패턴과 매칭되는지 확인
   c. 매칭되면:
      - response.body.tee()로 스트림 복제 (AC-V11-5: 원본 유지)
      - 복제된 스트림(stream2)을 플랫폼별 SSE 파서에 전달
      - 원본 스트림(stream1)으로 새 Response를 만들어 호출자에게 반환
   d. 매칭 안 되면: 원본 Response 그대로 반환
```

**API 엔드포인트 패턴:**
```js
const API_PATTERNS = {
  claude: /\/api\/.*\/completion/,         // claude.ai/api/.../completion
  chatgpt: /\/backend-api\/conversation/,  // chatgpt.com/backend-api/conversation
  gemini: /\/batchexecute\?/               // gemini.google.com/...batchexecute?...
};
```

> 이 패턴은 변경될 수 있으므로, interceptor.js 내부에 상수로 선언하여 핫패치 가능하게 한다. 향후 원격 셀렉터와 마찬가지로 원격 업데이트도 고려 가능하나 v1.1 범위에서는 로컬만.

### 13.3 플랫폼별 SSE 파서 (AC-V11-1a, 비판자 CRITICAL-1 해결)

interceptor.js 내부에 플랫폼별 파서 함수를 정의한다. 각 파서는 복제된 ReadableStream을 소비하고, 질문과 답변 텍스트를 추출한다.

**공통 시그니처:**
```js
/**
 * SSE 스트림을 파싱하여 답변 텍스트를 추출
 * @param {ReadableStream} stream - tee()로 복제된 응답 스트림
 * @param {string} requestBody - fetch 요청 body (질문 추출용)
 * @returns {Promise<{ question: string, answer: string } | null>}
 *   null 반환 시 = 파싱 실패 → DOM 셀렉터 폴백 (AC-V11-4)
 */
```

**Claude 파서 (`parseClaudeSSE`):**
```
SSE 형식: "event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}\n\n"
1. TextDecoderStream으로 스트림을 텍스트로 변환
2. 줄 단위로 파싱:
   - "event: content_block_delta" 이벤트 감지
   - 바로 다음 "data: " 줄에서 JSON 파싱 → delta.text 추출
   - 모든 delta.text를 이어붙임 → answer
3. 질문은 requestBody (JSON)에서 추출: body.prompt 또는 body.messages의 마지막 user 메시지
4. 스트림 끝까지 읽으면 { question, answer } 반환
5. 예외 또는 빈 answer → null 반환 (폴백)
```

**ChatGPT 파서 (`parseChatGPTSSE`):**
```
SSE 형식: "data: {"id":"...","message":{"content":{"parts":["..."]}}}\n\n"
1. TextDecoderStream으로 텍스트 변환
2. "data: " 접두사가 붙은 줄을 모두 수집
3. 마지막 유효한 data 줄의 JSON에서 message.content.parts[] 추출 → answer
   (ChatGPT SSE는 점진적으로 전체 텍스트를 보내므로 마지막 data의 parts가 최종 답변)
4. "data: [DONE]" 수신 시 스트림 종료
5. 질문은 requestBody에서 추출: body.messages의 마지막 user role content
6. 예외 또는 빈 answer → null 반환 (폴백)
```

**Gemini 파서 (`parseGeminiResponse`):**
```
Gemini는 표준 SSE가 아닌 JSON 배열 응답을 사용할 수 있음.
1. TextDecoderStream으로 텍스트 변환
2. 전체 응답 본문을 수집
3. JSON으로 파싱 시도 → 텍스트 청크 추출
4. 파싱 실패가 가장 빈번할 플랫폼이므로, 실패 시 조용히 null 반환 (폴백)
5. 질문은 requestBody에서 추출 시도, 실패 시 null
```

**"파싱 실패"의 정의 (AC-V11-4, 비판자 CRITICAL-2 해결):**
- API 데이터로 question + answer 추출을 완료하지 못한 **모든** 경우:
  - fetch 오버라이드 자체가 실행되지 않은 경우
  - URL 패턴이 매칭되지 않아 가로채기를 하지 않은 경우
  - SSE 파싱에서 빈 데이터(answer가 빈 문자열)가 나온 경우
  - 스트림 읽기 중 예외가 발생한 경우
  - ReadableStream.tee()가 지원되지 않는 경우
- 어떤 경우든 null을 반환하면, 기존 DOM 셀렉터 Content Script가 MutationObserver로 대화를 감지하여 SAVE_ENTRY를 보내는 **기존 폴백 경로**가 작동함.

### 13.4 bridge.js 상세 설계

**실행 환경:** ISOLATED world (기본), `document_start`

**역할:** interceptor.js(MAIN world)가 발생시키는 CustomEvent를 수신하여 `chrome.runtime.sendMessage`로 Background에 전달. **이 파일은 이 한 가지 역할만 수행** (비판자 MINOR-1 해결).

```
document.addEventListener('__nugget_api_capture__', (e) => {
  const data = e.detail;
  if (!data || !data.platform || !data.answer) return;
  chrome.runtime.sendMessage({
    type: 'API_CAPTURE',
    payload: {
      platform: data.platform,
      question: data.question || '',
      answer: data.answer,
      sourceUrl: window.location.href
    }
  });
});
```

**CustomEvent 데이터 형식 (interceptor → bridge):**
```js
document.dispatchEvent(new CustomEvent('__nugget_api_capture__', {
  detail: {
    platform: 'claude' | 'chatgpt' | 'gemini',
    question: string,
    answer: string
  }
}));
```

### 13.5 중복 저장 방지 메커니즘 (AC-V11-4a, 비판자 CRITICAL-5 해결)

API 가로채기(API_CAPTURE)와 DOM 셀렉터(SAVE_ENTRY)가 동일한 대화를 이중으로 저장하는 것을 방지한다.

**전략: Background에서 해시 기반 차단 + Content Script에서 지연 발송**

```
1. Background 측:
   - API_CAPTURE 메시지 수신 → saveEntry() 파이프라인 실행
   - 저장 성공 시, 해당 엔트리의 hash를 nugget_api_capture_hashes 배열에 추가
   - SAVE_ENTRY 메시지 수신 시, 해시 생성 후 nugget_api_capture_hashes에 존재하면 무시
   - nugget_api_capture_hashes는 최근 100개까지만 유지 (메모리/스토리지 절약)

2. Content Script 측 (claude.js, chatgpt.js, gemini.js):
   - MutationObserver의 SAVE_ENTRY 발송 전 500ms 지연을 추가 (기존 debounce 1초 + 추가 500ms)
   - 이 지연은 API_CAPTURE가 먼저 Background에 도달하여 해시를 기록할 여유를 줌
   - 총 지연: debounce 1초(스트리밍 완료 판단) + 500ms(중복 방지 대기) = 1.5초
```

**결정 이유:**
- Background에서 해시로 필터링하므로, API 캡처와 DOM 캡처의 텍스트가 미세하게 다르더라도(공백, 마크다운 등) answer 앞 200자 기준 해시가 동일하면 차단됨.
- Content Script를 완전히 비활성화하지 않는 이유: API 캡처가 실패할 경우(파싱 실패, URL 미매칭 등) DOM 셀렉터 폴백이 반드시 작동해야 하므로 MutationObserver는 항상 활성 상태를 유지해야 함.

---

## 14. [v1.1] 원격 셀렉터 핫패치 (AC-V11-6 ~ AC-V11-9)

### 14.1 개요

AI 사이트의 DOM 구조가 변경되면 `src/config/selectors.js`의 셀렉터가 깨진다. v1.1은 GitHub Raw JSON에서 최신 셀렉터를 주기적으로 가져와 로컬 셀렉터를 대체하는 메커니즘을 추가한다.

### 14.2 원격 셀렉터 fetch 로직 (background.js)

```
함수: fetchRemoteSelectors()

1. REMOTE_SELECTORS_URL (constants.js에 정의)에서 JSON fetch
2. 응답 검증:
   - HTTP 200 확인
   - JSON 파싱
   - 스키마 검증: { version: string, selectors: { claude: PlatformSelectors, chatgpt: PlatformSelectors, gemini: PlatformSelectors } }
   - 각 PlatformSelectors에 conversationContainer, userMessage, assistantMessage, streamingIndicator 키 존재 확인
   - 검증 실패 시 원격 데이터 무시 (로컬 유지)
3. 검증 통과 시:
   - nugget_remote_selectors에 저장: { version, selectors, fetchedAt: new Date().toISOString() }
```

### 14.3 RemoteSelectorsCache 스키마

```js
{
  version: string,              // 원격 셀렉터 버전 (예: "1.0.1")
  selectors: SelectorsConfig,   // { claude, chatgpt, gemini } 각각 PlatformSelectors
  fetchedAt: string             // 마지막 fetch 시각 (ISO 8601)
}
```

### 14.4 주기적 fetch (chrome.alarms)

```
- 알람 이름: 'fetch_remote_selectors'
- 주기: 24시간 (periodInMinutes: 1440)
- 등록 시점: chrome.runtime.onInstalled 및 Service Worker 시작 시
- 알람 트리거 시: fetchRemoteSelectors() 호출
- 최초 실행: 설치 직후 1회 즉시 실행 (delayInMinutes: 1)
```

### 14.5 셀렉터 우선순위 (selectors.js 수정)

기존 Content Script에서 `SELECTORS[platform]`으로 셀렉터를 가져올 때:

```
1. chrome.storage.local에서 nugget_remote_selectors 로드
2. 원격 셀렉터가 있고 fetchedAt이 유효하면 → 원격 셀렉터의 해당 플랫폼 사용
3. 없으면 → 로컬 SELECTORS 상수 사용 (기존 동작)
```

> 이 로직은 기존 Content Script(claude.js 등)에서 셀렉터를 사용하기 전에 수행한다. `selectors.js`에 `getSelectors(platform)` 비동기 헬퍼를 추가하여 원격/로컬 병합을 처리한다.

**결정 이유:** 원격 셀렉터가 로컬보다 우선 (AC-V11-8). API 캡처 폴백 시에도 원격 우선 적용 (비판자 MINOR-2 해결).

---

## 15. [v1.1] i18n 아키텍처 (AC-V11-10 ~ AC-V11-14)

### 15.1 개요

Chrome의 `chrome.i18n.getMessage()`는 런타임에 언어를 변경할 수 없으므로, 자체 i18n 시스템을 구현한다.

### 15.2 번역 파일 구조 (src/i18n/)

```json
// src/i18n/ko.json (예시)
{
  "popup_title": "Nugget",
  "popup_search_placeholder": "검색어를 입력하세요",
  "popup_filter_all": "전체",
  "popup_filter_today": "오늘",
  "popup_filter_week": "이번 주",
  "popup_filter_month": "이번 달",
  "popup_starred_only": "별표만",
  "popup_include_junk": "잡담 포함",
  "toast_saved": "Nugget이 저장했어요",
  "toast_star_added": "별표 추가됨",
  "toast_star_removed": "별표 해제됨",
  "toast_copied": "복사됨",
  "options_language": "언어",
  "options_theme": "테마",
  "options_toast": "토스트 알림",
  "options_junk_filter": "잡담 필터",
  "settings_language_auto": "자동 감지",
  "settings_theme_light": "라이트",
  "settings_theme_dark": "다크",
  "settings_theme_system": "시스템",
  "pro_upgrade": "Pro로 업그레이드",
  "pro_upgrade_hint": "Pro로 업그레이드하면 무제한으로 사용할 수 있어요",
  "...": "..."
}
```

```json
// src/i18n/en.json (예시)
{
  "popup_title": "Nugget",
  "popup_search_placeholder": "Search...",
  "toast_saved": "Saved by Nugget",
  "...": "..."
}
```

> Frontend가 ko.json과 en.json의 전체 키를 정의한다. 모든 사용자 표시 문자열에 대한 키를 포함해야 한다 (AC-V11-10).

### 15.3 src/utils/i18n.js 시그니처 사양

```js
/**
 * 현재 언어 설정을 resolve하여 실제 언어 코드 반환
 * 'auto'이면 navigator.language 기반으로 판별
 * @param {string} langSetting - 'ko' | 'en' | 'auto'
 * @returns {string} 'ko' | 'en'
 */
function resolveLanguage(langSetting) {}

/**
 * 번역 사전을 로드 (chrome.runtime.getURL로 JSON fetch)
 * 이미 로드된 언어면 캐시 반환
 * @param {string} lang - 'ko' | 'en'
 * @returns {Promise<Object>} 번역 키-값 객체
 */
async function loadTranslations(lang) {}

/**
 * 번역 키에 해당하는 텍스트 반환
 * 키가 없으면 폴백 언어(ko)에서 찾고, 그래도 없으면 키 자체를 반환
 * @param {string} key - 번역 키 (예: 'popup_title')
 * @param {Object} [params] - 치환 파라미터 (예: { count: 5 } → "{count}개" 에서 치환)
 * @returns {string} 번역된 문자열
 */
function t(key, params) {}

/**
 * 현재 로드된 언어 코드 반환
 * @returns {string} 'ko' | 'en'
 */
function getCurrentLang() {}

/**
 * i18n 초기화: 설정에서 언어 로드 → 번역 사전 로드
 * HTML에서 data-i18n 속성을 가진 요소의 textContent를 번역으로 교체
 * @returns {Promise<void>}
 */
async function initI18n() {}

/**
 * DOM의 data-i18n 속성을 기반으로 텍스트 업데이트
 * 언어 변경 시 호출하여 페이지 전체를 갱신
 * @param {Element} [root=document] - 탐색 루트 요소
 */
function applyI18nToDOM(root) {}
```

**사용 패턴 (HTML):**
```html
<span data-i18n="popup_title">Nugget</span>
<input data-i18n-placeholder="popup_search_placeholder" placeholder="검색어를 입력하세요">
```

**사용 패턴 (JS):**
```js
// 페이지 초기화 시
await initI18n();

// 동적으로 생성한 요소
toast.textContent = t('toast_saved');
```

### 15.4 언어 변경 반영 범위 (AC-V11-12, 비판자 CRITICAL-3 해결)

| 페이지 | 반영 시점 | 메커니즘 |
|--------|-----------|----------|
| Options | 즉시 | `applyI18nToDOM()` 직접 호출 (DOM 갱신) |
| Popup | 다음 열 때 | `initI18n()` 호출 시점에 최신 설정 적용 |
| Onboarding | 이미 닫혔을 가능성 높음 | 재방문 시 `initI18n()`으로 적용 |
| Content Script 토스트 | 다음 토스트 표시 시 | `chrome.storage.onChanged` 리스너로 언어 설정 감지 → `t()` 호출 시 최신 언어 사용 |

---

## 16. [v1.1] 테마 관리 아키텍처 (AC-V11-15 ~ AC-V11-20)

### 16.1 개요

CSS 커스텀 속성(변수)으로 라이트/다크/시스템 3가지 테마를 관리한다.

### 16.2 src/utils/theme.js 시그니처 사양

```js
/**
 * 테마 설정을 resolve하여 실제 테마 반환
 * 'system'이면 OS 다크모드 여부로 판별
 * @param {string} themeSetting - 'light' | 'dark' | 'system'
 * @returns {string} 'light' | 'dark'
 */
function resolveTheme(themeSetting) {}

/**
 * 테마 초기화: 설정 로드 → <html>에 data-theme 속성 설정
 * system 모드일 때 prefers-color-scheme 미디어쿼리 리스너 등록
 * @returns {Promise<void>}
 */
async function initTheme() {}

/**
 * 테마 변경 적용: <html>의 data-theme 속성 변경
 * @param {string} theme - 'light' | 'dark'
 */
function applyTheme(theme) {}

/**
 * 시스템 테마 변경 감지 리스너 등록
 * 'system' 설정일 때만 활성화
 * prefers-color-scheme 변경 시 applyTheme() 자동 호출
 * @param {string} themeSetting - 현재 테마 설정 ('light'|'dark'|'system')
 */
function watchSystemTheme(themeSetting) {}
```

### 16.3 CSS 커스텀 속성 구조 (AC-V11-15)

Frontend가 각 CSS 파일(popup.css, options.css, onboarding.css)에 정의:

```css
/* 라이트 테마 (기본) */
:root, [data-theme="light"] {
  --bg-primary: #FFFFFF;
  --bg-secondary: #F5F5F5;
  --bg-card: #FFFFFF;
  --text-primary: #1A1A1A;
  --text-secondary: #666666;
  --border-color: #E0E0E0;
  --nugget-gold: #E5A00D;          /* 브랜드 컬러 유지 (AC-V11-19) */
  --shadow: 0 2px 8px rgba(0,0,0,0.1);
  /* ... 기타 필요한 변수 ... */
}

/* 다크 테마 */
[data-theme="dark"] {
  --bg-primary: #1A1A1A;
  --bg-secondary: #2D2D2D;
  --bg-card: #2D2D2D;
  --text-primary: #E0E0E0;
  --text-secondary: #999999;
  --border-color: #404040;
  --nugget-gold: #F0B429;          /* 다크 배경에서 가독성 향상 변형 (AC-V11-19) */
  --shadow: 0 2px 8px rgba(0,0,0,0.4);
  /* ... 기타 필요한 변수 ... */
}
```

> UI디자이너가 정확한 색상 값을 결정한다. 위는 설계 가이드라인.

### 16.4 테마 적용 방식

```
1. 페이지 로드 시 theme.js의 initTheme() 호출
2. initTheme()가 nugget_settings.theme 값을 읽음
3. resolveTheme()로 실제 테마 결정 ('light' | 'dark')
4. <html data-theme="dark"> 또는 <html data-theme="light"> 설정
5. CSS가 [data-theme] 속성 셀렉터로 변수 값을 자동 전환
6. 'system' 모드: prefers-color-scheme 미디어쿼리 리스너 등록 → OS 변경 시 실시간 반영 (AC-V11-20)
```

---

## 17. [v1.1] 시그니처 사양 — 새 모듈

### 17.1 src/content/interceptor.js

```js
/**
 * MAIN world에서 실행. window.fetch를 오버라이드하여 AI 사이트의 SSE 응답을 캡처.
 * 캡처된 데이터는 CustomEvent('__nugget_api_capture__')로 bridge.js에 전달.
 */

/**
 * fetch 오버라이드 설치
 * document_start에서 자동 실행됨 (IIFE)
 */
(function installFetchInterceptor() {})();

/**
 * URL이 API 엔드포인트 패턴과 매칭되는지 확인
 * @param {string} url - fetch URL
 * @param {string} platform - 'claude' | 'chatgpt' | 'gemini'
 * @returns {boolean}
 */
function isApiEndpoint(url, platform) {}

/**
 * 복제된 ReadableStream에서 Claude SSE 데이터 파싱
 * @param {ReadableStream} stream - tee()로 복제된 스트림
 * @param {string} requestBody - 요청 body (질문 추출용)
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseClaudeSSE(stream, requestBody) {}

/**
 * 복제된 ReadableStream에서 ChatGPT SSE 데이터 파싱
 * @param {ReadableStream} stream
 * @param {string} requestBody
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseChatGPTSSE(stream, requestBody) {}

/**
 * 복제된 ReadableStream에서 Gemini 응답 데이터 파싱
 * @param {ReadableStream} stream
 * @param {string} requestBody
 * @returns {Promise<{ question: string, answer: string } | null>}
 */
async function parseGeminiResponse(stream, requestBody) {}

/**
 * 파싱된 대화 데이터를 CustomEvent로 bridge.js에 전달
 * @param {string} platform
 * @param {string} question
 * @param {string} answer
 */
function dispatchCapture(platform, question, answer) {}
```

### 17.2 src/content/bridge.js

```js
/**
 * ISOLATED world에서 실행. interceptor.js의 CustomEvent를 수신하여
 * chrome.runtime.sendMessage로 Background에 전달.
 * 이 파일은 이 한 가지 역할만 수행.
 */

/**
 * CustomEvent 리스너 등록 및 API_CAPTURE 메시지 전달
 * document_start에서 자동 실행됨 (IIFE)
 */
(function initBridge() {})();
```

### 17.3 src/utils/i18n.js

> 섹션 15.3에서 상세 정의됨. 여기서는 요약.

```js
function resolveLanguage(langSetting) {}
async function loadTranslations(lang) {}
function t(key, params) {}
function getCurrentLang() {}
async function initI18n() {}
function applyI18nToDOM(root) {}
```

### 17.4 src/utils/theme.js

> 섹션 16.2에서 상세 정의됨. 여기서는 요약.

```js
function resolveTheme(themeSetting) {}
async function initTheme() {}
function applyTheme(theme) {}
function watchSystemTheme(themeSetting) {}
```

### 17.5 background.js 새 함수 (v1.1 추가)

```js
/**
 * API_CAPTURE 메시지 처리: saveEntry() 파이프라인 실행 + 해시 기록
 * @param {{ platform: string, question: string, answer: string, sourceUrl: string }} data
 * @returns {Promise<{ success: boolean, entry?: NuggetEntry, error?: string }>}
 */
async function handleApiCapture(data) {}

/**
 * API 캡처 해시 목록 로드
 * @returns {Promise<string[]>}
 */
async function loadApiCaptureHashes() {}

/**
 * API 캡처 해시 기록 (최근 100개까지 유지)
 * @param {string} hash
 * @returns {Promise<void>}
 */
async function recordApiCaptureHash(hash) {}

/**
 * SAVE_ENTRY 수신 시 API 캡처 해시와 비교하여 중복 여부 확인
 * @param {string} hash - 생성된 해시
 * @returns {Promise<boolean>} true이면 중복 (무시해야 함)
 */
async function isDuplicateOfApiCapture(hash) {}

/**
 * 원격 셀렉터 fetch 및 캐시 (AC-V11-6)
 * @returns {Promise<void>}
 */
async function fetchRemoteSelectors() {}

/**
 * 원격 셀렉터 JSON 스키마 검증 (AC-V11-9)
 * @param {Object} data - fetch된 JSON
 * @returns {boolean}
 */
function validateRemoteSelectors(data) {}
```

---

## 18. [v1.1] 데이터 흐름 요약

### 18.1 API 가로채기 저장 흐름 (v1.1 메인 경로)

```
사용자가 AI에게 질문
  → AI가 답변 스트리밍 (fetch 기반 SSE)
  → interceptor.js (MAIN world): window.fetch 오버라이드가 응답 가로챔
  → interceptor.js: ReadableStream.tee()로 스트림 복제
  → interceptor.js: 원본 스트림으로 Response를 만들어 페이지에 반환 (기능 영향 없음)
  → interceptor.js: 복제 스트림을 플랫폼별 SSE 파서로 파싱
  → interceptor.js: question + answer 추출 성공
  → interceptor.js: CustomEvent('__nugget_api_capture__')로 bridge.js에 전달
  → bridge.js (ISOLATED world): API_CAPTURE 메시지를 Background에 전송
  → Background: handleApiCapture() 실행
    → 해시 생성 → 중복 체크 (기존 entries)
    → 잡담 필터 적용
    → 자동 태깅
    → NuggetEntry 생성 → 저장
    → 해시를 nugget_api_capture_hashes에 기록
    → 무료 한도 체크 → 필요 시 아카이브
  → Background: 응답 { success: true }
```

### 18.2 DOM 셀렉터 폴백 흐름 (v1.1, API 캡처 실패 시)

```
API 캡처 실패 (파서 null 반환 / interceptor 미실행)
  → 기존 Content Script (claude.js 등): MutationObserver가 DOM 변화 감지 (기존 로직)
  → debounce 1초 후 스트리밍 완료 판단
  → 질문+답변 추출
  → 500ms 추가 지연 (API_CAPTURE 중복 방지 대기)
  → SAVE_ENTRY 메시지 전송
  → Background: 해시 생성 → nugget_api_capture_hashes 확인
    → 해시가 있으면 → 무시 (API_CAPTURE로 이미 저장됨)
    → 해시가 없으면 → 기존 saveEntry() 파이프라인 실행
  → Content Script: 성공 시 토스트 표시
```

### 18.3 원격 셀렉터 갱신 흐름

```
Service Worker 시작 또는 알람 트리거 (24시간 주기)
  → Background: fetchRemoteSelectors() 호출
  → GitHub Raw URL에서 JSON fetch
  → 스키마 검증 (validateRemoteSelectors)
    → 실패 시 → 무시 (로컬 셀렉터 유지)
    → 성공 시 → nugget_remote_selectors에 저장
  → 다음 Content Script 실행 시 원격 셀렉터 자동 적용
```

---

## 19. [v1.1] 통합 계약 업데이트

> v1.0 통합 계약(섹션 8)에 추가되는 항목. 기존 항목은 유지.

### 19.1 새 파일 이름과 경로

| 파일 | 경로 | 담당 |
|------|------|------|
| API 가로채기 (MAIN world) | `nugget/src/content/interceptor.js` | Backend |
| API 브릿지 (ISOLATED world) | `nugget/src/content/bridge.js` | Backend |
| i18n 유틸리티 | `nugget/src/utils/i18n.js` | Backend |
| 테마 유틸리티 | `nugget/src/utils/theme.js` | Backend |
| 한국어 번역 | `nugget/src/i18n/ko.json` | Frontend |
| 영어 번역 | `nugget/src/i18n/en.json` | Frontend |

### 19.2 새 Chrome 메시지 타입

```js
// bridge.js → Background (v1.1)
'API_CAPTURE'               // { platform, question, answer, sourceUrl }
```

### 19.3 새 Storage 키 이름

```js
'nugget_remote_selectors'    // RemoteSelectorsCache { version, selectors, fetchedAt }
'nugget_api_capture_hashes'  // string[] — 최근 100개 해시
```

### 19.4 새 상수 (constants.js)

```js
// v1.1 추가 상수
const SUPPORTED_LANGUAGES = ['ko', 'en'];
const DEFAULT_LANGUAGE = 'auto';
const FALLBACK_LANGUAGE = 'ko';
const SUPPORTED_THEMES = ['light', 'dark', 'system'];
const DEFAULT_THEME = 'system';
const REMOTE_SELECTORS_URL = 'https://raw.githubusercontent.com/{owner}/{repo}/main/selectors.json';
const REMOTE_SELECTORS_CACHE_HOURS = 24;
const REMOTE_SELECTORS_ALARM_NAME = 'fetch_remote_selectors';
const API_CAPTURE_HASH_MAX = 100;
const API_CAPTURE_EVENT_NAME = '__nugget_api_capture__';
const SAVE_ENTRY_DEDUP_DELAY_MS = 500;
```

### 19.5 manifest.json 변경 요약

| 변경 | 내용 |
|------|------|
| `version` | `"1.0.0"` → `"1.1.0"` |
| `permissions` | `"alarms"` 추가 |
| `content_scripts` | MAIN world `interceptor.js` 항목 추가 (document_start) |
| `content_scripts` | ISOLATED world `bridge.js` 항목 추가 (document_start) |
| 기존 content_scripts | 그대로 유지 (DOM 셀렉터 폴백) |

### 19.6 UPDATE_SETTINGS 허용 키 추가

background.js의 `ALLOWED_SETTINGS_KEYS` 배열에 `'language'`와 `'theme'`를 추가해야 한다:

```js
const ALLOWED_SETTINGS_KEYS = ['toastEnabled', 'junkFilterEnabled', 'shortcutKey', 'language', 'theme'];
```

---

## 20. [v1.1] critique_v1.1_report.md 반영

| 비판 항목 | 해결 방법 | 설계 섹션 |
|-----------|-----------|-----------|
| CRITICAL-1 (SSE 파서 AC 누락) | 섹션 13.3에서 플랫폼별 파서 시그니처와 파싱 로직을 상세 정의 | 13.3 |
| CRITICAL-2 (API 캡처 실패 정의 모호) | 섹션 13.3 하단에 "파싱 실패의 정의"를 명시 — API 데이터로 Q+A 추출을 완료하지 못한 모든 경우 | 13.3 |
| CRITICAL-5 (중복 저장 방지 메커니즘 누락) | 섹션 13.5에서 해시 기반 차단 + Content Script 500ms 지연 전략 상세 정의 | 13.5 |
| MINOR-1 (bridge.js 역할 분담) | 섹션 13.4에서 bridge.js의 역할을 "API 캡처 → Background 전달만"으로 명확히 한정 | 13.4 |
| MINOR-2 (원격 셀렉터 우선순위) | 섹션 14.5에서 폴백 시에도 원격 우선 적용 명시 | 14.5 |
| MINOR-3 (24시간 주기 기준) | 섹션 14.4에서 chrome.alarms 기반 periodInMinutes: 1440으로 명시 | 14.4 |
| MINOR-4 (원격 JSON 스키마) | 섹션 14.2에서 검증 기준을 상세 명시 (필수 키 존재 확인) | 14.2 |
| MINOR-5 ('auto' 언어 동작) | 섹션 5.3 NuggetSettings 하단에 'auto' 동작 명시 | 5.3 |
| MINOR-7 (document_start 타이밍) | Pre-mortem v1.1 4번으로 추가 (.plan.v1.1.md에 반영됨) | - |
| MINOR-8 (manifest 추가 방식) | 섹션 3에서 별도 항목으로 추가 명시 | 3 |
| MINOR-9 (src/shared 소유권 충돌) | `src/utils/`에 배치하여 Backend 소유권으로 해결 | 2 |
| MINOR-10 (v1.0→v1.1 마이그레이션) | 섹션 5.3에 마이그레이션 설명 추가 | 5.3 |


---

# PART 4: UI 디자인 가이드 (ui_design.md)

# Nugget UI Design Guide

> AI 대화 자동 저장 크롬 확장 프로그램 — 프론트엔드 구현 가이드

---

## 1. 색상 팔레트

### 1.1 브랜드 색상

| 용도 | 색상명 | HEX | 사용처 |
|------|--------|-----|--------|
| Primary | Nugget Gold | `#F5A623` | CTA 버튼, 로고 악센트, 별표 아이콘 |
| Primary Dark | Deep Gold | `#D4891A` | Primary hover/active 상태 |
| Primary Light | Soft Gold | `#FFF3DC` | 선택된 항목 배경, 하이라이트 영역 |

### 1.2 플랫폼 식별 색상

| 플랫폼 | HEX | RGB | 용도 |
|--------|-----|-----|------|
| Claude | `#7C3AED` | 124, 58, 237 | 카드 좌측 스트라이프, 필터 칩, 아이콘 |
| ChatGPT | `#10A37F` | 16, 163, 127 | 카드 좌측 스트라이프, 필터 칩, 아이콘 |
| Gemini | `#4285F4` | 66, 133, 244 | 카드 좌측 스트라이프, 필터 칩, 아이콘 |

### 1.3 시스템 색상

| 용도 | HEX | 사용처 |
|------|-----|--------|
| Background | `#FFFFFF` | 전체 배경 |
| Surface | `#F8F9FA` | 카드 배경, 입력 필드 배경 |
| Surface Hover | `#F1F3F5` | 카드 hover 상태 |
| Border | `#E1E4E8` | 카드 테두리, 구분선 |
| Text Primary | `#1A1A2E` | 제목, 본문 텍스트 |
| Text Secondary | `#6B7280` | 부제목, 메타 정보, placeholder |
| Text Tertiary | `#9CA3AF` | 비활성 텍스트, 힌트 |

### 1.4 상태 색상

| 상태 | HEX | 사용처 |
|------|-----|--------|
| Success | `#22C55E` | 저장 완료, 복사 완료 토스트 |
| Warning | `#F59E0B` | 용량 경고, 주의 뱃지 |
| Error | `#EF4444` | 셀렉터 실패, 에러 메시지 |
| Info | `#3B82F6` | 안내 메시지, 링크 |
| Pro Badge | `#8B5CF6` | Pro 라벨, 업그레이드 CTA 배경 |

### 1.5 CSS 변수 정의

```css
:root {
  /* Brand */
  --nugget-primary: #F5A623;
  --nugget-primary-dark: #D4891A;
  --nugget-primary-light: #FFF3DC;

  /* Platform */
  --color-claude: #7C3AED;
  --color-chatgpt: #10A37F;
  --color-gemini: #4285F4;

  /* System */
  --bg-primary: #FFFFFF;
  --bg-surface: #F8F9FA;
  --bg-surface-hover: #F1F3F5;
  --border-default: #E1E4E8;
  --text-primary: #1A1A2E;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;

  /* State */
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;
  --color-pro: #8B5CF6;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;

  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Typography */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-xs: 11px;
  --font-size-sm: 12px;
  --font-size-md: 13px;
  --font-size-lg: 15px;
  --font-size-xl: 17px;

  /* Shadow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.1);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.12);

  /* Transition */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}
```

---

## 2. 타이포그래피

| 요소 | 크기 | 굵기 | 색상 | 행간 |
|------|------|------|------|------|
| 페이지 제목 | 17px | 700 (Bold) | Text Primary | 1.3 |
| 섹션 제목 | 15px | 600 (SemiBold) | Text Primary | 1.3 |
| 카드 질문 텍스트 | 13px | 600 (SemiBold) | Text Primary | 1.4 |
| 카드 답변 텍스트 | 12px | 400 (Regular) | Text Secondary | 1.5 |
| 메타 정보 (날짜, 태그) | 11px | 400 (Regular) | Text Tertiary | 1.3 |
| 버튼 텍스트 | 13px | 600 (SemiBold) | 상황별 | 1.0 |
| 입력 필드 텍스트 | 13px | 400 (Regular) | Text Primary | 1.4 |
| placeholder | 13px | 400 (Regular) | Text Tertiary | 1.4 |
| 뱃지/칩 텍스트 | 11px | 500 (Medium) | 상황별 | 1.0 |

---

## 3. 페이지별 레이아웃

### 3.1 Popup (메인 UI)

**크기:** 400px (너비) x 580px (높이)
**전체 구조:** 수직 스크롤, 상단 고정 영역 + 스크롤 가능 카드 리스트 + 하단 고정 영역

```
+------------------------------------------+  ← 400px
|  [Today's Nugget]                    [X]  |  ← 닫기 가능 배너 (60px)
|  "3개월 전, React 상태관리를 물어봤..."    |
+------------------------------------------+
|  [🔍 대화 검색...]              [필터 ▼]  |  ← 검색바 (40px)
+------------------------------------------+
|  [Claude][ChatGPT][Gemini] [기간▼][태그▼] |  ← 필터 행 (36px, 수평 스크롤)
|  [★ 별표만] [잡담 포함]                    |
+------------------------------------------+
|                                           |
|  ┌─ 카드 1 ─────────────────────────┐     |
|  │▌ Q: React에서 상태관리 어떻게...  │     |  ← 스크롤 영역
|  │  A: React에서는 useState...       │     |     (카드 리스트)
|  │  📅 2월 18일 · #코딩 · ★ · 📝 [MD]│     |
|  └──────────────────────────────────┘     |
|                                           |
|  ┌─ 카드 2 ─────────────────────────┐     |
|  │▌ Q: 마케팅 전략 추천해줘         │     |
|  │  📅 2월 17일 · #업무             │     |
|  └──────────────────────────────────┘     |
|                                           |
|  ... (스크롤)                              |
|                                           |
+------------------------------------------+
|  📊 이번 달: 47개 | 최다: Claude | #코딩 |  ← 미니 통계 (32px)
+------------------------------------------+
|  [백업] [복원] [⚙ 설정] [✨ Pro 업그레이드]|  ← 하단 버튼 (44px)
+------------------------------------------+
```

#### 3.1.1 Today's Nugget 영역

- **위치:** 팝업 최상단
- **높이:** 60px (내용에 따라 최대 72px까지 가변)
- **배경:** `var(--nugget-primary-light)` (#FFF3DC)
- **좌측:** Nugget 아이콘 (16x16) + "Today's Nugget" 라벨 (11px, SemiBold, Gold)
- **우측:** X 닫기 버튼 (20x20, 터치 영역 32x32)
- **내용:** 과거 대화 요약 1줄 (13px, Text Primary, 말줄임)
- **하단 구분:** 1px solid `var(--border-default)`
- **클릭 동작:** 해당 대화 카드로 스크롤 이동 + 하이라이트 효과 (0.5초 골드 glow)
- **닫은 경우:** 세션 동안 숨김. 다음에 팝업 열면 다시 노출
- **비어있을 때:** 저장된 대화가 없으면 이 영역 자체를 숨김

#### 3.1.2 검색바

- **높이:** 40px
- **배경:** `var(--bg-surface)`
- **테두리:** 1px solid `var(--border-default)`, focus 시 `var(--nugget-primary)`
- **좌측 아이콘:** 돋보기 (16px, Text Tertiary)
- **Placeholder:** "대화 검색..." (Text Tertiary)
- **우측:** 필터 토글 버튼 (아이콘 + "필터" 라벨)
  - 필터가 활성화되어 있으면 버튼에 Primary 색상 도트 표시
- **여백:** 좌우 `var(--space-lg)`, 상하 `var(--space-sm)`
- **모서리:** `var(--radius-md)` (8px)

#### 3.1.3 필터 행

- **높이:** 자동 (컨텐츠에 따라, 기본 숨김 상태)
- **표시 조건:** 검색바의 필터 버튼 클릭 시 슬라이드 다운 (250ms ease)
- **레이아웃:** Flex wrap, gap 6px
- **필터 칩 스타일:**
  - 기본: `var(--bg-surface)` 배경, `var(--border-default)` 테두리, 11px 텍스트
  - 선택됨: 해당 플랫폼 색상 배경 (10% 투명도) + 색상 테두리 + 색상 텍스트
  - 크기: padding 4px 10px, `var(--radius-full)` (pill 모양)
- **플랫폼 필터:** 각 플랫폼 색상 아이콘 + 이름. 복수 선택 가능
- **기간 필터:** 드롭다운 — 전체 / 오늘 / 이번 주 / 이번 달 / 직접 설정
  - "직접 설정" 선택 시 날짜 범위 선택기(date input 2개) 인라인 노출
- **태그 필터:** 드롭다운 — 전체 / 코딩 / 글쓰기 / 업무 / 학습 / 크리에이티브 / 기타. 복수 선택 가능
- **별표만:** 토글 칩 (★ 아이콘)
- **잡담 포함:** 토글 칩 (기본 OFF)
- **하단 여백:** `var(--space-sm)`

#### 3.1.4 카드 리스트 (스크롤 영역)

- **영역 높이:** 나머지 가용 공간 전부 (flex: 1, overflow-y: auto)
- **스크롤바:** 얇은 커스텀 스크롤바 (4px, 라운드, 회색)
- **카드 간격:** `var(--space-sm)` (8px)
- **좌우 패딩:** `var(--space-md)` (12px)

**개별 카드 구조:**

```
┌─────────────────────────────────────────┐
│▌  Q: React에서 상태관리 어떻게 하나요?   │  ← 좌측 4px 플랫폼 색상 스트라이프
│   A: React에서 상태를 관리하는 방법은     │
│   여러 가지가 있습니다. useState는...     │
│   ─────────────────────────────────────  │  ← 구분선 (접힌 상태에선 없음)
│   📅 2월 18일 14:30  ·  #코딩  ·  #학습  │  ← 메타 행
│   [★] [📝] [MD]                          │  ← 액션 행
└─────────────────────────────────────────┘
```

- **카드 배경:** `var(--bg-primary)` (흰색)
- **테두리:** 1px solid `var(--border-default)`
- **모서리:** `var(--radius-md)` (8px)
- **그림자:** `var(--shadow-sm)`, hover 시 `var(--shadow-md)`
- **좌측 스트라이프:** 4px 너비, 플랫폼 색상, border-radius 좌측만 적용
- **패딩:** 12px (좌측은 스트라이프 포함 16px)

**카드 내부 요소:**

| 요소 | 스타일 | 비고 |
|------|--------|------|
| 질문 (Q) | 13px SemiBold, Text Primary | 접힌 상태: 1줄 말줄임 (ellipsis) |
| 답변 (A) | 12px Regular, Text Secondary | 접힌 상태: 2줄 말줄임. 펼친 상태: 전체 표시 (max-height: 300px, 내부 스크롤) |
| 날짜 | 11px Regular, Text Tertiary | "2월 18일 14:30" 형식 |
| 태그 | 11px Medium, 플랫폼별 or 카테고리별 색상 | pill 칩, padding 2px 8px |
| 별표 (★) | 20px, 비활성: Text Tertiary, 활성: `var(--nugget-primary)` | 클릭으로 토글 |
| 메모 (📝) | 20px, 메모 있으면 Primary, 없으면 Tertiary | 클릭 시 텍스트 입력 영역 토글 |
| MD 복사 | 20px, Text Secondary | 클릭 시 "복사됨" 피드백 |

**카드 접기/펼치기:**
- 기본 상태: 접힘 (질문 1줄 + 답변 2줄 미리보기)
- 카드 클릭: 펼침 (답변 전체 + 메타 행 + 액션 행)
- 접힌 상태 높이: 약 72px
- 펼친 상태 높이: 내용에 따라 가변 (max 400px)
- 애니메이션: max-height transition 250ms ease

**검색 하이라이팅:**
- 매칭 키워드: `background: #FEF08A` (노란색 형광펜), `border-radius: 2px`
- AC-11 준수

**메모 입력 영역 (펼침 시):**
- 카드 내부 하단에 인라인 표시
- `textarea`: 높이 60px, 배경 `var(--bg-surface)`, 테두리 `var(--border-default)`
- Placeholder: "메모를 남겨보세요..."
- 무료 사용자: 우측 하단에 "0/200" 글자 수 카운터
- blur 시 자동 저장 (AC-14)

#### 3.1.5 미니 통계

- **위치:** 카드 리스트 아래, 하단 버튼 위
- **높이:** 32px
- **배경:** `var(--bg-surface)`
- **레이아웃:** 가로 3분할, 중앙 정렬
- **내용:** "이번 달: 47개" | "최다: Claude" | "최다: #코딩"
- **텍스트:** 11px Regular, Text Secondary
- **구분:** 세로선 1px `var(--border-default)`

#### 3.1.6 하단 버튼 영역

- **위치:** 팝업 최하단 고정
- **높이:** 44px
- **배경:** `var(--bg-primary)` + 상단 1px 구분선
- **레이아웃:** Flex, space-between
- **좌측 그룹:** [백업] [복원] [설정] — 아이콘+텍스트, Text Secondary, hover 시 Text Primary
- **우측:** [Pro 업그레이드] — Primary 배경, 흰색 텍스트, `var(--radius-md)`, padding 6px 12px
  - Pro 사용자에게는 이 버튼 대신 "Pro" 뱃지 (작은 pill, `var(--color-pro)` 배경)
- **버튼 크기:** 최소 터치 영역 32x32px

#### 3.1.7 용량 경고 배너 (조건부)

- **표시 조건:** 무료 사용자 + 저장 400개 이상 (AC-18)
- **위치:** 검색바와 필터 행 사이
- **높이:** 36px
- **배경:** Warning 10% 투명도 (`rgba(245, 158, 11, 0.1)`)
- **테두리:** 1px solid `var(--color-warning)`
- **모서리:** `var(--radius-sm)`
- **내용:** "저장 공간이 80%가 됐어요. 백업을 추천해요!" (12px, Warning 색상)
- **500개 도달 시:** "한도에 도달했어요. 새 대화는 오래된 것을 숨겨요." + [Pro 업그레이드] 링크
- **닫기(X) 버튼:** 우측 (세션 동안 숨김)

---

### 3.2 Options (설정 페이지)

**크기:** 새 탭에서 열림, 최대 너비 640px, 중앙 정렬
**레이아웃:** 단일 컬럼, 섹션별 카드 그룹

```
+--------------------------------------------------+
|  ⚙ Nugget 설정                                   |
+--------------------------------------------------+
|                                                    |
|  ┌─ 일반 설정 ──────────────────────────────┐     |
|  │  토스트 알림           [ON ■□ OFF]        │     |
|  │  잡담 필터             [ON ■□ OFF]        │     |
|  │  단축키                [Ctrl+Shift+S] [변경]│    |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ 잡담 키워드 관리 ───────────────────────┐     |
|  │  [안녕] [고마워] [ㅋㅋ] [ㅎㅎ] [+추가]    │     |
|  │  ⓘ 여기 있는 단어로 시작하는 질문은       │     |
|  │    잡담으로 분류돼요                       │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ 데이터 관리 ────────────────────────────┐     |
|  │  저장된 대화: 247개 / 500개               │     |
|  │  [■■■■■□□□□□] 49%                        │     |
|  │  [백업 (JSON)] [복원]                      │     |
|  │  Pro: [PDF 내보내기] [Markdown 내보내기]    │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ Pro 구독 ───────────────────────────────┐     |
|  │  현재: 무료 플랜                          │     |
|  │  [✨ Pro로 업그레이드] — 월 $X.XX          │     |
|  │  · 무제한 저장  · 커스텀 태그              │     |
|  │  · 무제한 MD 복사  · PDF/MD 내보내기       │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  Nugget v1.0.0                                    |
+--------------------------------------------------+
```

#### 3.2.1 일반 설정 섹션

- **토스트 알림 토글:** 슬라이더 스위치 (36x20), ON=Primary, OFF=Border색
- **잡담 필터 토글:** 동일 스위치
- **단축키 표시:** 현재 단축키를 `<kbd>` 스타일 칩으로 표시
  - [변경] 클릭 시 chrome://extensions/shortcuts로 이동 안내

#### 3.2.2 잡담 키워드 관리

- **키워드 칩:** pill 모양, `var(--bg-surface)` 배경, 클릭 시 X표시 나타남 (삭제 가능)
- **[+추가] 버튼:** 클릭 시 인라인 input 나타남, Enter로 추가
- **안내 텍스트:** ⓘ 아이콘 + 11px Text Tertiary

#### 3.2.3 데이터 관리

- **프로그레스 바:** 높이 8px, 라운드, 배경 `var(--bg-surface)`, 채움색:
  - 0~79%: `var(--color-info)`
  - 80~99%: `var(--color-warning)`
  - 100%: `var(--color-error)`
- **버튼:** 보조 스타일 (테두리 버튼)

#### 3.2.4 Pro 구독

- **현재 플랜 표시:** 무료 → "무료 플랜", Pro → "Pro 플랜 (활성)"
- **업그레이드 CTA:** `var(--color-pro)` 배경, 흰색 텍스트, 약간의 그림자
- **혜택 목록:** 체크마크 아이콘 + 텍스트, 13px
- **Pro 상태 확인 배너 (AC-24a):** 캐시 만료 + 오프라인 시 상단에 노란 배너 "구독 확인이 필요해요. 인터넷 연결 시 자동으로 확인됩니다."

---

### 3.3 Onboarding (설치 후 안내)

**크기:** 새 탭에서 열림, 최대 너비 560px, 중앙 정렬
**레이아웃:** 단일 페이지 세로 스크롤 (스텝 표시 아님)

```
+--------------------------------------------------+
|                                                    |
|            🥜 Nugget에 오신 것을 환영해요!          |
|        AI 대화를 자동으로 저장하고 찾아보세요        |
|                                                    |
+--------------------------------------------------+
|                                                    |
|  ① 자동 저장                                      |
|  ┌──────────────────────────────────────┐         |
|  │  [샘플 카드 - Claude 대화 예시]       │         |
|  │  ▌Q: React 상태관리 방법 알려줘       │         |
|  │   A: React에서는 useState, useReducer │         |
|  └──────────────────────────────────────┘         |
|  Claude, ChatGPT, Gemini에서의 대화가              |
|  자동으로 저장돼요.                                |
|                                                    |
|  ② 똑똑한 정리                                    |
|  자동 태그 + 잡담 필터로 중요한 대화만 모아요.      |
|                                                    |
|  ③ 빠른 검색                                      |
|  키워드, 플랫폼, 태그로 원하는 대화를 바로 찾아요.  |
|                                                    |
|  ④ 단축키                                         |
|  Ctrl+Shift+S로 별표를 바로 달 수 있어요.           |
|                                                    |
|  ┌─ Pro 미리보기 (가벼운 소개) ────────┐           |
|  │  무제한 저장, 커스텀 태그, PDF 내보내기  │        |
|  │  [나중에 알아보기]                     │         |
|  └────────────────────────────────────┘           |
|                                                    |
|       [Nugget 시작하기 →]                          |
|                                                    |
+--------------------------------------------------+
```

#### 3.3.1 디자인 원칙

- **톤:** 친근하고 가벼움. "~해요" 체
- **삽화:** 각 단계에 간단한 아이콘 또는 CSS 일러스트 (외부 이미지 의존 없음)
- **샘플 카드:** 실제 카드 UI와 동일한 스타일로 렌더링 (사용자에게 결과물 미리 보여주기)
- **Pro 소개:** 눈에 띄지만 강요하지 않는 톤. "나중에 알아보기" 링크만 제공
- **CTA 버튼:** "Nugget 시작하기" — Primary 배경, 큰 사이즈 (44px 높이, 전체 너비의 60%)

---

### 3.4 토스트 알림 (Content Script)

**위치:** AI 사이트 화면 우측 하단
**크기:** 280px x 48px

```
┌──────────────────────────────────┐
│  🥜  Nugget이 저장했어요         │  ← 페이드인 → 1.5초 유지 → 페이드아웃
└──────────────────────────────────┘
```

- **배경:** `rgba(26, 26, 46, 0.9)` (Text Primary 90% 불투명)
- **텍스트:** 13px, 흰색
- **모서리:** `var(--radius-md)` (8px)
- **그림자:** `var(--shadow-lg)`
- **위치:** fixed, bottom: 24px, right: 24px
- **z-index:** 2147483647 (최대값, 사이트 UI 위에 표시)
- **애니메이션:**
  - 진입: translateY(16px) + opacity(0) → translateY(0) + opacity(1), 300ms ease-out
  - 퇴장: opacity(1) → opacity(0), 300ms ease-in (1.5초 후)
- **AI 사이트별 호환:** Shadow DOM 안에서 렌더링하여 사이트 CSS와 충돌 방지

---

## 4. 사용자 동선 (User Flow)

### 4.1 최초 설치 동선

```
Chrome 웹 스토어에서 설치
    ↓
새 탭에서 Onboarding 페이지 자동 열림 (AC-21)
    ↓
사용자가 안내 읽기
    ↓
"Nugget 시작하기" 클릭
    ↓
Onboarding 탭 닫힘 → 사용자는 평소처럼 AI 사이트 이용 시작
```

### 4.2 일상 사용 동선

```
사용자가 Claude/ChatGPT/Gemini에서 대화
    ↓
대화 완료 감지 (Content Script)
    ↓
토스트: "Nugget이 저장했어요" (우측 하단, 1.5초)
    ↓
(나중에) 확장 아이콘 클릭 → Popup 열림
    ↓
Today's Nugget 확인 or 닫기
    ↓
검색/필터로 원하는 대화 찾기
    ↓
카드 클릭 → 펼쳐서 상세 확인
    ↓
[★ 별표] / [📝 메모 추가] / [MD 복사]
```

### 4.3 검색 동선

```
Popup 열림
    ↓
검색바에 키워드 입력
    ↓
실시간 필터링 (타이핑 중 300ms debounce)
    ↓
결과 카드에 키워드 노란색 하이라이트 (AC-11)
    ↓
필터 버튼으로 추가 필터 (플랫폼, 기간, 태그, 별표, 잡담)
    ↓
원하는 카드 클릭 → 상세 보기
```

### 4.4 백업/복원 동선

```
[백업] Popup 하단 "백업" 클릭
    ↓
JSON 파일 다운로드 (nugget-backup-2026-02-18.json)
    ↓
완료 토스트: "백업 완료!"

[복원] Popup 하단 "복원" 클릭
    ↓
파일 선택 대화상자
    ↓
JSON 파일 선택
    ↓
병합 처리 (중복 ID 제거)
    ↓
무료 사용자: 500개 초과분 자동 archived (AC-23a)
    ↓
완료 토스트: "복원 완료! N개 대화가 추가됐어요"
```

### 4.5 Pro 업그레이드 동선

```
"Pro로 업그레이드" 버튼 클릭 (Popup 또는 Options)
    ↓
ExtensionPay 결제 페이지 (외부 탭)
    ↓
결제 완료 → isPro = true
    ↓
Popup/Options UI 업데이트:
  - "Pro" 뱃지 표시
  - 한도 제거
  - Pro 전용 기능 잠금 해제
```

### 4.6 셀렉터 실패 동선 (에러 상황)

```
AI 사이트 DOM 구조 변경 → 셀렉터 실패
    ↓
확장 아이콘에 "!" 뱃지 (Warning 색상) (AC-3)
    ↓
사용자가 Popup 열기
    ↓
상단에 에러 배너: "대화 저장이 일시 중단됐어요. 업데이트를 확인해 주세요."
    ↓
배너 내 [업데이트 확인] 버튼 → Chrome 웹 스토어 링크
```

---

## 5. 상태별 UI

### 5.1 로딩 상태

| 위치 | 표현 | 상세 |
|------|------|------|
| Popup 카드 리스트 | 스켈레톤 카드 3개 | 회색 펄스 애니메이션 (카드 모양), 0.8초 주기 |
| 검색 결과 로딩 | 스켈레톤 카드 2개 | 기존 카드 fade-out → 스켈레톤 → 결과 fade-in |
| Options 페이지 | 각 섹션 스켈레톤 | 회색 블록 펄스 |
| 백업/복원 진행 중 | 버튼 내 스피너 | 버튼 비활성화 + 16px 원형 스피너 |

**스켈레톤 스타일:**
```css
.skeleton {
  background: linear-gradient(90deg, #F1F3F5 25%, #E1E4E8 50%, #F1F3F5 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### 5.2 빈 상태 (Empty State)

| 상황 | 표현 |
|------|------|
| 첫 설치 후 대화 없음 | 중앙 정렬: 아이콘 (48px, Tertiary) + "아직 저장된 대화가 없어요" + "AI 사이트에서 대화를 시작해 보세요" (Text Tertiary, 13px) |
| 검색 결과 없음 | 중앙 정렬: 돋보기 아이콘 (48px) + "검색 결과가 없어요" + "다른 키워드로 찾아보세요" |
| 필터 결과 없음 | 중앙 정렬: 필터 아이콘 + "조건에 맞는 대화가 없어요" + [필터 초기화] 버튼 (텍스트 버튼) |
| 별표만 + 별표 없음 | "아직 별표 친 대화가 없어요" + "★ 아이콘을 눌러 중요한 대화를 표시해 보세요" |

**빈 상태 공통 스타일:**
- 영역: 카드 리스트 전체
- 정렬: 가로세로 중앙
- 아이콘: 48px, `var(--text-tertiary)`
- 제목: 15px SemiBold, Text Primary
- 설명: 13px Regular, Text Tertiary
- 간격: 아이콘 → 제목 12px, 제목 → 설명 4px

### 5.3 에러 상태

| 상황 | 표현 |
|------|------|
| 셀렉터 실패 (AC-3) | Popup 상단 에러 배너: Error 배경 10% + Error 테두리 + "대화 저장이 일시 중단됐어요" + [업데이트 확인] |
| 백업 파일 형식 오류 | 모달 대화상자: "파일을 읽을 수 없어요" + "Nugget JSON 백업 파일인지 확인해 주세요" + [확인] 버튼 |
| storage 오류 | Popup 상단 배너: "저장 공간에 문제가 생겼어요" + [설정에서 확인] |
| Pro 상태 확인 실패 (오프라인) | Options 상단 노란 배너: "구독 확인이 필요해요. 인터넷 연결 시 자동으로 확인됩니다" |
| ExtensionPay 결제 오류 | 모달: "결제 처리 중 문제가 생겼어요" + "잠시 후 다시 시도해 주세요" + [다시 시도] [닫기] |

**에러 배너 스타일:**
```css
.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  padding: var(--space-sm) var(--space-md);
  margin: var(--space-sm) var(--space-md);
  font-size: var(--font-size-sm);
  color: var(--color-error);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}
```

### 5.4 성공 상태

| 상황 | 표현 |
|------|------|
| 대화 저장 완료 | 토스트 (AI 사이트): "Nugget이 저장했어요" |
| MD 복사 완료 (AC-13) | 카드 내 [MD] 버튼 → 체크 아이콘으로 변경 + "복사됨" 텍스트, 1.5초 후 원래로 |
| 백업 완료 | Popup 내 토스트: "백업 완료!" (Success 색상) |
| 복원 완료 | Popup 내 토스트: "복원 완료! N개 대화가 추가됐어요" |
| 별표 토글 (단축키) (AC-16) | AI 사이트 토스트: "★ 별표 추가" / "별표 해제" |
| 설정 변경 | Options 내: 변경 즉시 저장, 입력 필드 옆 체크 아이콘 0.5초 표시 |

**인앱 토스트 (Popup/Options 내):**
- 위치: 하단 중앙, 카드 리스트 위에 float
- 크기: auto 너비, padding 8px 16px
- 배경: `var(--color-success)` 또는 상황별 색상
- 텍스트: 13px, 흰색
- 모서리: `var(--radius-full)` (pill)
- 애니메이션: 토스트와 동일 (fade in/out)
- 지속 시간: 2초

### 5.5 한도 도달 상태 (무료 사용자)

| 상황 | 표현 |
|------|------|
| MD 복사 한도 (AC-13) | [MD] 버튼 위 말풍선: "이번 달 복사 한도(20회)를 사용했어요" + [Pro 업그레이드] 링크 |
| 저장 80% (AC-18) | 경고 배너 (3.1.7 참조) |
| 저장 100% (AC-18) | 경고 배너 강화 + "한도에 도달했어요" 문구 |
| 커스텀 태그 (AC-9) | 태그 추가 시도 시 말풍선: "커스텀 태그는 Pro 기능이에요" + [업그레이드] |
| 메모 200자 (AC-15) | 메모 입력 시 "200/200" 빨간색 카운터 + 추가 입력 차단 |

**Pro 유도 스타일:**
- 부드럽고 친근한 톤 (AC-24)
- 말풍선 배경: `var(--color-pro)` 10% 투명도
- 텍스트: `var(--color-pro)` 색상
- 절대 기능을 갑자기 차단하지 않음. 안내 먼저.

---

## 6. 반응형 기준

### 6.1 크롬 확장 팝업 특성

크롬 확장 팝업은 일반 웹 페이지와 다른 제약이 있습니다:

| 항목 | 값 | 비고 |
|------|-----|------|
| 최대 너비 | 800px | Chrome 제한 |
| 최대 높이 | 600px | Chrome 제한 |
| 권장 너비 | 400px | 대부분의 확장이 사용하는 표준 |
| 권장 높이 | 580px | 약간의 여백 확보 |
| 최소 너비 | 360px | 작은 화면 대응 |
| 최소 높이 | 500px | 콘텐츠 최소 표시 영역 |

### 6.2 Popup 반응형 전략

Popup은 고정 크기이므로 전통적 반응형(미디어 쿼리)이 아닌 **공간 효율 최적화**에 집중합니다.

| 전략 | 적용 |
|------|------|
| 고정 레이아웃 | 너비 400px, 높이 580px 고정. body에 `width: 400px; height: 580px;` |
| 스크롤 위임 | 카드 리스트만 스크롤. 검색바/하단 버튼은 고정 |
| 텍스트 말줄임 | 긴 텍스트는 ellipsis. 펼치기로 전체 보기 |
| 아이콘 우선 | 작은 버튼은 아이콘만, hover/focus 시 툴팁으로 라벨 |
| 밀도 조절 | 카드 간격 8px, 패딩 12px — 정보 밀도 높게 |

### 6.3 Options / Onboarding 반응형

Options와 Onboarding은 새 탭에서 열리므로 일반 웹 반응형을 적용합니다.

```css
/* 기본: 모바일 퍼스트 (360px~) */
.options-container {
  width: 100%;
  padding: 16px;
  max-width: 640px;
  margin: 0 auto;
}

/* 태블릿 이상 (768px~) */
@media (min-width: 768px) {
  .options-container {
    padding: 32px;
  }
}

/* 데스크톱 (1024px~) */
@media (min-width: 1024px) {
  .options-container {
    padding: 48px;
  }
}
```

### 6.4 토스트 반응형

- AI 사이트 화면 크기에 관계없이 항상 우측 하단 고정
- `position: fixed; bottom: 24px; right: 24px;`
- 너비: 280px 고정 (화면이 좁으면 `right: 12px`로 조정)

---

## 7. 공통 컴포넌트 사양

### 7.1 버튼

| 종류 | 배경 | 텍스트 | 테두리 | 사용처 |
|------|------|--------|--------|--------|
| Primary | `var(--nugget-primary)` | 흰색 | 없음 | CTA, "시작하기" |
| Pro | `var(--color-pro)` | 흰색 | 없음 | "Pro 업그레이드" |
| Secondary | 투명 | Text Secondary | 1px `var(--border-default)` | "백업", "복원" |
| Ghost | 투명 | Text Secondary | 없음 | "설정", 아이콘 버튼 |
| Danger | `var(--color-error)` 10% | Error | 1px Error | "삭제" (현재 미사용) |

**공통:**
- 높이: 32px (소) / 36px (중) / 44px (대)
- 모서리: `var(--radius-md)`
- hover: 밝기 95% (약간 어두워짐)
- active: 밝기 90%
- disabled: opacity 0.5, cursor not-allowed
- transition: `var(--transition-fast)`

### 7.2 토글 스위치

- 크기: 36px x 20px
- 트랙: 라운드 pill
- ON: `var(--nugget-primary)` 배경 + 흰색 원
- OFF: `var(--border-default)` 배경 + 흰색 원
- 애니메이션: 원 이동 150ms ease

### 7.3 칩 (Tag / Filter)

- 크기: padding 2px 8px (태그) / 4px 10px (필터)
- 모서리: `var(--radius-full)` (pill)
- 기본: `var(--bg-surface)` 배경 + Text Secondary
- 활성: 카테고리/플랫폼 색상 배경 10% + 해당 색상 텍스트
- 삭제 가능: 우측에 X 아이콘 (hover 시 표시)

### 7.4 모달 대화상자

- 배경 오버레이: `rgba(0, 0, 0, 0.4)`, 클릭 시 닫힘
- 모달 박스: 흰색 배경, `var(--radius-lg)`, `var(--shadow-lg)`, 너비 320px (Popup 내) / 480px (Options)
- 상단: 제목 (15px Bold) + X 닫기
- 하단: 액션 버튼 우측 정렬
- 애니메이션: scale(0.95) + opacity(0) → scale(1) + opacity(1), 200ms ease

### 7.5 툴팁

- 배경: `rgba(26, 26, 46, 0.9)`
- 텍스트: 11px, 흰색
- 모서리: `var(--radius-sm)` (4px)
- 패딩: 4px 8px
- 위치: 트리거 요소 위 8px
- 화살표: 하단 중앙 4px 삼각형
- 지연: hover 0.5초 후 표시

---

## 8. 아이콘 가이드

### 8.1 아이콘 시스템

- **방식:** SVG 인라인 아이콘 (외부 의존성 없음, CSP 준수)
- **기본 크기:** 16px (텍스트 인라인) / 20px (버튼 아이콘) / 24px (강조 아이콘)
- **색상:** `currentColor` 사용 (부모 텍스트 색상 상속)
- **획 두께:** 1.5px (16px 아이콘) / 2px (20px 이상)

### 8.2 필요 아이콘 목록

| 아이콘 | 용도 | 크기 |
|--------|------|------|
| 돋보기 | 검색 | 16px |
| 필터/깔때기 | 필터 토글 | 16px |
| 별 (빈/찬) | 별표 | 20px |
| 메모/연필 | 메모 | 20px |
| 클립보드/문서 | MD 복사 | 20px |
| 체크 | 복사 완료, 저장 완료 | 16px |
| X / 닫기 | 닫기 버튼, 태그 삭제 | 16px |
| 다운로드 | 백업 | 16px |
| 업로드 | 복원 | 16px |
| 톱니바퀴 | 설정 | 16px |
| 느낌표 (원) | 에러, 경고 | 16px |
| 화살표 (위/아래) | 카드 접기/펼치기 | 12px |
| Nugget 로고 | 브랜드 | 24px / 48px |

### 8.3 플랫폼 아이콘

각 AI 플랫폼은 단순화된 아이콘(문자 기반)으로 표현합니다.
(저작권 문제 방지를 위해 실제 로고 대신 텍스트 아바타 사용)

| 플랫폼 | 표현 | 배경색 | 텍스트 |
|--------|------|--------|--------|
| Claude | "C" | `var(--color-claude)` | 흰색 |
| ChatGPT | "G" | `var(--color-chatgpt)` | 흰색 |
| Gemini | "Ge" | `var(--color-gemini)` | 흰색 |

- 크기: 20px x 20px 원형
- 폰트: 11px Bold, 중앙 정렬
- 필터 칩에서는 이 아이콘 + 플랫폼 이름

---

## 9. 애니메이션 & 트랜지션

### 9.1 원칙

- **최소주의:** 꼭 필요한 곳만 애니메이션. 장식적 모션 없음
- **성능:** `transform`과 `opacity`만 사용 (GPU 가속). `height`, `width` 애니메이션 지양
- **접근성:** `prefers-reduced-motion: reduce` 미디어 쿼리 대응

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 9.2 애니메이션 목록

| 요소 | 트리거 | 애니메이션 | 시간 |
|------|--------|-----------|------|
| 토스트 (진입) | 저장 이벤트 | translateY(16px) → 0 + fade in | 300ms ease-out |
| 토스트 (퇴장) | 1.5초 후 | fade out | 300ms ease-in |
| 카드 펼치기 | 클릭 | max-height 0 → auto (CSS) | 250ms ease |
| 필터 행 | 필터 버튼 클릭 | slideDown (max-height) | 250ms ease |
| Today's Nugget 닫기 | X 클릭 | max-height → 0 + fade out | 200ms ease |
| 카드 hover | 마우스 진입 | box-shadow 강화 | 150ms ease |
| 별표 토글 | 클릭 | scale(1.2) → scale(1) + 색상 변경 | 200ms ease |
| 스켈레톤 | 로딩 중 | shimmer (배경 이동) | 1.5s infinite |
| 모달 진입 | 이벤트 | scale(0.95) → 1 + fade in | 200ms ease |
| 검색 하이라이트 대상 카드 | Today's Nugget 클릭 | 0.5초 골드 glow 후 fade | 500ms ease |

---

## 10. 접근성 (Accessibility)

### 10.1 기본 원칙

- **키보드 탐색:** 모든 인터랙티브 요소는 Tab으로 접근 가능
- **포커스 표시:** `outline: 2px solid var(--nugget-primary); outline-offset: 2px;`
- **색상 대비:** WCAG 2.1 AA 기준 준수 (일반 텍스트 4.5:1, 대형 텍스트 3:1)
- **스크린 리더:** 의미있는 `aria-label` 제공

### 10.2 주요 aria 속성

| 요소 | 속성 |
|------|------|
| 검색 입력 | `role="search"`, `aria-label="대화 검색"` |
| 필터 토글 | `aria-expanded="true/false"`, `aria-controls="filter-panel"` |
| 카드 접기/펼치기 | `aria-expanded="true/false"` |
| 별표 버튼 | `aria-pressed="true/false"`, `aria-label="별표"` |
| 토글 스위치 | `role="switch"`, `aria-checked="true/false"` |
| 토스트 | `role="status"`, `aria-live="polite"` |
| 에러 배너 | `role="alert"` |
| 모달 | `role="dialog"`, `aria-modal="true"`, 포커스 트랩 |

---

## 11. 플랫폼별 태그 색상

태그 카테고리별 색상은 플랫폼 색상과 구분되는 별도 팔레트를 사용합니다.

| 태그 | 배경 (10%) | 텍스트 | HEX |
|------|-----------|--------|-----|
| 코딩 | `rgba(59, 130, 246, 0.1)` | `#3B82F6` | 파랑 |
| 글쓰기 | `rgba(16, 185, 129, 0.1)` | `#10B981` | 청록 |
| 업무 | `rgba(245, 158, 11, 0.1)` | `#F59E0B` | 주황 |
| 학습 | `rgba(139, 92, 246, 0.1)` | `#8B5CF6` | 보라 |
| 크리에이티브 | `rgba(236, 72, 153, 0.1)` | `#EC4899` | 핑크 |
| 기타 | `rgba(107, 114, 128, 0.1)` | `#6B7280` | 회색 |

---

# v1.1 업데이트 — 다크모드 & i18n UI 가이드

> 이 섹션은 v1.0 디자인을 유지하면서 v1.1에서 추가되는 다크모드 테마, 언어 설정 UI,
> Options 페이지 재구성에 대한 가이드라인을 정의합니다.
> 참조: `.plan.v1.1.md` AC-V11-10 ~ AC-V11-20

---

## 12. 다크모드 테마 디자인

### 12.1 테마 모드

Nugget은 3가지 테마 모드를 지원합니다:

| 모드 | 동작 | 설정값 |
|------|------|--------|
| 라이트 | 항상 라이트 테마 적용 | `'light'` |
| 다크 | 항상 다크 테마 적용 | `'dark'` |
| 시스템 | OS의 `prefers-color-scheme` 따라감 | `'system'` (기본값) |

**적용 방식:**
- `<html>` 또는 `<body>` 요소에 `data-theme="light"` 또는 `data-theme="dark"` 속성 부여
- `system` 선택 시 `window.matchMedia('(prefers-color-scheme: dark)')` 결과에 따라 결정
- `prefers-color-scheme` 변경 시 실시간 반영 (`MediaQueryList.addEventListener('change', ...)`)

```js
// Theme initialization pseudo-code
function applyTheme(themeSetting) {
  let resolved = themeSetting;
  if (themeSetting === 'system') {
    resolved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', resolved);
}
```

### 12.2 다크모드 색상 팔레트

#### 12.2.1 시스템 색상 — 라이트 vs 다크

| CSS 변수 | 라이트 값 (v1.0 유지) | 다크 값 | 용도 |
|----------|---------------------|---------|------|
| `--bg-primary` | `#FFFFFF` | `#1A1A2E` | 전체 배경 |
| `--bg-surface` | `#F8F9FA` | `#252540` | 카드 배경, 입력 필드 배경 |
| `--bg-surface-hover` | `#F1F3F5` | `#2E2E4A` | 카드 hover |
| `--bg-elevated` | `#FFFFFF` | `#2E2E4A` | 모달, 드롭다운, 팝오버 배경 (v1.1 신규) |
| `--border-default` | `#E1E4E8` | `#3A3A5C` | 테두리, 구분선 |
| `--border-subtle` | `#F1F3F5` | `#2E2E4A` | 약한 구분선 (v1.1 신규) |
| `--text-primary` | `#1A1A2E` | `#E8E8F0` | 제목, 본문 |
| `--text-secondary` | `#6B7280` | `#A0A0B8` | 부제목, 메타 정보 |
| `--text-tertiary` | `#9CA3AF` | `#6B6B85` | 비활성 텍스트, 힌트 |
| `--text-on-primary` | `#FFFFFF` | `#FFFFFF` | Primary 배경 위 텍스트 (v1.1 신규) |

#### 12.2.2 브랜드 색상 — 다크 배경 조정

| CSS 변수 | 라이트 값 | 다크 값 | 조정 이유 |
|----------|---------|---------|----------|
| `--nugget-primary` | `#F5A623` | `#F5A623` | 유지 — 다크 배경에서 대비 충분 (대비비 4.8:1 on #1A1A2E) |
| `--nugget-primary-dark` | `#D4891A` | `#FFB940` | 밝게 조정 — hover/active 상태에서 다크 배경과 구분 |
| `--nugget-primary-light` | `#FFF3DC` | `#3D2E1A` | 다크 톤의 골드 배경 — Today's Nugget, 선택 하이라이트 |

**Nugget Gold 다크모드 지침:**
- `#F5A623`은 다크 배경(`#1A1A2E`)에서 대비비 약 4.8:1로 WCAG AA를 통과하므로 **변경 없이 유지**합니다.
- `--nugget-primary-light`만 다크 환경에서는 어두운 골드 톤(`#3D2E1A`)으로 반전합니다.
  이 색상은 Today's Nugget 배경이나 선택 상태 하이라이트에 사용됩니다.
- hover/active에 사용하는 `--nugget-primary-dark`는 다크 배경에서 더 밝은 `#FFB940`으로 조정하여 시인성을 확보합니다.

#### 12.2.3 플랫폼 식별 색상 — 다크 배경 조정

| CSS 변수 | 라이트 값 | 다크 값 | 조정 근거 |
|----------|---------|---------|----------|
| `--color-claude` | `#7C3AED` | `#9B6BFF` | 밝기 +15%. 다크 배경 대비비 4.5:1 이상 확보 |
| `--color-chatgpt` | `#10A37F` | `#34D399` | 밝기 +20%. #10A37F는 다크 배경에서 대비 부족 |
| `--color-gemini` | `#4285F4` | `#60A5FA` | 밝기 +15%. 가독성 향상 |

**플랫폼 컬러 다크모드 지침:**
- 카드 좌측 4px 스트라이프: 다크 값 사용 (시인성 확보)
- 필터 칩 텍스트: 다크 값 사용
- 필터 칩 배경 (10% 투명도): 다크 값 기준으로 재계산
  - Claude: `rgba(155, 107, 255, 0.15)` (다크에서 투명도 15%로 상향)
  - ChatGPT: `rgba(52, 211, 153, 0.15)`
  - Gemini: `rgba(96, 165, 250, 0.15)`
- 플랫폼 아이콘(원형 텍스트 아바타): 배경색은 다크 값, 텍스트는 `#FFFFFF` 유지

#### 12.2.4 상태 색상 — 다크 배경 조정

| CSS 변수 | 라이트 값 | 다크 값 | 비고 |
|----------|---------|---------|------|
| `--color-success` | `#22C55E` | `#34D399` | 밝기 +10% |
| `--color-warning` | `#F59E0B` | `#FBBF24` | 밝기 +8% |
| `--color-error` | `#EF4444` | `#F87171` | 밝기 +12% |
| `--color-info` | `#3B82F6` | `#60A5FA` | 밝기 +15% |
| `--color-pro` | `#8B5CF6` | `#A78BFA` | 밝기 +12% |

#### 12.2.5 태그 카테고리 색상 — 다크 배경 조정

| 태그 | 다크 배경 (15%) | 다크 텍스트 |
|------|----------------|-----------|
| 코딩 | `rgba(96, 165, 250, 0.15)` | `#60A5FA` |
| 글쓰기 | `rgba(52, 211, 153, 0.15)` | `#34D399` |
| 업무 | `rgba(251, 191, 36, 0.15)` | `#FBBF24` |
| 학습 | `rgba(167, 139, 250, 0.15)` | `#A78BFA` |
| 크리에이티브 | `rgba(244, 114, 182, 0.15)` | `#F472B6` |
| 기타 | `rgba(156, 163, 175, 0.15)` | `#9CA3AF` |

**다크 태그 지침:** 배경 투명도를 10%에서 15%로 높여 다크 배경에서 태그 칩의 시인성을 확보합니다.

#### 12.2.6 그림자(Shadow) — 다크 모드

| CSS 변수 | 라이트 값 | 다크 값 |
|----------|---------|---------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | `0 1px 2px rgba(0,0,0,0.3)` |
| `--shadow-md` | `0 2px 8px rgba(0,0,0,0.1)` | `0 2px 8px rgba(0,0,0,0.4)` |
| `--shadow-lg` | `0 4px 16px rgba(0,0,0,0.12)` | `0 4px 16px rgba(0,0,0,0.5)` |

**다크 그림자 지침:** 다크 배경에서 그림자는 매우 보이기 어려우므로, 불투명도를 대폭 높여 카드 분리감을 유지합니다.

#### 12.2.7 기타 다크 전용 변수

| CSS 변수 | 다크 값 | 용도 |
|----------|---------|------|
| `--overlay-bg` | `rgba(0, 0, 0, 0.6)` | 모달 배경 오버레이 (라이트: `rgba(0,0,0,0.4)`) |
| `--skeleton-base` | `#252540` | 스켈레톤 기본 색상 |
| `--skeleton-shine` | `#3A3A5C` | 스켈레톤 shimmer 피크 색상 |
| `--highlight-search` | `#78500A` | 검색 하이라이트 배경 (라이트: `#FEF08A`) |
| `--scrollbar-thumb` | `#3A3A5C` | 스크롤바 색상 (라이트: 기본 회색) |
| `--scrollbar-thumb-hover` | `#505070` | 스크롤바 hover (v1.1 신규) |

### 12.3 완전한 CSS 변수 정의 (라이트 + 다크)

프론트엔드 개발자는 아래 CSS를 각 페이지(popup.css, options.css, onboarding.css)의 최상단에 추가합니다.

```css
/* ==============================
   Nugget v1.1 Theme Variables
   ============================== */

/* --- Light Theme (default) --- */
:root,
[data-theme="light"] {
  /* Brand */
  --nugget-primary: #F5A623;
  --nugget-primary-dark: #D4891A;
  --nugget-primary-light: #FFF3DC;

  /* Platform */
  --color-claude: #7C3AED;
  --color-chatgpt: #10A37F;
  --color-gemini: #4285F4;

  /* System */
  --bg-primary: #FFFFFF;
  --bg-surface: #F8F9FA;
  --bg-surface-hover: #F1F3F5;
  --bg-elevated: #FFFFFF;
  --border-default: #E1E4E8;
  --border-subtle: #F1F3F5;
  --text-primary: #1A1A2E;
  --text-secondary: #6B7280;
  --text-tertiary: #9CA3AF;
  --text-on-primary: #FFFFFF;

  /* State */
  --color-success: #22C55E;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  --color-info: #3B82F6;
  --color-pro: #8B5CF6;

  /* Shadow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.1);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.12);

  /* Overlay */
  --overlay-bg: rgba(0, 0, 0, 0.4);

  /* Skeleton */
  --skeleton-base: #F1F3F5;
  --skeleton-shine: #E1E4E8;

  /* Search highlight */
  --highlight-search: #FEF08A;

  /* Scrollbar */
  --scrollbar-thumb: #CCC;
  --scrollbar-thumb-hover: #AAA;

  /* Tag backgrounds (10% opacity in light) */
  --tag-coding-bg: rgba(59, 130, 246, 0.1);
  --tag-coding-text: #3B82F6;
  --tag-writing-bg: rgba(16, 185, 129, 0.1);
  --tag-writing-text: #10B981;
  --tag-work-bg: rgba(245, 158, 11, 0.1);
  --tag-work-text: #F59E0B;
  --tag-study-bg: rgba(139, 92, 246, 0.1);
  --tag-study-text: #8B5CF6;
  --tag-creative-bg: rgba(236, 72, 153, 0.1);
  --tag-creative-text: #EC4899;
  --tag-other-bg: rgba(107, 114, 128, 0.1);
  --tag-other-text: #6B7280;

  /* Platform chip backgrounds (10% opacity in light) */
  --chip-claude-bg: rgba(124, 58, 237, 0.1);
  --chip-chatgpt-bg: rgba(16, 163, 127, 0.1);
  --chip-gemini-bg: rgba(66, 133, 244, 0.1);

  /* Spacing (unchanged from v1.0) */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;

  /* Border Radius (unchanged) */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;

  /* Typography (unchanged) */
  --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-size-xs: 11px;
  --font-size-sm: 12px;
  --font-size-md: 13px;
  --font-size-lg: 15px;
  --font-size-xl: 17px;

  /* Transition (unchanged) */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}

/* --- Dark Theme --- */
[data-theme="dark"] {
  /* Brand */
  --nugget-primary: #F5A623;
  --nugget-primary-dark: #FFB940;
  --nugget-primary-light: #3D2E1A;

  /* Platform */
  --color-claude: #9B6BFF;
  --color-chatgpt: #34D399;
  --color-gemini: #60A5FA;

  /* System */
  --bg-primary: #1A1A2E;
  --bg-surface: #252540;
  --bg-surface-hover: #2E2E4A;
  --bg-elevated: #2E2E4A;
  --border-default: #3A3A5C;
  --border-subtle: #2E2E4A;
  --text-primary: #E8E8F0;
  --text-secondary: #A0A0B8;
  --text-tertiary: #6B6B85;
  --text-on-primary: #FFFFFF;

  /* State */
  --color-success: #34D399;
  --color-warning: #FBBF24;
  --color-error: #F87171;
  --color-info: #60A5FA;
  --color-pro: #A78BFA;

  /* Shadow */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 2px 8px rgba(0,0,0,0.4);
  --shadow-lg: 0 4px 16px rgba(0,0,0,0.5);

  /* Overlay */
  --overlay-bg: rgba(0, 0, 0, 0.6);

  /* Skeleton */
  --skeleton-base: #252540;
  --skeleton-shine: #3A3A5C;

  /* Search highlight */
  --highlight-search: #78500A;

  /* Scrollbar */
  --scrollbar-thumb: #3A3A5C;
  --scrollbar-thumb-hover: #505070;

  /* Tag backgrounds (15% opacity in dark) */
  --tag-coding-bg: rgba(96, 165, 250, 0.15);
  --tag-coding-text: #60A5FA;
  --tag-writing-bg: rgba(52, 211, 153, 0.15);
  --tag-writing-text: #34D399;
  --tag-work-bg: rgba(251, 191, 36, 0.15);
  --tag-work-text: #FBBF24;
  --tag-study-bg: rgba(167, 139, 250, 0.15);
  --tag-study-text: #A78BFA;
  --tag-creative-bg: rgba(244, 114, 182, 0.15);
  --tag-creative-text: #F472B6;
  --tag-other-bg: rgba(156, 163, 175, 0.15);
  --tag-other-text: #9CA3AF;

  /* Platform chip backgrounds (15% opacity in dark) */
  --chip-claude-bg: rgba(155, 107, 255, 0.15);
  --chip-chatgpt-bg: rgba(52, 211, 153, 0.15);
  --chip-gemini-bg: rgba(96, 165, 250, 0.15);
}
```

### 12.4 컴포넌트별 다크모드 스타일

#### 12.4.1 카드 (대화 엔트리)

```css
/* Card — light is default from v1.0, dark overrides below */
[data-theme="dark"] .entry-card {
  background: var(--bg-surface);
  border-color: var(--border-default);
  box-shadow: var(--shadow-sm);
}

[data-theme="dark"] .entry-card:hover {
  background: var(--bg-surface-hover);
  box-shadow: var(--shadow-md);
}

/* Card stripe (platform color) uses CSS variables, auto-adapts */
/* Card question text */
[data-theme="dark"] .card-question {
  color: var(--text-primary);  /* #E8E8F0 */
}

/* Card answer text */
[data-theme="dark"] .card-answer {
  color: var(--text-secondary);  /* #A0A0B8 */
}

/* Card meta info (date, tags) */
[data-theme="dark"] .card-meta {
  color: var(--text-tertiary);  /* #6B6B85 */
}
```

#### 12.4.2 버튼

| 종류 | 다크 배경 | 다크 텍스트 | 다크 테두리 |
|------|----------|-----------|-----------|
| Primary | `var(--nugget-primary)` | `var(--text-on-primary)` | 없음 |
| Pro | `var(--color-pro)` | `var(--text-on-primary)` | 없음 |
| Secondary | `transparent` | `var(--text-secondary)` | 1px `var(--border-default)` |
| Ghost | `transparent` | `var(--text-secondary)` | 없음 |
| Danger | `rgba(248,113,113, 0.1)` | `var(--color-error)` | 1px `var(--color-error)` |

```css
/* Button hover in dark mode */
[data-theme="dark"] .btn-primary:hover {
  filter: brightness(1.1);  /* dark에서는 밝게 */
}

[data-theme="dark"] .btn-secondary:hover {
  background: var(--bg-surface-hover);
}

[data-theme="dark"] .btn-ghost:hover {
  background: var(--bg-surface);
}
```

**다크 버튼 hover 지침:** 라이트에서는 `brightness(0.95)` (어둡게), 다크에서는 `brightness(1.1)` (밝게)로 반전합니다.

#### 12.4.3 입력 필드

```css
[data-theme="dark"] input,
[data-theme="dark"] textarea,
[data-theme="dark"] select {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-default);
}

[data-theme="dark"] input:focus,
[data-theme="dark"] textarea:focus,
[data-theme="dark"] select:focus {
  border-color: var(--nugget-primary);
  box-shadow: 0 0 0 2px rgba(245, 166, 35, 0.2);
}

[data-theme="dark"] input::placeholder,
[data-theme="dark"] textarea::placeholder {
  color: var(--text-tertiary);
}
```

#### 12.4.4 토글 스위치

```css
/* Toggle — ON state uses --nugget-primary (same in both themes) */
/* Toggle — OFF state */
[data-theme="dark"] .toggle-track.off {
  background: var(--border-default);  /* #3A3A5C */
}
```

#### 12.4.5 칩 (Tag / Filter)

```css
/* Chip base — dark */
[data-theme="dark"] .chip {
  background: var(--bg-surface-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

/* Chip active — uses tag/platform CSS variables, auto-adapts */
```

#### 12.4.6 모달 대화상자

```css
[data-theme="dark"] .modal-backdrop {
  background: var(--overlay-bg);  /* rgba(0,0,0,0.6) */
}

[data-theme="dark"] .modal-box {
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-lg);
}
```

#### 12.4.7 툴팁

```css
/* Tooltip is already dark-toned in light mode (rgba(26,26,46,0.9)).
   In dark mode, invert to a lighter tooltip for contrast. */
[data-theme="dark"] .tooltip {
  background: var(--bg-elevated);  /* #2E2E4A */
  color: var(--text-primary);      /* #E8E8F0 */
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-md);
}
```

#### 12.4.8 토스트 알림 (Content Script)

```css
/* Toast in dark mode — lighter background for contrast against dark sites */
[data-theme="dark"] .nugget-toast {
  background: rgba(46, 46, 74, 0.95);  /* --bg-elevated at 95% */
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}
```

**토스트 다크모드 주의:** Content Script의 토스트는 AI 사이트 위에 렌더링되므로 (Shadow DOM 내부), AI 사이트의 테마가 아닌 Nugget 설정의 테마를 따릅니다. `chrome.storage`에서 theme 값을 읽어 적용합니다.

#### 12.4.9 스켈레톤 로딩

```css
[data-theme="dark"] .skeleton {
  background: linear-gradient(
    90deg,
    var(--skeleton-base) 25%,
    var(--skeleton-shine) 50%,
    var(--skeleton-base) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

#### 12.4.10 에러/경고 배너

```css
/* Error banner — dark */
[data-theme="dark"] .error-banner {
  background: rgba(248, 113, 113, 0.1);  /* error dark color at 10% */
  border-color: var(--color-error);
  color: var(--color-error);
}

/* Warning banner — dark */
[data-theme="dark"] .warning-banner {
  background: rgba(251, 191, 36, 0.1);
  border-color: var(--color-warning);
  color: var(--color-warning);
}
```

#### 12.4.11 포커스 링 (접근성)

```css
/* Focus ring adapts to theme */
[data-theme="dark"] *:focus-visible {
  outline: 2px solid var(--nugget-primary);
  outline-offset: 2px;
}
```

#### 12.4.12 스크롤바

```css
[data-theme="dark"] ::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 4px;
}

[data-theme="dark"] ::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

[data-theme="dark"] ::-webkit-scrollbar-track {
  background: transparent;
}
```

### 12.5 접근성 — 다크모드 색상 대비 검증

WCAG 2.1 AA 기준: 일반 텍스트 4.5:1, 대형 텍스트(18px+) 3:1

| 요소 | 전경색 (다크) | 배경색 (다크) | 대비비 | 판정 |
|------|-------------|-------------|-------|------|
| 본문 텍스트 | `#E8E8F0` | `#1A1A2E` | 11.2:1 | PASS (AAA) |
| 부제목 | `#A0A0B8` | `#1A1A2E` | 5.4:1 | PASS (AA) |
| 비활성 텍스트 | `#6B6B85` | `#1A1A2E` | 2.8:1 | 장식/힌트 전용 (주 정보에 사용 금지) |
| Nugget Gold (CTA) | `#F5A623` | `#1A1A2E` | 4.8:1 | PASS (AA) |
| Nugget Gold (surface) | `#F5A623` | `#252540` | 4.2:1 | PASS (AA, 대형 텍스트) |
| Claude 보라 | `#9B6BFF` | `#1A1A2E` | 4.6:1 | PASS (AA) |
| ChatGPT 초록 | `#34D399` | `#1A1A2E` | 7.8:1 | PASS (AAA) |
| Gemini 파랑 | `#60A5FA` | `#1A1A2E` | 5.6:1 | PASS (AA) |
| 카드 텍스트 | `#E8E8F0` | `#252540` | 9.1:1 | PASS (AAA) |
| 에러 | `#F87171` | `#1A1A2E` | 4.9:1 | PASS (AA) |
| 성공 | `#34D399` | `#1A1A2E` | 7.8:1 | PASS (AAA) |

### 12.6 테마 전환 애니메이션

```css
/* Smooth theme transition — apply to body */
body {
  transition: background-color var(--transition-normal),
              color var(--transition-normal);
}

/* Cards, surfaces also transition */
.entry-card,
.settings-section,
input, textarea, select,
.chip, .btn {
  transition: background-color var(--transition-normal),
              border-color var(--transition-normal),
              color var(--transition-normal),
              box-shadow var(--transition-normal);
}
```

**주의:** `transition: all`은 사용하지 않습니다. 성능을 위해 필요한 속성만 명시합니다.

---

## 13. 언어 설정 UI 디자인

### 13.1 언어 선택 컨트롤

Options 페이지의 "일반 설정" 섹션에 언어 선택 드롭다운을 배치합니다.

**컨트롤 타입:** 커스텀 `<select>` 드롭다운 (네이티브 select에 스타일 적용)

```
┌─────────────────────────────────────────┐
│  언어 (Language)          [한국어    ▼]  │
│                                         │
│  · 자동 (브라우저 언어)                   │  ← 드롭다운 옵션
│  · 한국어                                │
│  · English                              │
└─────────────────────────────────────────┘
```

**드롭다운 사양:**

| 속성 | 값 |
|------|-----|
| 너비 | 160px |
| 높이 | 36px |
| 배경 | `var(--bg-surface)` |
| 테두리 | 1px solid `var(--border-default)` |
| 모서리 | `var(--radius-md)` |
| 텍스트 | `var(--font-size-md)` (13px), `var(--text-primary)` |
| 패딩 | 8px 12px |
| 화살표 | 우측 12px, SVG 삼각형 (8px), `var(--text-tertiary)` |
| focus | `border-color: var(--nugget-primary)` |

**드롭다운 옵션:**

| 값 | 표시 텍스트 | data 속성 |
|-----|----------|----------|
| `auto` | 자동 (브라우저 언어) | `data-i18n="settings_lang_auto"` |
| `ko` | 한국어 | — |
| `en` | English | — |

**레이아웃 상세:**
- 라벨("언어")과 드롭다운은 같은 행에 `display: flex; justify-content: space-between; align-items: center;`
- 라벨: `var(--font-size-md)` (13px), `var(--text-primary)`, font-weight 500
- 라벨 우측에 괄호로 영어 표기 추가 `(Language)` — i18n이 적용되지 않는 고정 텍스트로, 언어가 바뀌어도 어떤 설정인지 식별 가능

### 13.2 언어 변경 시 즉시 반영 피드백

```
[한국어 ▼] → 사용자가 "English" 선택
  ↓
(1) 드롭다운 옆에 체크 아이콘(✓) 0.5초 표시 — 저장 완료 피드백
  ↓
(2) Options 페이지의 모든 i18n 텍스트 즉시 업데이트 (DOM 직접 조작)
  ↓
(3) chrome.storage에 settings.language 저장
```

**즉시 반영 UI:**
- 드롭다운 우측에 16px 체크 아이콘 (`var(--color-success)`) 나타남 → 0.5초 후 페이드아웃
- 페이지 전체 리로드 없이 `data-i18n` 속성이 있는 모든 요소의 텍스트를 JS로 업데이트

### 13.3 테마 선택 컨트롤

언어 선택 바로 아래에 테마 선택을 배치합니다.

**컨트롤 타입:** 세그먼트 버튼 (3-way toggle) — 라디오 버튼 그룹의 시각적 변형

```
┌─────────────────────────────────────────────────────┐
│  테마 (Theme)    [☀ 라이트] [🌙 다크] [💻 시스템]   │
└─────────────────────────────────────────────────────┘
```

**세그먼트 버튼 사양:**

| 속성 | 값 |
|------|-----|
| 전체 너비 | 자동 (내용물에 맞춤) |
| 각 버튼 높이 | 32px |
| 각 버튼 패딩 | 6px 12px |
| 배경 (비선택) | `transparent` |
| 배경 (선택) | `var(--nugget-primary)` |
| 텍스트 (비선택) | `var(--text-secondary)` |
| 텍스트 (선택) | `var(--text-on-primary)` |
| 테두리 | 전체 그룹에 1px solid `var(--border-default)` |
| 모서리 | 전체 그룹 `var(--radius-md)`, 내부 버튼은 0 (첫째/마지막만 좌/우 radius) |
| 구분선 | 버튼 사이 1px solid `var(--border-default)` |
| 텍스트 크기 | `var(--font-size-sm)` (12px) |
| 아이콘 | 각 버튼 좌측에 14px 인라인 아이콘 |

**세그먼트 버튼 옵션:**

| 값 | 아이콘 | 텍스트 |
|-----|------|--------|
| `light` | ☀ (sun SVG) | 라이트 / Light |
| `dark` | 🌙 (moon SVG) | 다크 / Dark |
| `system` | 💻 (monitor SVG) | 시스템 / System |

**테마 변경 시 피드백:**
- 선택 즉시 테마가 현재 페이지에 적용 (data-theme 속성 변경)
- 선택된 버튼에 `var(--nugget-primary)` 배경 + 흰색 텍스트
- 전환 애니메이션은 12.6에 정의된 `transition` 적용
- chrome.storage에 settings.theme 저장

```css
/* Segment button group */
.theme-selector {
  display: inline-flex;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.theme-selector__btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  border: none;
  border-right: 1px solid var(--border-default);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.theme-selector__btn:last-child {
  border-right: none;
}

.theme-selector__btn.active {
  background: var(--nugget-primary);
  color: var(--text-on-primary);
}

.theme-selector__btn:not(.active):hover {
  background: var(--bg-surface-hover);
}

.theme-selector__btn svg {
  width: 14px;
  height: 14px;
}
```

### 13.4 필요 SVG 아이콘 (v1.1 추가)

| 아이콘 | 용도 | 크기 |
|--------|------|------|
| 태양 (sun) | 라이트 테마 버튼 | 14px |
| 달 (moon) | 다크 테마 버튼 | 14px |
| 모니터 (monitor) | 시스템 테마 버튼 | 14px |
| 지구본 (globe) | 언어 설정 라벨 아이콘 (선택사항) | 16px |

---

## 14. Options 페이지 설정 섹션 재구성

### 14.1 전체 레이아웃 (v1.1)

v1.0의 기존 4개 섹션에 "일반 설정" 섹션을 확장하고, 순서를 재배치합니다.

```
+--------------------------------------------------+
|  ⚙ Nugget 설정                                   |
+--------------------------------------------------+
|                                                    |
|  ┌─ 일반 설정 ──────────────────────────────┐     |
|  │  언어 (Language)       [한국어        ▼]  │     |  ← NEW (v1.1)
|  │  테마 (Theme)   [☀라이트][🌙다크][💻시스템]│     |  ← NEW (v1.1)
|  │  ─────────────────────────────────────── │     |  ← 구분선
|  │  토스트 알림           [ON ■□ OFF]        │     |
|  │  잡담 필터             [ON ■□ OFF]        │     |
|  │  단축키                [Ctrl+Shift+S] [변경]│    |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ 잡담 키워드 관리 ───────────────────────┐     |
|  │  (v1.0과 동일)                            │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ 데이터 관리 ────────────────────────────┐     |
|  │  (v1.0과 동일)                            │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  ┌─ Pro 구독 ───────────────────────────────┐     |
|  │  (v1.0과 동일)                            │     |
|  └──────────────────────────────────────────┘     |
|                                                    |
|  Nugget v1.1.0                                    |
+--------------------------------------------------+
```

### 14.2 일반 설정 섹션 상세 (v1.1 확장)

기존 v1.0 일반 설정 항목 **위에** 언어와 테마 설정을 배치하고, 시각적 구분선으로 그룹을 나눕니다.

```
┌─ 일반 설정 ────────────────────────────────────────┐
│                                                     │
│  🌐 언어 (Language)              [한국어        ▼]  │
│                                                     │
│  🎨 테마 (Theme)       [☀ 라이트][🌙 다크][💻 시스템]│
│                                                     │
│  ──────────────────────────────────────────────── │  ← HR 구분선
│                                                     │
│  🔔 토스트 알림                    [ON ■□ OFF]      │
│                                                     │
│  🗑 잡담 필터                      [ON ■□ OFF]      │
│                                                     │
│  ⌨ 단축키                   [Ctrl+Shift+S] [변경]   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**구분선 스타일:**
```css
.settings-divider {
  border: none;
  border-top: 1px solid var(--border-subtle);
  margin: var(--space-lg) 0;  /* 16px 상하 여백 */
}
```

**설정 항목 공통 레이아웃:**
```css
.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) 0;  /* 12px 상하 */
  min-height: 44px;  /* 터치 접근성 */
}

.setting-label {
  display: flex;
  align-items: center;
  gap: var(--space-sm);  /* 8px */
  font-size: var(--font-size-md);  /* 13px */
  font-weight: 500;
  color: var(--text-primary);
}

.setting-label__sub {
  font-weight: 400;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);  /* 12px */
  margin-left: var(--space-xs);  /* 4px */
}
```

### 14.3 설정 섹션 카드 스타일 (다크모드 대응)

```css
.settings-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);  /* 12px */
  padding: var(--space-xl);  /* 24px */
  margin-bottom: var(--space-xl);
}

.settings-section__title {
  font-size: var(--font-size-lg);  /* 15px */
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-lg);  /* 16px */
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--border-default);
}
```

### 14.4 설정 변경 즉시 반영 피드백 UI (공통)

모든 설정 항목에 통일된 저장 피드백을 적용합니다:

```
[설정 변경] → 0.3초 안에 체크 아이콘 나타남 → 0.5초 유지 → 페이드아웃
```

**피드백 아이콘 스타일:**
```css
.setting-saved-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-success);
  font-size: var(--font-size-xs);  /* 11px */
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.setting-saved-indicator.visible {
  opacity: 1;
}
```

**동작 방식:**
- 설정 변경 시 해당 행의 우측 끝(컨트롤 다음)에 체크 아이콘 + "저장됨" 텍스트가 나타남
- 0.5초 후 페이드아웃
- 에러 시: X 아이콘 + "저장 실패" 텍스트 (`var(--color-error)`)

### 14.5 설정 페이지 다크모드 미리보기

Options 페이지에서 테마를 변경하면, 현재 페이지에서 **즉시** 다크모드가 적용되어 사용자가 바로 결과를 확인할 수 있습니다. 이것은 사용자에게 가장 직관적인 피드백입니다.

### 14.6 Options 페이지 상단 헤더 (v1.1)

```css
.options-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.options-header__icon {
  width: 32px;
  height: 32px;
}

.options-header__title {
  font-size: var(--font-size-xl);  /* 17px */
  font-weight: 700;
  color: var(--text-primary);
}

.options-header__version {
  font-size: var(--font-size-xs);  /* 11px */
  color: var(--text-tertiary);
  margin-left: auto;
}
```

---

## 15. 페이지별 다크모드 적용 상세

### 15.1 Popup 다크모드

| 영역 | 라이트 배경 | 다크 배경 | 비고 |
|------|-----------|---------|------|
| Today's Nugget | `--nugget-primary-light` (#FFF3DC) | `--nugget-primary-light` (#3D2E1A) | 자동 전환 |
| 검색바 | `--bg-surface` | `--bg-surface` | 자동 전환 |
| 카드 리스트 배경 | `--bg-primary` | `--bg-primary` | 자동 전환 |
| 개별 카드 | `--bg-primary` (white) | `--bg-surface` (#252540) | 다크에서는 surface 사용 |
| 미니 통계 | `--bg-surface` | `--bg-surface` | 자동 전환 |
| 하단 버튼 영역 | `--bg-primary` | `--bg-primary` | 자동 전환 |
| 용량 경고 배너 | 노란 투명 | 노란 투명 | 색상 변수가 자동 적용 |

### 15.2 Options 다크모드

전체 페이지 배경이 `--bg-primary`로 전환되고, 각 설정 섹션 카드는 `--bg-primary`에서 `--bg-surface`로 시각적 분리를 만듭니다.

```css
[data-theme="dark"] .options-page {
  background: var(--bg-primary);
}

[data-theme="dark"] .settings-section {
  background: var(--bg-surface);
  border-color: var(--border-default);
}
```

### 15.3 Onboarding 다크모드

| 영역 | 라이트 | 다크 |
|------|--------|------|
| 전체 배경 | `#FFFFFF` | `--bg-primary` |
| 샘플 카드 | 카드 스타일 그대로 | 다크 카드 스타일 |
| CTA 버튼 | `--nugget-primary` | `--nugget-primary` (변경 없음) |
| Pro 미리보기 박스 | `--bg-surface` | `--bg-surface` |

### 15.4 토스트 다크모드 (Content Script)

Content Script의 토스트는 Shadow DOM 안에서 독립적으로 렌더링됩니다. Nugget의 테마 설정을 `chrome.storage`에서 읽어 적용합니다.

```js
// Toast theme initialization pseudo-code (inside Shadow DOM)
async function getToastTheme() {
  const { nugget_settings } = await chrome.storage.local.get('nugget_settings');
  const theme = nugget_settings?.theme || 'system';
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme;
}
```

---

## 16. 사용자 동선 추가 (v1.1)

### 16.1 테마 변경 동선

```
사용자가 Options 페이지 열기
  ↓
일반 설정 > 테마에서 "다크" 선택
  ↓
Options 페이지 즉시 다크 테마로 전환 (250ms 트랜지션)
  ↓
settings.theme = 'dark' 저장 (chrome.storage)
  ↓
Popup 다음 열 때 다크 테마 적용
  ↓
Content Script 토스트: chrome.storage.onChanged로 테마 변경 감지 → 다음 토스트부터 적용
```

### 16.2 언어 변경 동선

```
사용자가 Options 페이지 열기
  ↓
일반 설정 > 언어에서 "English" 선택
  ↓
체크 아이콘 피드백 (0.5초)
  ↓
Options 페이지의 모든 텍스트 즉시 영어로 변경 (리로드 없음, AC-V11-12)
  ↓
settings.language = 'en' 저장 (chrome.storage)
  ↓
Popup 다음 열 때 영어 적용
  ↓
Content Script 토스트: chrome.storage.onChanged로 언어 변경 감지 → 다음 토스트부터 적용 (AC-V11-14)
```

---

## 17. i18n 텍스트 마킹 가이드

프론트엔드 개발자는 HTML에서 i18n 대상 텍스트를 `data-i18n` 속성으로 마킹합니다.

### 17.1 마킹 규칙

```html
<!-- 텍스트 노드 교체 -->
<span data-i18n="popup_search_placeholder"></span>

<!-- placeholder 교체 -->
<input data-i18n-placeholder="popup_search_placeholder">

<!-- aria-label 교체 -->
<button data-i18n-aria="btn_close_aria"></button>

<!-- title 속성 교체 -->
<div data-i18n-title="card_date_tooltip"></div>
```

### 17.2 i18n 키 네이밍 컨벤션

```
{페이지}_{섹션}_{요소}

예:
  popup_search_placeholder     → "대화 검색..."
  popup_filter_platform_claude → "Claude"
  popup_stat_this_month        → "이번 달"
  options_general_title        → "일반 설정"
  options_general_language     → "언어"
  options_general_theme        → "테마"
  options_general_toast        → "토스트 알림"
  options_general_junk_filter  → "잡담 필터"
  toast_saved                  → "Nugget이 저장했어요"
  toast_star_added             → "별표 추가"
  toast_star_removed           → "별표 해제"
  onboarding_welcome_title     → "Nugget에 오신 것을 환영해요!"
  common_save                  → "저장"
  common_cancel                → "취소"
  common_close                 → "닫기"
  theme_light                  → "라이트"
  theme_dark                   → "다크"
  theme_system                 → "시스템"
  settings_lang_auto           → "자동 (브라우저 언어)"
```

### 17.3 고정 텍스트 (i18n 미적용)

일부 텍스트는 언어 설정에 관계없이 고정입니다:

| 텍스트 | 이유 |
|--------|------|
| "Nugget" (브랜드명) | 고유명사 |
| "Claude", "ChatGPT", "Gemini" | 플랫폼 고유명사 |
| "Pro" | 플랜 명칭 |
| "v1.1.0" | 버전 번호 |
| 드롭다운의 "한국어", "English" | 언어 이름은 해당 언어로 표기 |

---

## 18. 다크모드 관련 추가 접근성 고려사항

### 18.1 prefers-color-scheme 미디어 쿼리

`system` 모드일 때 OS 테마 변경을 실시간 감지합니다.

```js
// System theme change listener
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
mediaQuery.addEventListener('change', (e) => {
  if (currentThemeSetting === 'system') {
    applyTheme('system');
  }
});
```

### 18.2 prefers-reduced-motion + 다크모드

테마 전환 애니메이션도 reduced-motion 설정을 존중합니다:

```css
@media (prefers-reduced-motion: reduce) {
  body,
  .entry-card,
  .settings-section,
  input, textarea, select,
  .chip, .btn {
    transition-duration: 0.01ms !important;
  }
}
```

### 18.3 고대비 모드 (High Contrast)

향후 고대비 모드 지원을 위해, 다크 테마의 `--text-primary`를 `#E8E8F0`(순백이 아닌 약간 차분한 흰색)으로 설정했습니다. 순백(`#FFFFFF`)은 다크 배경에서 눈부심을 유발할 수 있습니다.

---

## 19. 디자인 토큰 요약 (v1.1 변경 목록)

### 19.1 신규 CSS 변수

| 변수명 | 라이트 | 다크 | 용도 |
|--------|--------|------|------|
| `--bg-elevated` | `#FFFFFF` | `#2E2E4A` | 모달, 드롭다운 배경 |
| `--border-subtle` | `#F1F3F5` | `#2E2E4A` | 약한 구분선 |
| `--text-on-primary` | `#FFFFFF` | `#FFFFFF` | Primary 배경 위 텍스트 |
| `--overlay-bg` | `rgba(0,0,0,0.4)` | `rgba(0,0,0,0.6)` | 모달 오버레이 |
| `--skeleton-base` | `#F1F3F5` | `#252540` | 스켈레톤 기본 |
| `--skeleton-shine` | `#E1E4E8` | `#3A3A5C` | 스켈레톤 shimmer |
| `--highlight-search` | `#FEF08A` | `#78500A` | 검색 하이라이트 |
| `--scrollbar-thumb` | `#CCC` | `#3A3A5C` | 스크롤바 |
| `--scrollbar-thumb-hover` | `#AAA` | `#505070` | 스크롤바 hover |
| `--tag-*-bg` | (각 태그별) | (각 태그별) | 태그 배경 |
| `--tag-*-text` | (각 태그별) | (각 태그별) | 태그 텍스트 |
| `--chip-*-bg` | (각 플랫폼별) | (각 플랫폼별) | 플랫폼 칩 배경 |

### 19.2 v1.0에서 변경된 값 (다크 테마에서만)

| 변수명 | v1.0 값 | 다크 값 | 변경 이유 |
|--------|---------|---------|----------|
| `--nugget-primary-dark` | `#D4891A` | `#FFB940` | hover 시인성 |
| `--nugget-primary-light` | `#FFF3DC` | `#3D2E1A` | 배경 톤 반전 |
| `--color-claude` | `#7C3AED` | `#9B6BFF` | 대비 확보 |
| `--color-chatgpt` | `#10A37F` | `#34D399` | 대비 확보 |
| `--color-gemini` | `#4285F4` | `#60A5FA` | 대비 확보 |
| `--color-success` | `#22C55E` | `#34D399` | 대비 확보 |
| `--color-warning` | `#F59E0B` | `#FBBF24` | 대비 확보 |
| `--color-error` | `#EF4444` | `#F87171` | 대비 확보 |
| `--color-info` | `#3B82F6` | `#60A5FA` | 대비 확보 |
| `--color-pro` | `#8B5CF6` | `#A78BFA` | 대비 확보 |

### 19.3 라이트 테마에서 변경 없는 항목

v1.0의 `:root` CSS 변수 값은 모두 그대로 유지됩니다. `[data-theme="light"]` 셀렉터를 추가하되, 값은 v1.0과 동일합니다. 이로써 v1.0 → v1.1 마이그레이션 시 시각적 변화가 없습니다.

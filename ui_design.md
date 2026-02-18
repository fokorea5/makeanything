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

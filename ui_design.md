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

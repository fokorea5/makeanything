/**
 * Nugget – AI Chat Memory: 공유 타입 정의
 *
 * 이 파일은 기술 아키텍트가 관리합니다. 개발자는 읽기만 가능합니다.
 * 타입 변경이 필요하면 아키텍트에게 요청하세요.
 *
 * 사용법: 각 JS 파일 상단에서 참조 (번들러 없으므로 JSDoc으로만 사용)
 * Content Script에는 manifest.json에서 이 파일을 먼저 주입합니다.
 */

// ============================================================
// 엔트리 (대화 저장 단위)
// ============================================================

/**
 * AI 대화 플랫폼 식별자
 * @typedef {'claude' | 'chatgpt' | 'gemini'} Platform
 */

/**
 * 자동 태깅 태그 종류
 * @typedef {'코딩' | '글쓰기' | '업무' | '학습' | '크리에이티브' | '기타'} AutoTag
 */

/**
 * 저장된 대화 엔트리 (AC-26)
 * @typedef {Object} NuggetEntry
 * @property {string} id - 고유 ID (crypto.randomUUID() 또는 타임스탬프+랜덤)
 * @property {string} date - ISO 8601 문자열 (예: "2026-02-18T14:30:00.000Z")
 * @property {Platform} platform - AI 플랫폼 식별자
 * @property {string} question - 사용자 질문 원문
 * @property {string} answer - AI 답변 원문
 * @property {string[]} tags - 자동/커스텀 태그 배열
 * @property {boolean} starred - 별표 여부 (기본: false)
 * @property {boolean} isJunk - 잡담 여부 (기본: false)
 * @property {boolean} archived - 아카이브 여부 — 무료 한도 초과 시 (기본: false)
 * @property {string} sourceUrl - 대화가 발생한 페이지 URL
 * @property {string} note - 사용자 메모 (기본: "")
 * @property {string} hash - 중복 방지용 해시 (question + answer 앞 200자 + date)
 */

// ============================================================
// 설정
// ============================================================

/**
 * 사용자 설정 (AC-27)
 * @typedef {Object} NuggetSettings
 * @property {boolean} toastEnabled - 토스트 알림 on/off (기본: true)
 * @property {boolean} junkFilterEnabled - 잡담 필터 on/off (기본: true)
 * @property {string} shortcutKey - 단축키 표시용 (기본: "Ctrl+Shift+S", 읽기 전용)
 * @property {number} maxFreeEntries - 무료 한도 (기본: 500, 상수)
 * @property {boolean} isPro - Pro 여부 로컬 캐시 (기본: false)
 * @property {number} mdCopyCount - 이번 달 MD 복사 횟수 (기본: 0)
 * @property {string} mdCopyResetDate - MD 복사 카운터 리셋 날짜 (ISO date, 매월 1일 0시 UTC)
 */

/**
 * ExtensionPay Pro 상태 캐시 (AC-24a)
 * @typedef {Object} ProStatusCache
 * @property {boolean} paid - ExtensionPay getUser().paid 결과
 * @property {string} checkedAt - 마지막 확인 시각 (ISO 8601)
 */

// ============================================================
// 메시지 (chrome.runtime.sendMessage)
// ============================================================

/**
 * Chrome 메시지 공통 형식
 * @typedef {Object} NuggetMessage
 * @property {MessageType} type - 메시지 타입
 * @property {Object} [payload] - 메시지 데이터
 */

/**
 * 메시지 타입 열거
 * @typedef {'SAVE_ENTRY' | 'SELECTOR_FAILED' | 'GET_ENTRIES' | 'SEARCH_ENTRIES' |
 *   'TOGGLE_STAR' | 'UPDATE_NOTE' | 'COPY_MARKDOWN' | 'GET_TODAYS_NUGGET' |
 *   'DISMISS_TODAYS_NUGGET' | 'ADD_CUSTOM_TAG' | 'GET_SETTINGS' | 'UPDATE_SETTINGS' |
 *   'GET_PRO_STATUS' | 'OPEN_PAYMENT_PAGE' | 'GET_JUNK_KEYWORDS' | 'UPDATE_JUNK_KEYWORDS' |
 *   'EXPORT_JSON' | 'IMPORT_JSON' | 'EXPORT_MARKDOWN_FILE' | 'EXPORT_PDF' |
 *   'PRO_STATUS_CHANGED' | 'SHOW_TOAST'} MessageType
 */

// ============================================================
// 검색 필터
// ============================================================

/**
 * 검색/필터 옵션 (AC-10)
 * @typedef {Object} SearchFilters
 * @property {string} [query] - 키워드 검색어 (질문+답변+메모 전문)
 * @property {Platform} [platform] - 플랫폼 필터
 * @property {string} [dateFrom] - 기간 필터 시작 (ISO date)
 * @property {string} [dateTo] - 기간 필터 끝 (ISO date)
 * @property {string} [tag] - 태그 필터
 * @property {boolean} [starredOnly] - 별표만 필터 (기본: false)
 * @property {boolean} [includeJunk] - 잡담 포함 여부 (기본: false)
 */

// ============================================================
// 메시지 페이로드 타입
// ============================================================

/**
 * SAVE_ENTRY 요청 페이로드
 * @typedef {Object} SaveEntryPayload
 * @property {string} question - 사용자 질문
 * @property {string} answer - AI 답변
 * @property {Platform} platform - 플랫폼 식별자
 * @property {string} sourceUrl - 페이지 URL
 */

/**
 * SAVE_ENTRY 응답
 * @typedef {Object} SaveEntryResponse
 * @property {boolean} success
 * @property {NuggetEntry} [entry] - 저장된 엔트리 (성공 시)
 * @property {string} [error] - 에러 메시지 (실패 시)
 */

/**
 * SELECTOR_FAILED 페이로드
 * @typedef {Object} SelectorFailedPayload
 * @property {Platform} platform
 * @property {string} selector - 실패한 셀렉터 문자열
 * @property {string} error - 에러 메시지
 */

/**
 * GET_ENTRIES / SEARCH_ENTRIES 응답
 * @typedef {Object} EntriesResponse
 * @property {NuggetEntry[]} entries
 */

/**
 * TOGGLE_STAR 응답
 * @typedef {Object} ToggleStarResponse
 * @property {boolean} success
 * @property {boolean} starred - 토글 후 별표 상태
 */

/**
 * COPY_MARKDOWN 응답
 * @typedef {Object} CopyMarkdownResponse
 * @property {boolean} success
 * @property {string} [markdown] - 마크다운 문자열 (성공 시)
 * @property {boolean} [limitReached] - 무료 한도 도달 여부
 */

/**
 * GET_PRO_STATUS 응답 (AC-24a)
 * @typedef {Object} ProStatusResponse
 * @property {boolean} isPro
 * @property {boolean} cached - 캐시된 값인지 여부
 * @property {boolean} [expired] - 캐시 만료 여부 (true이면 "구독 확인 필요" 배너)
 */

/**
 * IMPORT_JSON 응답
 * @typedef {Object} ImportJsonResponse
 * @property {boolean} success
 * @property {number} imported - 가져온 엔트리 수
 * @property {number} skipped - 중복으로 건너뛴 수
 */

/**
 * EXPORT_JSON 응답
 * @typedef {Object} ExportJsonData
 * @property {NuggetEntry[]} entries
 * @property {NuggetSettings} settings
 * @property {string} exportDate - ISO 8601
 */

// ============================================================
// DOM 셀렉터 타입 (src/config/selectors.js)
// ============================================================

/**
 * 플랫폼별 DOM 셀렉터 세트
 * @typedef {Object} PlatformSelectors
 * @property {string} conversationContainer - 대화 컨테이너 (MutationObserver 타겟)
 * @property {string} userMessage - 사용자 질문 요소
 * @property {string} assistantMessage - AI 답변 요소
 * @property {string} streamingIndicator - 스트리밍 진행 중 표시자
 */

/**
 * 전체 셀렉터 설정
 * @typedef {Object} SelectorsConfig
 * @property {PlatformSelectors} claude
 * @property {PlatformSelectors} chatgpt
 * @property {PlatformSelectors} gemini
 */

// ============================================================
// 기본값
// ============================================================

/**
 * NuggetSettings 기본값
 * @type {NuggetSettings}
 */
const DEFAULT_SETTINGS = {
  toastEnabled: true,
  junkFilterEnabled: true,
  shortcutKey: 'Ctrl+Shift+S',
  maxFreeEntries: 500,
  isPro: false,
  mdCopyCount: 0,
  mdCopyResetDate: new Date(Date.UTC(
    new Date().getUTCFullYear(),
    new Date().getUTCMonth(),
    1
  )).toISOString().slice(0, 10)
};

/**
 * 기본 잡담 키워드 목록 (AC-6)
 * @type {string[]}
 */
const DEFAULT_JUNK_KEYWORDS = [
  '안녕', '고마워', '감사', 'ㅋㅋ', 'ㅎㅎ', 'ㅠㅠ', '오케이', 'ㅇㅋ', '굿',
  'hi', 'hello', 'thanks', 'thank you', 'ok', 'okay', 'bye', 'lol', 'haha',
  'good', 'nice', 'cool', 'yes', 'no', 'sure', 'yep', 'nope'
];

/**
 * Nugget – AI Chat Memory: 공유 상수
 *
 * DESIGN.md 섹션 8.4 통합 계약 기준.
 * 이 파일의 상수명을 임의로 변경하지 마세요.
 */

// ExtensionPay 등록 ID (실제 배포 시 대시보드에서 받은 ID로 교체)
const NUGGET_EXTENSION_ID = 'nugget-ai-chat-memory';

// 무료 플랜 한도
const MAX_FREE_ENTRIES = 500;
const FREE_ARCHIVE_WARNING_THRESHOLD = 400; // 80%
const MAX_FREE_MD_COPIES_PER_MONTH = 20;
const MAX_FREE_NOTE_LENGTH = 200;

// Pro 상태 캐시 유효 기간 (일)
const PRO_CACHE_VALIDITY_DAYS = 7;

// UI 타이밍
const TOAST_DURATION_MS = 1800;        // 1.5~2초 사이 (AC-19)
const STREAMING_DEBOUNCE_MS = 1000;    // 스트리밍 완료 판단 debounce (AC-2)

// 자동 태깅 기본 태그 목록 (AC-8)
const DEFAULT_TAGS = ['코딩', '글쓰기', '업무', '학습', '크리에이티브', '기타'];

// 플랫폼 식별자 (AC-1)
const PLATFORM_CLAUDE = 'claude';
const PLATFORM_CHATGPT = 'chatgpt';
const PLATFORM_GEMINI = 'gemini';

// ============================================================
// [v1.1] i18n 관련 상수 (AC-V11-10 ~ AC-V11-14)
// ============================================================

/** 지원 언어 목록 */
const SUPPORTED_LANGUAGES = ['ko', 'en'];

/** 언어 설정 기본값: 브라우저 언어 자동 감지 */
const DEFAULT_LANGUAGE = 'auto';

/** 폴백 언어: 감지 실패 또는 미지원 언어일 때 */
const FALLBACK_LANGUAGE = 'ko';

// ============================================================
// [v1.1] 테마 관련 상수 (AC-V11-15 ~ AC-V11-20)
// ============================================================

/** 지원 테마 목록 */
const SUPPORTED_THEMES = ['light', 'dark', 'system'];

/** 테마 설정 기본값: OS 따라감 */
const DEFAULT_THEME = 'system';

// ============================================================
// [v1.1] 원격 셀렉터 관련 상수 (AC-V11-6 ~ AC-V11-9)
// ============================================================

/** 원격 셀렉터 JSON URL (배포 시 실제 레포지토리 URL로 교체) */
const REMOTE_SELECTORS_URL = 'https://raw.githubusercontent.com/user/nugget-selectors/main/selectors.json';

/** 원격 셀렉터 캐시 유효기간 (시간) */
const REMOTE_SELECTORS_CACHE_HOURS = 24;

/** chrome.alarms 알람 이름 */
const REMOTE_SELECTORS_ALARM_NAME = 'fetch_remote_selectors';

// ============================================================
// [v1.1] API 가로채기 관련 상수 (AC-V11-1 ~ AC-V11-5)
// ============================================================

/** API 캡처 해시 최대 보관 수 (중복 저장 방지용) */
const API_CAPTURE_HASH_MAX = 100;

/** interceptor → bridge 간 CustomEvent 이름 */
const API_CAPTURE_EVENT_NAME = '__nugget_api_capture__';

/** Content Script의 SAVE_ENTRY 발송 전 중복 방지 대기 시간 (ms) */
const SAVE_ENTRY_DEDUP_DELAY_MS = 500;

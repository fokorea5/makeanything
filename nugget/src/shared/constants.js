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

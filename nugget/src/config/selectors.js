/**
 * Nugget – AI Chat Memory: 플랫폼별 DOM 셀렉터 설정
 *
 * DESIGN.md 섹션 9.3 시그니처 사양 기준.
 *
 * 핫패치 가능: AI 사이트 DOM 변경 시 이 파일만 수정하면 됩니다 (AC-2, Pre-mortem 1).
 * 셀렉터 실패 시 SELECTOR_FAILED 메시지로 사용자에게 알림 (AC-3).
 *
 * @confidence: low — 실제 AI 사이트 DOM은 수시로 변경됩니다.
 *   배포 전 최신 DOM 구조 확인 필수.
 */

/**
 * 플랫폼별 DOM 셀렉터 설정
 * @type {SelectorsConfig}
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
    /** 대화 컨테이너 (MutationObserver 타겟) */
    conversationContainer: 'main div.flex.flex-col',
    /** 사용자 질문 요소 */
    userMessage: 'div[data-message-author-role="user"]',
    /** AI 답변 요소 */
    assistantMessage: 'div[data-message-author-role="assistant"]',
    /** 스트리밍 진행 중 표시자 */
    streamingIndicator: 'button[aria-label="Stop generating"]'
  },

  gemini: {
    /** 대화 컨테이너 (MutationObserver 타겟) */
    conversationContainer: 'chat-window',
    /** 사용자 질문 요소 */
    userMessage: 'user-query',
    /** AI 답변 요소 */
    assistantMessage: 'model-response',
    /** 스트리밍 진행 중 표시자 */
    streamingIndicator: '.loading-indicator'
  }
};

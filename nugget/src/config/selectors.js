/**
 * Nugget – AI Chat Memory: 플랫폼별 DOM 셀렉터 설정
 *
 * DESIGN.md 섹션 9.3, 14.5 기준.
 *
 * 핫패치 가능: AI 사이트 DOM 변경 시 이 파일만 수정하면 됩니다 (AC-2, Pre-mortem 1).
 * 셀렉터 실패 시 SELECTOR_FAILED 메시지로 사용자에게 알림 (AC-3).
 * [v1.1] 원격 셀렉터가 있으면 로컬보다 우선 적용 (AC-V11-8).
 *
 * @confidence: low — 실제 AI 사이트 DOM은 수시로 변경됩니다.
 *   배포 전 최신 DOM 구조 확인 필수.
 */

/**
 * 플랫폼별 DOM 셀렉터 설정 (로컬 폴백)
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

// ============================================================
// [v1.1] 원격 셀렉터 우선 적용 (AC-V11-8, DESIGN.md 섹션 14.5)
// ============================================================

/**
 * 플랫폼별 셀렉터 반환 — 원격 셀렉터 우선, 없으면 로컬 폴백
 * @param {string} platform - 'claude' | 'chatgpt' | 'gemini'
 * @returns {Promise<PlatformSelectors>}
 */
async function getSelectors(platform) {
  try {
    // chrome.storage.local에서 원격 셀렉터 캐시 로드 (AC-V11-7)
    const result = await new Promise((resolve) => {
      chrome.storage.local.get(['nugget_remote_selectors'], resolve);
    });

    const remoteCache = result.nugget_remote_selectors;

    // 원격 셀렉터가 있고 유효하면 우선 사용 (AC-V11-8)
    if (
      remoteCache &&
      remoteCache.selectors &&
      remoteCache.selectors[platform] &&
      typeof remoteCache.selectors[platform].conversationContainer === 'string'
    ) {
      return remoteCache.selectors[platform];
    }
  } catch (e) {
    // 원격 셀렉터 로드 실패 — 로컬 폴백
    console.debug('[Nugget/selectors] 원격 셀렉터 로드 실패:', e);
  }

  // 로컬 셀렉터 반환 (폴백)
  return SELECTORS[platform];
}

/**
 * Nugget – AI Chat Memory: API 브릿지 (ISOLATED world)
 *
 * DESIGN.md 섹션 13.4, 17.2 기준.
 * interceptor.js(MAIN world)가 발생시키는 CustomEvent를 수신하여
 * chrome.runtime.sendMessage로 Background에 전달한다.
 *
 * 실행 환경: ISOLATED world (기본), document_start
 * 이 파일은 이 한 가지 역할만 수행 (비판자 MINOR-1 반영).
 *
 * 통합 계약:
 *   - CustomEvent 이름: '__nugget_api_capture__' (API_CAPTURE_EVENT_NAME)
 *   - 메시지 타입: 'API_CAPTURE'
 */

(function initBridge() {
  'use strict';

  // 통합 계약: CustomEvent 이름 (constants.js의 API_CAPTURE_EVENT_NAME)
  const API_CAPTURE_EVENT_NAME = '__nugget_api_capture__';

  /**
   * CustomEvent 리스너 등록 및 API_CAPTURE 메시지 Background 전달
   * DESIGN.md 섹션 13.4
   */
  document.addEventListener(API_CAPTURE_EVENT_NAME, (e) => {
    try {
      const data = e.detail;

      // 기본 유효성 검사 (DESIGN.md 섹션 13.4)
      if (!data || !data.platform || !data.answer) return;

      // API_CAPTURE 메시지를 Background에 전달 (AC-V11-2)
      chrome.runtime.sendMessage({
        type: 'API_CAPTURE',
        payload: {
          platform: data.platform,
          question: data.question || '',
          answer: data.answer,
          sourceUrl: window.location.href
        }
      }).catch((err) => {
        // Extension 재시작 등으로 runtime이 끊긴 경우 — 조용히 실패
        console.debug('[Nugget/bridge] sendMessage 실패:', err);
      });
    } catch (err) {
      console.debug('[Nugget/bridge] CustomEvent 처리 오류:', err);
    }
  });

  console.debug('[Nugget/bridge] CustomEvent 리스너 등록 완료');

})();

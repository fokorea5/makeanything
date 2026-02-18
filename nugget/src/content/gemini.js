/**
 * Nugget – AI Chat Memory: Gemini Content Script
 *
 * DESIGN.md 섹션 6.1, 9.4 기준.
 * gemini.google.com에서 대화를 감지하고 저장합니다.
 *
 * 주입 순서 (manifest.json):
 *   1. src/shared/types.js
 *   2. src/config/selectors.js   → SELECTORS 전역 변수
 *   3. src/content/gemini.js     (이 파일)
 *
 * @confidence: low — gemini.google.com DOM 구조는 수시로 변경됩니다.
 *   Gemini는 Shadow DOM 또는 Angular 기반으로 커스텀 엘리먼트를 사용합니다.
 *   셀렉터 작동 여부를 실제 사이트에서 확인하세요.
 */

(function () {
  'use strict';

  const PLATFORM = 'gemini'; // PLATFORM_GEMINI
  const DEBOUNCE_MS = 1000;  // STREAMING_DEBOUNCE_MS

  const processedElements = new WeakSet();

  // ============================================================
  // 토스트 (AC-19)
  // ============================================================

  /**
   * 토스트 DOM 주입 및 표시 (AC-19)
   * @param {string} message
   */
  function showToast(message) {
    const existing = document.getElementById('nugget-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'nugget-toast';
    toast.textContent = message;
    Object.assign(toast.style, {
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      background: 'rgba(30, 30, 30, 0.92)',
      color: '#fff',
      padding: '10px 18px',
      borderRadius: '8px',
      fontSize: '14px',
      fontFamily: 'system-ui, sans-serif',
      zIndex: '2147483647',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      opacity: '0',
      transition: 'opacity 0.25s ease',
      pointerEvents: 'none',
      maxWidth: '320px',
      wordBreak: 'break-word'
    });

    document.body.appendChild(toast);
    requestAnimationFrame(() => { toast.style.opacity = '1'; });

    const TOAST_MS = 1800; // TOAST_DURATION_MS
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, TOAST_MS);
  }

  // ============================================================
  // 질문+답변 추출
  // ============================================================

  /**
   * 질문+답변 쌍 추출
   * Gemini는 커스텀 엘리먼트(user-query, model-response)를 사용합니다.
   * @returns {{ question: string, answer: string, answerElement: Element } | null}
   */
  function extractQAPair() {
    try {
      const sel = SELECTORS[PLATFORM];

      const userMsgs = document.querySelectorAll(sel.userMessage);
      const assistantMsgs = document.querySelectorAll(sel.assistantMessage);

      if (userMsgs.length === 0 || assistantMsgs.length === 0) return null;

      const lastUser = userMsgs[userMsgs.length - 1];
      const lastAssistant = assistantMsgs[assistantMsgs.length - 1];

      // Gemini 커스텀 엘리먼트는 innerText가 없을 수 있음 — textContent 폴백
      const question = (lastUser.innerText || lastUser.textContent || '').trim();
      const answer = (lastAssistant.innerText || lastAssistant.textContent || '').trim();

      if (!question || !answer) return null;

      return { question, answer, answerElement: lastAssistant };
    } catch (err) {
      console.error('[Nugget/gemini] extractQAPair 오류:', err);
      return null;
    }
  }

  // ============================================================
  // 스트리밍 완료 감지
  // ============================================================

  let debounceTimer = null;

  function onMutation() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      // 로딩 인디케이터가 있으면 스트리밍 중
      try {
        const sel = SELECTORS[PLATFORM];
        const loading = document.querySelector(sel.streamingIndicator);
        if (loading) return;
      } catch (e) {
        // streamingIndicator 셀렉터 실패 — 계속 진행
      }

      const pair = extractQAPair();
      if (!pair) return;

      const { question, answer, answerElement } = pair;

      if (processedElements.has(answerElement)) return;
      // 최소 10자 (AC-1: 짧은 답변도 저장)
      if (answer.length < 10) return;

      processedElements.add(answerElement);

      try {
        const response = await chrome.runtime.sendMessage({
          type: 'SAVE_ENTRY',
          payload: {
            question,
            answer,
            platform: PLATFORM,
            sourceUrl: window.location.href
          }
        });

        // toastEnabled 확인 후 토스트 표시 (AC-19)
        if (response && response.success && response.toastEnabled !== false) {
          showToast('💾 Nugget이 저장했어요');
        }
      } catch (err) {
        console.debug('[Nugget/gemini] sendMessage 실패:', err);
      }
    }, DEBOUNCE_MS);
  }

  // ============================================================
  // SHOW_TOAST 메시지 수신
  // ============================================================

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message && message.type === 'SHOW_TOAST' && message.payload) {
      showToast(message.payload.message);
    }
  });

  // ============================================================
  // Content Script 초기화
  // ============================================================

  /**
   * Content Script 초기화
   * @param {string} platform
   */
  function initContentScript(platform) {
    let sel;
    try {
      sel = SELECTORS[platform];
      if (!sel || !sel.conversationContainer) {
        throw new Error(`셀렉터 없음: ${platform}`);
      }
    } catch (err) {
      chrome.runtime.sendMessage({
        type: 'SELECTOR_FAILED',
        payload: { platform, selector: 'SELECTORS', error: err.message }
      }).catch(() => {});
      return;
    }

    let attempts = 0;
    const MAX_ATTEMPTS = 20;
    const RETRY_MS = 500;

    function tryAttachObserver() {
      // Gemini는 Angular 기반으로 body에 전역 관찰
      const target = document.body;
      if (!target) {
        if (attempts++ < MAX_ATTEMPTS) {
          setTimeout(tryAttachObserver, RETRY_MS);
        } else {
          chrome.runtime.sendMessage({
            type: 'SELECTOR_FAILED',
            payload: { platform, selector: sel.conversationContainer, error: 'document.body 없음' }
          }).catch(() => {});
        }
        return;
      }

      const observer = new MutationObserver(onMutation);
      observer.observe(target, {
        childList: true,
        subtree: true,
        characterData: true
      });

      console.debug('[Nugget/gemini] MutationObserver 등록 완료');
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', tryAttachObserver, { once: true });
    } else {
      tryAttachObserver();
    }
  }

  initContentScript(PLATFORM);

})();

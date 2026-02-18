/**
 * Nugget – AI Chat Memory: Claude.ai Content Script
 *
 * DESIGN.md 섹션 6.1, 9.4 기준.
 * MutationObserver로 스트리밍 완료를 감지하고 질문+답변을 추출하여 저장합니다.
 * [v1.1] DOM 셀렉터 폴백 전용 (API 캡처가 메인 경로, AC-V11-2).
 * [v1.1] SAVE_ENTRY 발송 전 500ms 지연 추가 (API_CAPTURE 중복 방지, AC-V11-4a).
 *
 * 주입 순서 (manifest.json):
 *   1. src/shared/types.js
 *   2. src/config/selectors.js   → SELECTORS 전역 변수
 *   3. src/content/claude.js     (이 파일)
 *
 * @confidence: low — claude.ai DOM 구조는 수시로 변경됩니다.
 */

(function () {
  'use strict';

  const PLATFORM = 'claude'; // PLATFORM_CLAUDE
  const DEBOUNCE_MS = 1000;  // STREAMING_DEBOUNCE_MS
  const SAVE_ENTRY_DEDUP_DELAY_MS = 500; // [v1.1] API 캡처 중복 방지 대기 (AC-V11-4a)

  // [v1.1] i18n 초기화 — 토스트 메시지 다국어 지원 (AC-V11-14)
  if (typeof initI18n === 'function') initI18n();

  // 이미 처리한 답변 DOM 요소를 추적 (같은 답변 중복 저장 방지)
  const processedElements = new WeakSet();

  // ============================================================
  // 토스트 (AC-19)
  // ============================================================

  /**
   * 토스트 DOM 주입 및 표시 (AC-19)
   * 우측 하단, 1.5~2초 표시, 페이드 애니메이션
   * @param {string} message
   */
  function showToast(message) {
    // 기존 토스트 제거
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

    // 페이드 인
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
    });

    // 1800ms 후 페이드 아웃
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
   * @returns {{ question: string, answer: string } | null}
   */
  function extractQAPair() {
    try {
      const sel = SELECTORS[PLATFORM];

      // 사용자 메시지 전체 목록 (마지막 = 최신 질문)
      const userMsgs = document.querySelectorAll(sel.userMessage);
      // AI 답변 전체 목록 (마지막 = 최신 답변)
      const assistantMsgs = document.querySelectorAll(sel.assistantMessage);

      if (userMsgs.length === 0 || assistantMsgs.length === 0) return null;

      const lastUser = userMsgs[userMsgs.length - 1];
      const lastAssistant = assistantMsgs[assistantMsgs.length - 1];

      const question = lastUser.innerText.trim();
      const answer = lastAssistant.innerText.trim();

      if (!question || !answer) return null;

      return { question, answer, answerElement: lastAssistant };
    } catch (err) {
      console.error('[Nugget/claude] extractQAPair 오류:', err);
      return null;
    }
  }

  // ============================================================
  // 스트리밍 완료 감지 + 저장
  // ============================================================

  let debounceTimer = null;

  /**
   * 스트리밍 완료 감지 (debounce)
   * DOM 변화가 멈춘 후 DEBOUNCE_MS만큼 기다려 스트리밍 완료로 판단
   */
  function onMutation() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      // 아직 스트리밍 중이면 스킵
      try {
        const sel = SELECTORS[PLATFORM];
        const streaming = document.querySelector(sel.streamingIndicator);
        if (streaming) return; // 스트리밍 진행 중
      } catch (e) {
        // streamingIndicator 셀렉터 실패 — 계속 진행 (보수적으로 저장 시도)
      }

      const pair = extractQAPair();
      if (!pair) return;

      const { question, answer, answerElement } = pair;

      // 이미 처리한 요소면 스킵
      if (processedElements.has(answerElement)) return;

      // 너무 짧은 답변은 스트리밍 중일 가능성 — 최소 10자 (AC-1: 짧은 답변도 저장)
      if (answer.length < 10) return;

      // 처리 완료 마킹
      processedElements.add(answerElement);

      // [v1.1] 500ms 추가 지연: API_CAPTURE가 먼저 Background에 도달할 여유 (AC-V11-4a)
      // 총 지연: debounce 1초(스트리밍 완료) + 500ms(중복 방지 대기) = 1.5초
      await new Promise(resolve => setTimeout(resolve, SAVE_ENTRY_DEDUP_DELAY_MS));

      // Background로 전송
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
        // [v1.1] API 캡처 중복으로 무시된 경우(success:false) 토스트 표시 안 함
        if (response && response.success && response.toastEnabled !== false) {
          showToast('💾 ' + (typeof t === 'function' ? t('toast_saved') : 'Nugget이 저장했어요'));
        }
        // 실패 시 조용히 무시 (사용자 경험 방해 방지)
      } catch (err) {
        // Extension 재시작 등으로 runtime이 끊긴 경우
        console.debug('[Nugget/claude] sendMessage 실패:', err);
      }
    }, DEBOUNCE_MS);
  }

  // ============================================================
  // SHOW_TOAST 메시지 수신 (단축키 토스트 등)
  // ============================================================

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message && message.type === 'SHOW_TOAST' && message.payload) {
      showToast(message.payload.message);
    }
    // sendResponse 불필요 — 단방향
  });

  // ============================================================
  // Content Script 초기화
  // ============================================================

  /**
   * Content Script 초기화 — MutationObserver 설정 및 대화 감지 시작
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
      // @risk: 없음 — 단순 셀렉터 로드 실패
      chrome.runtime.sendMessage({
        type: 'SELECTOR_FAILED',
        payload: { platform, selector: 'SELECTORS', error: err.message }
      }).catch(() => {});
      return;
    }

    /**
     * 대화 컨테이너를 찾아 MutationObserver 등록
     * SPA이므로 컨테이너가 나중에 렌더링될 수 있어 재시도
     */
    let attempts = 0;
    const MAX_ATTEMPTS = 20;
    const RETRY_MS = 500;

    function tryAttachObserver() {
      // body 전체 관찰 (SPA에서 컨테이너가 동적으로 교체되므로)
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

      console.debug('[Nugget/claude] MutationObserver 등록 완료');
    }

    // DOM 준비 확인 후 시작
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', tryAttachObserver, { once: true });
    } else {
      tryAttachObserver();
    }
  }

  // 초기화 실행
  initContentScript(PLATFORM);

})();

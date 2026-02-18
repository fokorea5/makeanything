/**
 * Nugget – AI Chat Memory: ExtensionPay 결제 완료 감지 Content Script
 *
 * DESIGN.md 섹션 7.3 기준.
 * extensionpay.com에 주입되어 결제 완료(onPaid) 콜백을 수신합니다.
 *
 * 주입 순서 (manifest.json, run_at: "document_start"):
 *   1. src/lib/ExtPay.js   → ExtPay 전역 함수
 *   2. src/content/extpay-content.js (이 파일)
 *
 * 주의: MV3에서 onPaid 콜백을 받으려면 content_scripts 설정이 필수입니다.
 *   (oracle_report.md 섹션 4 참조)
 */

(function () {
  'use strict';

  // @risk: 결제
  // exception_policy: fail-open — 콜백 실패해도 사용자는 결제 완료됨.
  //   Background에 알림 실패 시 다음 GET_PRO_STATUS 호출 시 정상 반영됨.
  try {
    // MV3 콜백 내 재선언 (DESIGN.md 섹션 7.2)
    const extpay = ExtPay('nugget-ai-chat-memory');

    extpay.onPaid.addListener(user => {
      // @risk: 결제 — 결제 완료 처리
      // exception_policy: fail-open
      try {
        chrome.runtime.sendMessage({
          type: 'PRO_STATUS_CHANGED',
          payload: { paid: true }
        }).catch(err => {
          // Extension 재시작 등으로 runtime이 끊긴 경우 — 무시
          // 다음 사용 시 checkProStatus()로 최신 상태 반영됨
          console.warn('[Nugget/extpay] PRO_STATUS_CHANGED 전송 실패:', err);
        });
      } catch (msgErr) {
        console.error('[Nugget/extpay] sendMessage 오류:', msgErr);
      }
    });
  } catch (err) {
    // ExtPay 초기화 실패 (라이브러리 로드 실패 등)
    console.error('[Nugget/extpay] ExtPay 초기화 실패:', err);
  }

})();

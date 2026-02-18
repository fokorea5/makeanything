/**
 * ExtPay.js — ExtensionPay 라이브러리
 *
 * 이 파일은 실제 배포 시 npm extpay v3.1.2에서 복사합니다.
 *
 * 복사 방법:
 *   1. npm install extpay@3.1.2
 *   2. node_modules/extpay/dist/ExtPay.js 내용을 이 파일에 붙여넣기
 *
 * 또는:
 *   npx --yes extpay@3.1.2   (CLI가 있는 경우)
 *
 * 참조:
 *   - GitHub: https://github.com/Glench/ExtPay
 *   - npm: https://www.npmjs.com/package/extpay
 *   - oracle_report.md 섹션 2 (번들러 미사용 시 직접 파일 복사)
 *
 * 주의:
 *   - 번들러 없이 직접 파일 복사 방식 사용 (DESIGN.md 섹션 11 제약 6)
 *   - dist/ExtPay.js (일반 스크립트 버전)을 사용할 것
 *   - dist/ExtPay.module.js (ESM) 사용 금지 — Service Worker importScripts 미지원
 *
 * @placeholder: 이 파일은 빈 플레이스홀더입니다. 배포 전 실제 라이브러리로 교체 필수.
 */

// 개발/테스트용 stub — 실제 배포 시 npm extpay@3.1.2의 dist/ExtPay.js로 교체
// @confidence: low — 이 stub은 실제 결제 기능을 하지 않습니다.
if (typeof ExtPay === 'undefined') {
  function ExtPay(extensionId) {
    console.warn('[Nugget] ExtPay stub 사용 중. 배포 전 실제 라이브러리로 교체하세요.');
    return {
      startBackground: function () {
        console.warn('[ExtPay stub] startBackground() 호출됨');
      },
      getUser: function () {
        return Promise.reject(new Error('[ExtPay stub] getUser() — 실제 라이브러리가 아닙니다'));
      },
      openPaymentPage: function (planNickname) {
        console.warn('[ExtPay stub] openPaymentPage() 호출됨:', planNickname);
      },
      openLoginPage: function () {
        console.warn('[ExtPay stub] openLoginPage() 호출됨');
      },
      onPaid: {
        addListener: function (callback) {
          console.warn('[ExtPay stub] onPaid.addListener() 등록됨 (실제로 호출되지 않음)');
        }
      },
      onTrialStarted: {
        addListener: function (callback) {
          console.warn('[ExtPay stub] onTrialStarted.addListener() 등록됨');
        }
      }
    };
  }
}

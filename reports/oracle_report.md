# ExtensionPay 조사 보고서

조사일: 2026-02-18
조사관: 오라클 (외부 정보 조사관)

---

## 1. 공식 사이트 및 문서 URL

| 항목 | URL |
|------|-----|
| 공식 사이트 | https://extensionpay.com |
| GitHub (ExtPay 라이브러리) | https://github.com/Glench/ExtPay |
| npm 패키지 | https://www.npmjs.com/package/extpay |
| README (공식) | https://github.com/Glench/ExtPay/blob/main/README.md |
| Stripe 연동 가이드 | https://extensionpay.com/articles/add-stripe-payments-to-chrome-extensions |
| 유료 라이선스 추가 가이드 | https://extensionpay.com/articles/add-paid-licenses-to-chrome-extensions |
| 무료 체험 추가 가이드 | https://extensionpay.com/articles/how-to-add-free-trials-chrome-extension |
| 135개 통화 지원 안내 | https://extensionpay.com/articles/charge-currency-chrome-extensions |

---

## 2. npm 패키지 설치 방법 및 최신 버전

### 설치 명령어

```bash
# 안정 버전 (권장)
npm install extpay --save

# 베타 버전 (최신 기능 포함)
npm install extpay@4.0.0-beta.6
```

### 버전 현황

| 버전 | 상태 |
|------|------|
| 4.0.0-beta.6 | 최신 베타 (다중 요금제 지원 등 신기능) |
| 3.1.2 | 최신 안정 버전 (권장) |
| 3.1.1 / 3.1.0 | 안정 버전 |
| 3.0.7 이하 | 구버전 |

### 번들러 미사용 시 (직접 파일 복사)

```
dist/ExtPay.js        — 일반 스크립트
dist/ExtPay.module.js — ESM (ES Module)
dist/ExtPay.common.js — CommonJS
```

---

## 3. API 인증 방식

**API 키 방식이 아님** — Extension ID(확장 프로그램 ID) 기반 인증

### 등록 절차

1. https://extensionpay.com 에서 계정 생성
2. 대시보드에서 확장 프로그램 등록
3. 등록 시 부여받은 **Extension ID**를 코드에서 사용

### 초기화

```js
// Extension ID를 문자열 인자로 전달
const extpay = ExtPay('your-extension-id');
```

- 별도의 API 키 없음
- Extension ID가 서버와 통신하는 유일한 인증 수단
- 클라이언트 사이드 전용 — 서버 코드 불필요

---

## 4. Manifest V3 지원 여부

**지원함** — MV3 완전 호환

### manifest.json 필수 설정

```json
{
  "manifest_version": 3,
  "permissions": ["storage"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://extensionpay.com/*"],
      "js": ["ExtPay.js"],
      "run_at": "document_start"
    }
  ]
}
```

> **주의사항:**
> - `content_scripts` 설정은 `onPaid`, `onTrialStarted` 콜백을 사용할 때만 필요
> - Firefox의 경우 `"permissions"` 배열에 `"https://extensionpay.com/*"` 추가 필요
> - `content_security_policy`가 있으면 `connect-src https://extensionpay.com` 추가 필요

### MV3 Service Worker 주의사항

```js
// background.js (service_worker)
importScripts('ExtPay.js')

var extpay = ExtPay('your-extension-id');
extpay.startBackground();

// !! 중요: MV3 서비스 워커는 콜백 내부에서 extpay가 undefined가 됨
// 콜백 내에서 반드시 재선언해야 함 (startBackground()는 다시 호출하지 말 것)
chrome.storage.local.get('someKey', function() {
  var extpay = ExtPay('your-extension-id'); // 재선언 필요
  extpay.getUser().then(user => { /* ... */ });
});
```

---

## 5. 결제 연동 코드 예시

### 5-1. 기본 구조 (background.js)

```js
importScripts('ExtPay.js')

const extpay = ExtPay('your-extension-id');
extpay.startBackground();
```

### 5-2. 구독 상태 확인 (getUser)

```js
// 비동기 방식 (async/await)
const user = await extpay.getUser();
if (user.paid) {
  // 유료 기능 활성화
  enablePremiumFeatures();
} else {
  // 무료 사용자 처리
  showUpgradePrompt();
}

// then/catch 방식
extpay.getUser()
  .then(user => {
    if (user.paid) { enablePremiumFeatures(); }
  })
  .catch(err => {
    console.error('결제 상태 확인 실패:', err);
  });
```

### 5-3. User 객체 필드 전체 목록

```js
const user = await extpay.getUser();

user.paid               // boolean — 현재 유료 구독 활성 여부
user.paidAt             // Date|null — 최초 결제 시각
user.email              // string|null — 사용자 이메일
user.installedAt        // Date — 확장 프로그램 설치 시각
user.trialStartedAt     // Date|null — 무료 체험 시작 시각
user.plan               // object|null — 현재 구독 요금제 정보
user.subscriptionStatus // string — 'active' | 'past_due' | 'canceled'
user.subscriptionCancelAt // Date|null — 구독 취소 예정 시각
```

### 5-4. 결제 페이지 열기 (구독 생성)

```js
// 기본 — 요금제 선택 화면 열기
extpay.openPaymentPage();

// 특정 요금제 바로 열기 (planNickname은 대시보드에서 설정)
extpay.openPaymentPage('monthly');
extpay.openPaymentPage('yearly');
```

### 5-5. 결제 완료 콜백 (onPaid)

```js
// manifest.json의 content_scripts 설정 필요 (4번 항목 참고)
extpay.onPaid.addListener(user => {
  console.log('결제 완료:', user.email);
  enablePremiumFeatures();
});
// 최초 결제 후 + 다른 브라우저/프로필에서 로그인할 때도 호출됨
```

### 5-6. 다중 요금제 조회 (getPlans)

```js
const plans = await extpay.getPlans();
// 각 plan에는 unitAmountCents, currency, interval, intervalCount 포함
plans.forEach(plan => {
  console.log(`${plan.interval}ly: ${plan.unitAmountCents / 100} ${plan.currency}`);
});
```

### 5-7. 무료 체험 (Trial)

```js
// 무료 체험 페이지 열기
extpay.openTrialPage('7-day');  // '7-day', '14-day' 등 직접 표시할 텍스트

// 체험 시작 콜백 (content_scripts 설정 필요)
extpay.onTrialStarted.addListener(user => {
  console.log('체험 시작:', user.trialStartedAt);
});
```

### 5-8. 기존 유저 로그인 (다른 기기에서 복원)

```js
extpay.openLoginPage();  // 이메일로 매직링크 발송 → 유료 상태 복원
```

### 5-9. 실제 팝업 통합 예시 (popup.js)

```js
// popup.js
const extpay = ExtPay('your-extension-id');

extpay.getUser().then(user => {
  if (user.paid) {
    document.getElementById('premium-section').style.display = 'block';
    document.getElementById('upgrade-btn').style.display = 'none';
  } else {
    document.getElementById('upgrade-btn').addEventListener('click', () => {
      extpay.openPaymentPage();
    });
  }
}).catch(err => {
  // 네트워크 오류 등 예외 처리
  console.error(err);
});
```

---

## 6. 가격 정책 (ExtensionPay 자체 수수료)

| 항목 | 내용 |
|------|------|
| 가입비 | 무료 |
| 월정액 | 무료 |
| 거래 수수료 | **5%** (거래당) |
| Stripe 수수료 | 별도 (~2.9% + $0.30 / 건) |
| 대량 거래 할인 | 있음 — 직접 문의 필요 (flat monthly rate 협상 가능) |

### 실제 비용 계산 예시

```
사용자가 $10/월 구독 시:
  - ExtensionPay 수수료: $0.50 (5%)
  - Stripe 수수료: ~$0.59 (2.9% + $0.30)
  - 개발자 실수령: ~$8.91
```

> **참고:** Google Chrome Web Store의 구 결제 시스템도 5% 수수료를 부과했음.
> Paddle, Lemon Squeezy는 5% + $0.50/건으로 비교적 비슷하지만 세금 처리 포함.

---

## 7. Rate Limit 및 제한사항

### Rate Limit

공식 문서에 명시된 Rate Limit 없음. 단, 다음 사항 유의:

- `getUser()` 호출 시 매번 서버 요청 발생 — **과도한 폴링 자제 권장**
- 네트워크 장애에 대비한 `.catch()` 예외 처리 필수

### 기술적 제한사항

| 제한 | 내용 |
|------|------|
| 서버 의존성 | extensionpay.com 서버 다운 시 결제 확인 불가 |
| 오프라인 동작 | 오프라인 상태에서 `getUser()` 실패 가능 |
| MV3 서비스 워커 | 콜백 내에서 `extpay` 재선언 필수 (컨텍스트 손실) |
| Firefox 권한 | `"https://extensionpay.com/*"` 명시 필요 |
| CSP 설정 | `connect-src https://extensionpay.com` 추가 필요 |
| 테스트 모드 | 개발 중 결제 테이지 진입 시 계정 비밀번호 입력 필요 |

---

## 8. 알려진 이슈 및 대안

### 알려진 이슈

| 이슈 | 내용 |
|------|------|
| 세금 처리 미지원 | VAT/GST 등 세금 신고를 개발자가 직접 해야 함 |
| 단일 서비스 의존 | ExtensionPay 서비스 장애 시 결제 확인 전면 차단 |
| 영세 서비스 리스크 | 1인 운영 소규모 서비스 — 장기 지속 가능성 불확실 |
| 수수료 이중 부담 | ExtensionPay 5% + Stripe 수수료 별도 |
| 공식 문서 빈약 | Rate Limit, SLA, 상세 에러 코드 문서 없음 |

### 주요 대안 비교

| 서비스 | 수수료 | 세금 처리 | 서버 불필요 | 확장 전용 |
|--------|--------|-----------|------------|-----------|
| **ExtensionPay** | 5% + Stripe | 직접 처리 | O | O |
| **Paddle** | 5% + $0.50/건 | 자동 (MoR) | X | X |
| **Lemon Squeezy** | 5% + $0.50/건 | 자동 (MoR) | X | X |
| **Payzzle** | 별도 | Paddle/LS 연동 | O | O |
| **Polar** | 낮음 | 자동 (MoR) | X | X |
| **직접 Stripe** | 2.9% + $0.30 | 직접 처리 | X (백엔드 필요) | X |

### 결론

- **빠르게 시작하고, 백엔드 없이 구현**하려면 ExtensionPay가 최선
- **세금/VAT 자동 처리가 필요하면** Paddle 또는 Lemon Squeezy (+ Payzzle로 백엔드 제거)
- **장기적 안정성이 중요하면** 직접 Stripe 백엔드 구현 고려

---

## 참고 출처

- [ExtensionPay 공식 사이트](https://extensionpay.com)
- [GitHub — Glench/ExtPay](https://github.com/Glench/ExtPay)
- [npm — extpay](https://www.npmjs.com/package/extpay)
- [Indie Hackers — ExtensionPay 수수료 언급](https://www.indiehackers.com/product/extensionpay)
- [ExtensionPay Manifest V3 지원 발표 (Mozilla Discourse)](https://discourse.mozilla.org/t/extensionpay-now-supports-manifest-v3/85393)
- [Extension Radar — 2025 크롬 확장 수익화 가이드](https://www.extensionradar.com/blog/how-to-monetize-chrome-extension)

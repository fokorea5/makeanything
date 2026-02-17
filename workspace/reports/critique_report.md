# Critique Report — .plan.md (Polymarket Reaper Bot v1.1)

**비판자**: critique agent
**검토 대상**: `/workspace/projects/polymarket-reaper/.plan.md`
**검토일**: 2026-02-17

---

## 1. 사용자 요구 vs AC 매핑 검토

### 1-A. 6전략 반영 여부

| # | 사용자 원문 전략 | AC 매핑 | 판정 |
|---|---|---|---|
| 1 | 모호성 스코어링 | AC-07 | OK |
| 2 | 오라클 공포 프리미엄 | AC-08 | OK |
| 3 | 군중 반대 지표 (Z-score > 2, 주말 드리프트) | AC-11 | **결함** |
| 4 | 연관 시장 비효율 (논리적 불일치 + Complete Set) | AC-12 (Stage 2) + AC-18 (Reactor Omega) | OK (분리 배치) |
| 5 | 유동성 진공 사냥 | AC-15 | OK |
| 6 | 메타 봇 스코어링 | AC-20~22 (Meta Brain) | OK |

### 1-B. 베팅 룰 반영 여부

| 룰 | AC | 판정 |
|---|---|---|
| Fractional Kelly 0.4 | AC-23 | OK |
| 단일 15% | AC-24 | OK |
| 전체 60% | AC-25 | OK |
| 일일 손실 8% 서킷 | AC-26 | OK |

### 1-C. 기타 요구사항 반영 여부

| 요구사항 | AC | 판정 |
|---|---|---|
| 유지비용 고려 | **해당 AC 없음** | **결함** |
| 거래빈도 조절 | AC-28~30 | OK |
| 실행 비용 최소화 | AC-31~32 (postOnly/FOK) | 부분 반영 |
| 병목 돌파 (Complete Set vs 메타 충돌) | 듀얼 리액터 분리 | OK (구조적 해결) |
| 알파 증폭 52~55% 파생 지표 | AC-09, AC-13, AC-16 (보조지표) | OK |

---

## 2. 결함 목록

### CRITICAL 결함

**CRITICAL-01: "주말 드리프트 감지" AC 누락**

사용자 원문 전략 3번: "군중 반대 지표 (Z-score > 2, **주말 드리프트 감지**)".
AC-11은 Z-score 계산만 명시하고, "주말 드리프트 감지"에 대한 AC가 전혀 없다.
주말 드리프트는 주중 대비 주말 가격 변동의 비정상적 패턴을 포착하는 별도 로직이며,
단순 Z-score 계산과는 별개의 구현이 필요하다.
**조치**: AC-11에 주말 드리프트 감지 로직을 추가하거나, 별도 AC를 신설해야 한다.

---

**CRITICAL-02: "유지비용 고려" AC 전면 누락**

사용자 원문: "유지비용 고려 / 거래빈도 조절 기능 필수".
거래빈도 조절은 AC-28~30으로 반영되었으나, "유지비용 고려"에 해당하는 AC가 없다.
유지비용(holding cost)이란 포지션을 유지하는 동안 발생하는 기회비용,
자금 동결 비용, 시장 만기까지의 시간가치 등을 의미한다.
베팅 사이즈 결정(AC-23 Kelly) 시 유지비용을 반영하지 않으면,
장기 포지션의 실질 수익률이 과대 평가된다.
**조치**: Kelly Sizer(AC-23) 또는 Portfolio Tracker(AC-34)에 유지비용 반영 로직을 추가하는 AC가 필요하다.

---

**CRITICAL-03: AC-12와 AC-18 — Correlated Markets와 Complete Set의 역할 경계 모호**

AC-12 (Stage 2, Reactor Alpha): "같은 event_id 마켓 가격 합 != 1.0 (Complete Set) + implied conditional 비교"
AC-18 (Reactor Omega): "WS로 같은 event_id 마켓들의 가격 합 모니터링. 합 > 1.03 또는 < 0.97이면 차익 기회"

두 AC 모두 "같은 event_id 마켓의 가격 합"을 감시한다. 차이점은:
- AC-12: 합 != 1.0 (임계값 미명시) + "implied conditional 비교" (정의 미명시)
- AC-18: 합 > 1.03 또는 < 0.97 (명확한 임계값)

**문제점**:
1. AC-12의 "!= 1.0" 임계값이 없다. 0.001 차이도 트리거하는가? AC-18과 동일한 0.03을 쓰는가? 다르다면 기준은?
2. AC-12의 "implied conditional 비교"가 정의되지 않았다. 개발자가 "알아서" 판단해야 한다.
3. AC-12가 이상을 감지하면 Hit List에 추가되고(AC-14), AC-18도 같은 이상을 감지하면 즉시 FOK 실행한다(AC-19). 동일 마켓에 대해 Patient Executor(GTC)와 Sniper Executor(FOK)가 동시에 주문을 넣는 충돌 시나리오가 존재한다.
**조치**: (a) AC-12의 Complete Set 임계값과 "implied conditional" 정의를 명시, (b) 동일 마켓에 Alpha와 Omega가 동시에 시그널을 발생시킬 때의 우선순위/중복 방지 규칙을 AC로 추가.

---

**CRITICAL-04: 동일 마켓 중복 주문 방지 AC 부재**

CRITICAL-03과 연결. Reactor Alpha와 Reactor Omega가 **동시에** 같은 마켓에 시그널을 보낼 수 있다.
또한 Meta Brain의 Golden Cross(AC-21)가 추가 증폭까지 할 수 있다.
그러나 "동일 마켓에 이미 포지션이 있을 때 추가 주문을 어떻게 처리하는가?"에 대한 AC가 없다.
- 기존 포지션이 있으면 스킵? 증량? 반대 방향이면 청산?
- Patient Executor의 GTC 미체결 주문이 있을 때 Sniper가 FOK를 보내면?
**조치**: 중복 주문 방지 / 포지션 중첩 처리 로직에 대한 AC 신설 필요.

---

### MINOR 결함

**MINOR-01: AC-07 모호성 키워드 사전 미정의**

AC-07: "모호 키워드 TF-IDF 스코어링"이라 했지만, 모호 키워드 사전(lexicon)을 어디서 가져오는지 명시가 없다.
하드코딩인가? 외부 파일인가? 업데이트 가능한가?
**제안**: "모호 키워드 사전은 config 또는 별도 JSON 파일로 관리" 정도의 명시 추가.

---

**MINOR-02: AC-08 "분쟁 키워드" 정의 부재**

AC-08: "분쟁 키워드" 감지라 했지만, 어떤 키워드가 분쟁을 의미하는지 정의가 없다.
Polymarket의 UMA 오라클 분쟁 이력을 API로 조회할 수 있는지,
아니면 텍스트 분석으로 "dispute", "challenge" 등의 키워드를 찾는 것인지 불명확.
또한 "분쟁 이력 시장 타겟팅"이라는 원문을 보면 실제 분쟁 이력 데이터가 필요한데,
Polymarket/UMA API에서 분쟁 이력을 제공하는지 기술적 검증이 필요하다.
**제안**: 분쟁 키워드 소스(API vs 텍스트 매칭)와 키워드 목록 관리 방식을 명시.

---

**MINOR-03: AC-13 "/holders API" 존재 여부 미확인**

AC-13: "/holders API로 보유자 쏠림 80%+" — Polymarket의 공개 API에 /holders 엔드포인트가 있는지 확인이 필요하다. Gamma API 문서에서 이 엔드포인트가 확인되지 않으면 이 AC는 실현 불가능해진다.
**제안**: API 엔드포인트 존재 확인 후, 없다면 대체 방안(예: 온체인 데이터 조회 또는 AC 삭제)을 명시.

---

**MINOR-04: AC-16 "Volume-Price Divergence" 괴리 감지 기준 미명시**

AC-16: "거래량 vs 가격 변동 괴리 감지"라 했지만, 어떤 수치 기준으로 "괴리"를 판정하는지 없다.
다른 AC들은 임계값이 명확(Z > 2.0, spread > 0.05, depth > 3:1 등)한데,
AC-16만 정성적 표현에 머물러 있다.
**제안**: "거래량 N% 증가인데 가격 변동 M% 미만" 같은 수치 기준 추가.

---

**MINOR-05: AC-22 "전략별 가중치" 초기값/조정 메커니즘 미명시**

AC-22: "전략별 가중치 적용 후 가중 평균 confidence 산출" — 6개 전략 + 3개 보조지표의 초기 가중치를 어디서 정하는지, 런타임 조정이 가능한지 명시가 없다.
**제안**: 초기 가중치를 config에서 관리하고, 향후 성과 기반 조정 가능 여부를 명시.

---

**MINOR-06: AC-27과 AC-29 Drawdown 임계값 불일치/혼재**

AC-27 (Risk Sentinel Layer 5): DD >5% x0.5, >10% x0.25, >15% 중단
AC-29 (Frequency Governor AUTO): DD <3% TURBO, 3~6% NORMAL, >6% STEALTH

두 모듈이 모두 Drawdown을 기준으로 행동을 변경하지만, 임계값 체계가 다르다.
DD 6%일 때: Governor는 STEALTH, Risk Sentinel은 아직 x0.5 미적용(5% < DD).
DD 5.5%일 때: Governor는 NORMAL, Risk Sentinel은 x0.5 적용.
이것이 의도된 설계인지, 서로 겹치면 어떤 것이 우선인지 명확하지 않다.
결과적으로 DD 5.5%에서 Risk Sentinel이 Kelly를 x0.5로 줄이면서 Governor는 NORMAL(일반 속도)을 유지 — 이것이 의도된 조합인지 확인 필요.
**제안**: 두 DD 임계값 체계의 상호작용을 명시하거나, 하나의 통합 DD 테이블로 정리.

---

**MINOR-07: AC-23 "Frequency Governor 배수"의 모드별 수치 미정의**

AC-23: "Fractional Kelly 0.4 x Frequency Governor 배수" — TURBO/NORMAL/STEALTH 각 모드의 배수가 얼마인지 정의가 없다.
AC-28은 4개 모드를 정의하지만 각 모드가 Kelly에 적용하는 배수(예: TURBO x1.0, NORMAL x0.7, STEALTH x0.3 등)는 어디에도 없다.
개발자가 임의로 정해야 한다.
**제안**: 각 모드의 Kelly 배수, Stage 1 주기, Stage 2 주기 등 구체적 파라미터를 명시.

---

**MINOR-08: "실행 비용 최소화" 구체적 AC 부재**

사용자 원문: "실행 비용 최소화". Patient Executor의 postOnly(AC-32)가 부분적으로 이를 반영하지만,
실행 비용 최소화를 위한 명시적 전략(예: 가스비 감시, maker rebate 활용, 최소 주문 크기 설정,
수수료 대비 기대이익 필터링)에 대한 AC가 없다.
특히 "기대 수익 - 수수료 > 0"인 경우에만 실행하는 필터가 없으면,
소액 차익거래에서 수수료가 수익을 초과하는 역전이 발생한다.
**제안**: "수수료 차감 후 기대이익 > 최소 수익 임계값" 같은 실행 비용 필터 AC 추가.

---

**MINOR-09: AC-04 WebSocket 재연결 시 상태 복구 미명시**

AC-04: "자동 재연결(지수 백오프)" — 재연결 자체는 좋지만, 재연결 후 구독 중이던 마켓 채널의 재구독, 끊어진 동안 놓친 데이터의 보정(예: REST API 폴백으로 갭 메우기)에 대한 언급이 없다.
**제안**: "재연결 후 기존 구독 자동 복구 + 단절 구간 REST API 폴백" 명시.

---

**MINOR-10: "소스 부재 분석" AC 미반영**

사용자 원문 전략 1: "주관적 키워드/**소스 부재** 분석".
AC-07은 "모호 키워드 TF-IDF 스코어링"만 있고, "소스 부재"(resolution source가 명시되지 않은 마켓)를 감지하는 로직이 별도로 없다.
소스 부재는 키워드 분석과는 다른 차원의 체크(마켓 메타데이터에서 resolution source 필드 존재 여부)이다.
**제안**: AC-07에 "resolution source 미명시 마켓 감지" 로직을 추가하거나 별도 AC 신설.

---

## 3. 듀얼 리액터 데이터 흐름 분석

```
[전체 마켓]
    │
    ├── Reactor Alpha ──┐
    │   Stage 1 (5분)   │
    │   ↓ Target List    │
    │   Stage 2 (60초)  │
    │   ↓ Hit List       │──→ Meta Brain (Signal Buffer)
    │   Stage 3 (WS)    │         │
    │   ↓ Patient Exec  │    Golden Cross?
    │                    │         │
    ├── Reactor Omega ──┤    Kelly 1.5x
    │   WS 실시간       │         │
    │   ↓ Sniper Exec   │──→ Meta Brain
    │                    │
    └───────── Risk Sentinel (5층) ← 모든 주문 통과
                    │
              Frequency Governor
```

**데이터 흐름 모순 없음** — 단, 아래 문제 존재:

1. **Meta Brain 개입 시점 불명확**: AC-21에서 Golden Cross가 발생하면 Kelly 1.5x 증폭이라 했는데, 이것이 Patient Executor 주문에 적용되는 것인지, 별도의 새 주문을 생성하는 것인지 불명확. Reactor Alpha Stage 3가 이미 Patient Executor에 시그널을 보낸 후 Meta Brain이 Golden Cross를 감지하면, 이미 발송된 GTC 주문의 사이즈를 수정하는 것인가?

2. **Reactor Omega → Meta Brain 시그널 전달 경로 모호**: AC-18~19에서 Omega는 차익 기회를 발견하면 즉시 FOK 실행(AC-19)한다. 그런데 AC-21에서 Meta Brain이 "Omega도 이상 감지"를 참조한다. Omega가 FOK를 먼저 실행하고 나서 Meta Brain에도 시그널을 보내는 것인지, Meta Brain이 먼저 판단하고 Omega의 실행을 보류하는 것인지 순서가 불명확하다. 시간 순서에 따라 Golden Cross가 의미를 잃을 수 있다(Omega가 이미 실행 완료한 후).

---

## 4. 기술적 실현 가능성

38개 AC 중 **실현 불가능한 것은 없다**. 단, 아래 항목은 주의가 필요하다:

- **AC-13 (/holders API)**: MINOR-03에서 언급. API 존재 여부 미확인. 없으면 온체인 조회 필요 → 복잡도 대폭 증가.
- **AC-08 (분쟁 이력)**: MINOR-02에서 언급. UMA 오라클 분쟁 이력 API 존재 여부에 따라 구현 난이도 변동.
- **AC-18 (Complete Set 실시간)**: 기술적으로 가능하지만, Polymarket의 WS가 모든 event_id 마켓의 가격을 실시간으로 동시에 전달하는지, 별도 구독이 필요한지에 따라 구현 복잡도가 달라진다.

---

## 5. 최종 판정

| 구분 | 건수 |
|---|---|
| CRITICAL | 4건 |
| MINOR | 10건 |

**CRITICAL 결함이 존재하므로 계획 수정이 필요합니다.**

핵심 수정 요구사항:
1. "주말 드리프트 감지" AC 추가 (CRITICAL-01)
2. "유지비용 고려" AC 추가 (CRITICAL-02)
3. AC-12와 AC-18의 역할 경계 명확화 + implied conditional 정의 (CRITICAL-03)
4. 동일 마켓 중복 주문 방지 AC 신설 (CRITICAL-04)

MINOR 결함은 설계 단계에서 해소 가능하나, 특히 MINOR-06(DD 임계값 불일치), MINOR-07(Governor 배수 미정의), MINOR-08(실행 비용 필터 부재)는 조기 해결을 권고한다.

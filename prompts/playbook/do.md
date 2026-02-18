[DO — 설계 병렬화]

프론트가 있는 프로젝트:
  설계자 + UI디자이너를 동시에 TaskCreate (병렬).
  설계자: DESIGN.md (API, DB, 구조). UI디자이너: ui_design.md (레이아웃, 색상, 동선).
  설계자 완료 → 백엔드 시작. UI디자이너 완료 → 프론트 시작.
프론트가 없는 프로젝트:
  설계자만 소환 (기존과 동일).

[DO — DESIGN↔개발 동기화 포인트]
설계자가 DESIGN.md를 완성하면, 개발자를 바로 투입하지 마세요.
다음 2단계 핸드오프를 거쳐야 합니다:

1단계: 통합 계약 선행 확인
  설계자가 DESIGN.md를 제출하면, 오케스트레이터가 직접 확인:
  - "통합 계약" 섹션이 존재하는가?
  - "시그니처 사양" 섹션이 존재하는가?
  두 섹션 모두 없으면 설계자에게 보완 요청. 있으면 2단계로.

2단계: 개발자 Task에 명시적 준수 지시
  개발자 Task description에 다음을 추가:
  "DESIGN.md의 '시그니처 사양' 섹션에 명시된 클래스명, 생성자 인자,
   public 메서드 시그니처를 반드시 따르세요.
   패턴(싱글톤/주입 등)을 임의로 변경하지 마세요.
   변경이 필요하면 FREEZE를 선언하세요."

이 동기화 포인트를 건너뛰면 CHECK에서 대량 불일치가 발생합니다.

[DO — @risk 코드 예외 처리 원칙]
개발자 Task에 다음을 포함:
  "@risk 태그가 붙은 코드에서 예외 발생 시, 예외 처리 전략을 주석으로 명시하세요.
   예: // @risk:금융거래 exception_policy: fail-closed
   예: // @risk:조회 exception_policy: retry:3, fallback:empty
   전략 없이 except: pass 또는 except: log+continue는 금지."

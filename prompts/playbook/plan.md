[PLAN — 7단계]

1. 외부 API 의존 판단
   외부 API(거래소, 결제, 소셜, 데이터 등)에 의존하는가?
   YES → 오라클 소환: API 조사 (엔드포인트, 인증, Rate Limit, 응답 형식)
         oracle_report.md 완료 후 2단계로.
   NO → 바로 2단계.

2. .plan.md 작성
   사용자 원문 그대로 포함 + AC 목록 + 전달 방식 필수.
   오라클 보고서가 있으면 "기술적 제약사항" 부록에 핵심 제약을 요약 포함.

3. 비판자 소환: .plan.md 비판 요청
   오라클 보고서가 있으면 함께 전달.
   치명적 결함 → .plan.md 수정. 경미 → 기록 후 진행.

4. 교훈 DB 검색: python memory/lessons_db.py search "[키워드]"
   이전 프로젝트에서 같은 유형의 문제가 있었는지 확인.

5. 세포 분화 (프로젝트 규모별 편성)
   간단 스크립트: 비판자 + backend + QA (3명)
   프론트만 (정적): 비판자 + UI디자이너 + frontend + QA (4명)
   API/백엔드만: 비판자 + 설계자 + backend + QA (4명)
   풀스택: 비판자 + 설계자∥UI디자이너 + backend∥frontend + QA (6명)
   auth/pay/security 포함 시: + 보안 에이전트 필수 소환 (+1명)
   패키징 필요 시: + DevOps 2단계 (+1명)

6. Pre-mortem: 실패 시나리오 3개 → reports/premortem.md

7. 모든 Task에 "참조: .plan.md" 포함.
   외부 API 의존 또는 기술적 실현 가능성 미확인이면 MVP 제안.

[전달 방식 판단]
DISCOVER에서 사용자가 지정 → .plan.md에 기록.
"알아서"인 경우 프로젝트 특성으로 판단:
  정적 파일만 → HTML 전달
  서버 필요 → 실행 스크립트
  복잡한 의존성 → 도커
  개발자 대상 → 소스코드 + README

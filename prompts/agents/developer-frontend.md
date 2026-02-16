참조: .plan.md

[범위]
허용: src/ui/, src/pages/, src/styles/ 읽기/쓰기, 터미널.
금지: .plan.md, DESIGN.md, src/api/, src/db/, src/shared/ 수정.
공유 타입은 src/shared/에서 읽기만.

[작업 순서]
DESIGN.md를 먼저 읽고 설계를 따르세요.
로딩 상태와 에러 상태 UI를 빠뜨리지 마세요.
코드 완료 후 반드시 실행해서 에러 없는지 확인.

[코드]
처음 쓰는 라이브러리, 직접 테스트하지 않은 로직에 // @confidence: low
인증, 결제, 개인정보, 파일삭제 관련 코드에 // @risk: [영역] 태그.

[보고]
코드 완료 후 .plan.md의 AC를 하나씩 직접 확인하고 보고.
모든 할당 작업 완료 후 1회. reports/frontend_report.md에 상세.

[수정]
수정 Task를 받으면 Task에 명시된 reports/ 파일을 직접 읽고 수정.

[에러]
같은 에러 메시지 3회 반복 → SOS. backend과 동일.

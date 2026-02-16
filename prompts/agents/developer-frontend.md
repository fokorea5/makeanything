참조: .plan.md

[범위]
허용: src/ui/, src/pages/, src/styles/ 읽기/쓰기, 터미널.
금지: .plan.md, DESIGN.md, src/api/, src/db/, src/shared/ 수정.
공유 타입은 src/shared/에서 읽기만.

[코드]
@confidence, @risk 태그 남기기.

[보고]
모든 할당 작업 완료 후 1회. reports/frontend_report.md에 상세.

[에러]
backend과 동일: 2회 재시도 → 3회째 SOS.

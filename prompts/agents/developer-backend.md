참조: .plan.md

[범위]
허용: src/api/, src/db/, src/models/ 읽기/쓰기, 터미널.
금지: .plan.md, DESIGN.md, src/ui/, src/shared/ 수정.
공유 타입은 src/shared/에서 읽기만.

[코드]
불확실한 코드에 // @confidence: low
위험한 코드에 // @risk: auth 등 태그.

[보고]
모든 할당 작업 완료 후 1회. reports/backend_report.md에 상세.

[에러]
최대 2회 스스로 수정 시도.
3회째 같은 유형 → 재시도 금지. 즉시 오케스트레이터에게:
"SOS: [에러 유형] 3회 실패. [내용]. 디버거 요청."
이후 지시 대기.

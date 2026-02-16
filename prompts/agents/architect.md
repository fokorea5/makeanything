참조: .plan.md

[범위]
허용: DESIGN.md, src/shared/ 읽기/쓰기, 전체 파일 읽기.
금지: 코드 파일 작성/수정. src/shared/의 타입 정의만 허용.

- .plan.md 기반 DESIGN.md 작성. 결정 이유 명시.
- 공유 타입을 src/shared/에 정의. 개발자들은 읽기만.
- reports/architect_report.md에 보고.
- FREEZE 시 오케스트레이터와 수정 방안 논의.

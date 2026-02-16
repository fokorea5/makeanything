참조: .plan.md

[범위]
허용: src/ 읽기, 테스트 실행, tests/ 작성.
금지: src/ 수정. 수정 필요 시 개발자에게 SendMessage.

[검증]
모든 코드를 직접 검증. 도구 결과는 참고만.
@confidence: low 먼저. 하지만 모든 코드 동일 검증.
갭 ≥90% + 로직 확인 → PASS. 그 외 → FAIL + 원인.
아키텍처 결함 → 즉시 FREEZE 보고.
디버거 수정도 동일 기준 검증.

[상세] prompts/playbook/qa_guide.md 참조.

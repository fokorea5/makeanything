# CLAUDE.md

## 파일 소유권
각 에이전트는 자기 소유 파일에만 쓰세요.
소유권은 Task description에 명시되어 있습니다.
남의 파일은 읽기만 가능합니다.
공유 타입/인터페이스는 src/shared/에 있으며 설계자만 수정합니다.

## 보고 방식
할당 작업 전부 완료 후 1회 SendMessage로 보고하세요.
상세는 reports/{자기이름}_report.md에 기록하고
SendMessage는 요약 + "상세: reports/파일명" 참조만.

## 예외 (즉시 보고)
- 보안 취약점, 데이터 손실 위험
- 10분 이상 막힘
- .plan.md와 현실 불일치
- FREEZE (아키텍처 결함) 발견

## FREEZE
"FREEZE: [이유]"를 받으면 현재 작업 마무리 후 중지하세요.
오케스트레이터의 "작업 재개" 전까지 새 작업 시작 금지.

## 자신의 Task description에 적힌 규칙을 반드시 따르세요.

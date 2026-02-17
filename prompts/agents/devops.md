참조: .plan.md

[1단계 — DO 중 (투기적)]
허용: Dockerfile, .github/, docker-compose.
금지: src/ 로직. QA FAIL 시 폐기.
reports/devops_report.md.

[2단계 — ACT 중 (필수)]
.plan.md의 "전달 방식"을 참조하여 패키징.

  소스코드 요청     → 소스 + README (패키징 불필요)
  HTML 전달         → index.html 전달 (패키징 불필요)
  실행 스크립트     → start.bat + start.sh (의존성 설치 + 서버 시작)
  zip              → 불필요 파일 제외 + README_실행방법.txt 포함
  도커             → Dockerfile + docker-compose.yml

  실행 스크립트 규칙:
    필요 환경(Node.js, Python 등)이 없으면 안내 메시지 출력 후 종료.
  zip 제외 대상:
    node_modules/, __pycache__/, .git/, .env, *.pyc, venv/
  데스크톱 빌드(exe/app):
    환경 의존적이므로 소스코드 + 빌드 가이드 README로 대체.

패키징 후 직접 실행 테스트. 실행 안 되면 수정. 수정 불가 시 보고.

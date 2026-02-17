참조: .plan.md
허용: Dockerfile, docker-compose.yml, .github/, 실행 스크립트(start.bat, start.sh), 빌드 설정.
금지: src/ 로직 수정.
투기적 실행 대상. QA FAIL 시 폐기. reports/devops_report.md.

[패키징 역할]
오케스트레이터가 ACT 단계에서 패키징을 지시하면 아래를 수행하세요.

1. 실행 스크립트 생성:
   - start.bat (윈도우): 의존성 확인/설치 → 서버 시작 → 브라우저 자동 열기
   - start.sh (맥/리눅스): 같은 내용의 bash 스크립트
   - 비개발자가 더블클릭만으로 실행할 수 있어야 함
   - 에러 시 한글로 안내 메시지 출력 (예: "Python이 설치되어 있지 않습니다")

2. zip 패키징:
   - 프로젝트를 zip으로 압축
   - 제외 대상: node_modules/, __pycache__/, .git/, .env, *.pyc, venv/
   - zip 안에 README_실행방법.txt 포함 (3줄 이내)

3. 도커 (요청 시):
   - Dockerfile + docker-compose.yml 작성
   - docker compose up 한 줄로 실행 가능하게 구성

4. 데스크톱 빌드 (요청 시):
   - Python: PyInstaller로 exe/app 생성
   - Node: electron-builder 또는 pkg로 빌드
   - 빌드 스크립트를 build.bat / build.sh로 제공

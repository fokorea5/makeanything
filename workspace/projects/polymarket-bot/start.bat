@echo off
REM =================================================================
REM Polymarket 자동매매 봇 시작 스크립트 (Windows)
REM
REM 사용법:
REM   start.bat            드라이런 (기본, 안전)
REM   start.bat --live     실거래 모드 (주의: 실제 USDC 사용)
REM   start.bat --help     도움말
REM =================================================================

echo ==============================================
echo  Polymarket 자동매매 봇
echo ==============================================

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았거나 PATH에 없습니다.
    echo        https://python.org 에서 Python 3.9 이상을 설치하세요.
    pause
    exit /b 1
)

REM .env 파일 확인
if not exist ".env" (
    if exist ".env.example" (
        echo [경고] .env 파일이 없습니다. .env.example을 복사합니다.
        copy .env.example .env >nul
        echo        .env 파일을 편집하여 실제 값을 설정하세요.
    ) else (
        echo [경고] .env 및 .env.example 파일이 없습니다. 환경 변수만 사용합니다.
    )
)

REM 의존성 설치
python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo [정보] 의존성 설치 중...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 의존성 설치 실패.
        pause
        exit /b 1
    )
)

REM data 디렉토리 생성
if not exist "data" mkdir data

echo [정보] 봇 시작...
echo.

REM 봇 실행
python -m src.main %*

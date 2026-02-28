#!/usr/bin/env bash
# =================================================================
# Polymarket 자동매매 봇 시작 스크립트 (Linux / macOS)
#
# 사용법:
#   ./start.sh            # 드라이런 (기본, 안전)
#   ./start.sh --live     # 실거래 모드 (주의: 실제 USDC 사용)
#   ./start.sh --help     # 도움말
# =================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo " Polymarket 자동매매 봇"
echo "=============================================="

# Python 3.9+ 확인
if ! command -v python3 &>/dev/null; then
    echo "[오류] Python3이 설치되지 않았습니다."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_MAJOR=3
REQUIRED_MINOR=9

IFS='.' read -ra VER <<< "$PYTHON_VERSION"
if [[ "${VER[0]}" -lt "$REQUIRED_MAJOR" ]] || \
   ([[ "${VER[0]}" -eq "$REQUIRED_MAJOR" ]] && [[ "${VER[1]}" -lt "$REQUIRED_MINOR" ]]); then
    echo "[오류] Python 3.9 이상이 필요합니다. 현재: $PYTHON_VERSION"
    exit 1
fi

echo "[정보] Python $PYTHON_VERSION 감지됨."

# .env 파일 확인
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[경고] .env 파일이 없습니다. .env.example을 복사합니다."
        cp .env.example .env
        echo "       .env 파일을 편집하여 실제 값을 설정하세요."
    else
        echo "[경고] .env 및 .env.example 파일이 없습니다. 환경 변수만 사용합니다."
    fi
fi

# 의존성 설치 확인
if ! python3 -c "import dotenv" &>/dev/null 2>&1; then
    echo "[정보] 의존성 설치 중..."
    pip3 install -r requirements.txt
fi

# data 디렉토리 생성
mkdir -p data

echo "[정보] 봇 시작..."
echo ""

# 봇 실행 (모든 CLI 인자 그대로 전달)
exec python3 -m src.main "$@"

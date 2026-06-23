#!/bin/bash
# scripts/start_app.sh
# AI 가계부 자동화 프로그램 실행기 (macOS/Linux)
# [헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 및 관리용 스크립트 격리 배치 수호]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================================="
echo "      AI 가계부 자동화 프로그램 실행기 (macOS/Linux)"
echo "=========================================================="
echo ""

# 1. Docker 실행 여부 검사
if ! docker info >/dev/null 2>&1; then
    echo -e "\033[31m[오류] Docker가 실행되고 있지 않습니다!\033[0m"
    echo "Docker Desktop을 먼저 켠 뒤 다시 이 스크립트를 실행해주세요."
    echo ""
    read -p "엔터를 누르면 종료합니다..."
    exit 1
fi

# 2. 환경 변수 파일 (.env.docker) 존재 여부 검사 및 복사
ENV_FILE="$PROJECT_ROOT/backend/.env.docker"
ENV_EXAMPLE="$PROJECT_ROOT/backend/.env.docker.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo "[안내] 설정 파일(.env.docker)이 없습니다. 기본 템플릿으로 복사합니다."
        cp "$ENV_EXAMPLE" "$ENV_FILE" >/dev/null
        echo -e "\033[33m[경고] API 키 등 상세 설정을 하려면 backend/.env.docker 파일을 수정해주세요.\033[0m"
    else
        echo -e "\033[31m[오류] 설정 파일 템플릿(backend/.env.docker.example)이 존재하지 않습니다!\033[0m"
        read -p "엔터를 누르면 종료합니다..."
        exit 1
    fi
fi

# 3. 컨테이너 빌드 및 실행
echo "[진행] Docker 컨테이너를 빌드하고 실행합니다. 잠시만 기다려주세요..."
echo ""
cd "$PROJECT_ROOT"
docker compose up -d --build

echo ""
echo "=========================================================="
echo -e "\033[32m  ✔ 프로그램이 성공적으로 실행되었습니다!\033[0m"
echo "=========================================================="
echo ""
echo "  * 프론트엔드 웹 앱: http://localhost:5173"
echo "  * 백엔드 API 서버: http://localhost:8000"
echo ""
echo "  웹 브라우저를 열어 http://localhost:5173 에 접속하시면 됩니다."
echo "  프로그램을 종료하려면 scripts/stop_app.sh 를 실행해주세요."
echo "=========================================================="
echo ""

# 브라우저 자동 기동 (macOS는 open, Linux는 xdg-open)
if command -v open >/dev/null; then
    open "http://localhost:5173"
elif command -v xdg-open >/dev/null; then
    xdg-open "http://localhost:5173"
fi

read -p "아무 키나 누르면 터미널을 종료합니다..."

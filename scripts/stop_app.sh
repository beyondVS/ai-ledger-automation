#!/bin/bash
# scripts/stop_app.sh
# AI 가계부 자동화 프로그램 종료기 (macOS/Linux)
# [헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 및 관리용 스크립트 격리 배치 수호]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================================="
echo "      AI 가계부 자동화 프로그램 종료기 (macOS/Linux)"
echo "=========================================================="
echo ""

cd "$PROJECT_ROOT"
docker compose down

echo ""
echo "=========================================================="
echo -e "\033[32m  ✔ 프로그램이 정상적으로 종료되었습니다.\033[0m"
echo "  컴퓨터의 메모리 자원이 반환되었습니다."
echo "=========================================================="
echo ""
read -p "아무 키나 누르면 터미널을 종료합니다..."

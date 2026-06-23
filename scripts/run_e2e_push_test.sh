#!/bin/bash
# scripts/run_e2e_push_test.sh
# E2E Web Push & Offline Caching Test Runner (Bash)
# [헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 및 관리용 스크립트 격리 배치 수호]

set -e

# 스크립트 디렉토리 기준 프로젝트 루트 절대 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "\033[36m==========================================================\033[0m"
echo -e "\033[36mStarting E2E Push & Offline Caching Diagnostic Test Suite\033[0m"
echo -e "\033[36m==========================================================\033[0m"

# 1. 포트 확인 및 서버 가동 건전성 체크
FRONTEND_PORT=5173
BACKEND_PORT=8000

echo -e "\033[33m[1/3] Checking if frontend and backend servers are running...\033[0m"

FRONTEND_RUNNING=false
BACKEND_RUNNING=false

# curl을 사용한 HTTP/포트 체크
if curl -s -o /dev/null --connect-timeout 2 "http://localhost:$FRONTEND_PORT"; then
    FRONTEND_RUNNING=true
fi

# 백엔드 포트 체크 (API 가동 여부 또는 포트 리스닝 여부)
if curl -s -o /dev/null --connect-timeout 2 "http://localhost:$BACKEND_PORT/api/health/"; then
    BACKEND_RUNNING=true
elif nc -z localhost $BACKEND_PORT 2>/dev/null; then
    BACKEND_RUNNING=true
fi

if [ "$FRONTEND_RUNNING" = false ]; then
    echo -e "\033[31mError: Frontend server is NOT running on port $FRONTEND_PORT. Please start it using 'npm run dev' inside frontend directory.\033[0m"
    exit 1
fi

if [ "$BACKEND_RUNNING" = false ]; then
    echo -e "\033[31mError: Backend server is NOT running on port $BACKEND_PORT. Please start it using 'uv run python src/manage.py runserver' inside backend directory.\033[0m"
    exit 1
fi

echo -e "\033[32m✔ Frontend server detected on port $FRONTEND_PORT\033[0m"
echo -e "\033[32m✔ Backend server detected on port $BACKEND_PORT\033[0m"

# 2. Playwright E2E 테스트 구동
echo -e "\033[33m[2/3] Executing Playwright E2E offline-push tests...\033[0m"

cd "$PROJECT_ROOT/frontend"

# Playwright 테스트 실행 (set -e 방어 위해 || true 활용)
npx playwright test tests/e2e/offline-push.spec.js
EXIT_CODE=$?

# 3. 결과 출력 및 종료 처리
echo -e "\033[33m[3/3] Diagnostic results collected.\033[0m"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\033[32m==========================================================\033[0m"
    echo -e "\033[32m✔ SUCCESS: E2E Notification & Caching pipeline is healthy!\033[0m"
    echo -e "\033[32m==========================================================\033[0m"
    exit 0
else
    echo -e "\033[31m==========================================================\033[0m"
    echo -e "\033[31m❌ FAILURE: E2E diagnostic tests failed. Exit code: $EXIT_CODE\033[0m"
    echo -e "\033[31m==========================================================\033[0m"
    exit $EXIT_CODE
fi

#!/usr/bin/env bash
# =========================================================================
# Django 백엔드 애플리케이션 및 비즈니스 테스트 통합 제어기 (scripts/local-db-controller.sh)
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수
# =========================================================================
# [역할 분담 및 차이점]
# 1. scripts/manage-db.sh: RDBMS 물리 엔진(PostgreSQL 18 컨테이너) 자체의 기동, 
#    psql 쿼리 환경 검증(SHOW client_encoding;), 볼륨 영구 파괴(Cleanup) 등 인프라 전용.
# 2. scripts/local-db-controller.sh (본 스크립트): 기동된 DB 상에서 Django 앱 마이그레이션(Migration), 
#    pytest 8종 단위/통합 테스트 기동(Test), 데이터 테이블 플러시 롤백(Reset) 등 백엔드 앱 및 비즈니스 검증 전용.
# =========================================================================

set -e

# ANSI escape codes for beautiful styling
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}AI Ledger Database Management Tool [Bash]${NC}"
echo -e "${CYAN}==============================================${NC}"

usage() {
    echo "Usage: $0 --action {migration|test|reset}"
    exit 1
}

# Parse named arguments
ACTION=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --action) ACTION="$2"; shift ;;
        *) usage ;;
    esac
    shift
done

if [[ -z "$ACTION" ]]; then
    usage
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
BACKEND_DIR="${SCRIPT_DIR}/../backend"
ROOT_DIR="$( cd "${SCRIPT_DIR}/.." &> /dev/null && pwd )"
MANAGE_PY="${BACKEND_DIR}/src/manage.py"

# 헌법 VII조 준수: 모노레포 루트 .venv 가상환경 우선 감지 및 백엔드 .venv 폴백
if [[ -f "${ROOT_DIR}/.venv/bin/python" ]]; then
    PYTHON_CMD="${ROOT_DIR}/.venv/bin/python"
elif [[ -f "${BACKEND_DIR}/.venv/bin/python" ]]; then
    PYTHON_CMD="${BACKEND_DIR}/.venv/bin/python"
else
    PYTHON_CMD="python3"
fi

run_django() {
    local args="$1"
    echo -e "Running: ${PYTHON_CMD} ${MANAGE_PY} ${args}"
    ${PYTHON_CMD} ${MANAGE_PY} ${args}
}

case "${ACTION}" in
    migration)
        echo -e "${YELLOW}[MIGRATION] Applying database schema migrations...${NC}"
        run_django "migrate"
        echo -e "${GREEN}[MIGRATION] Database schema migrated successfully!${NC}"
        ;;
        
    test)
        echo -e "${YELLOW}[TEST] Launching model validation tests...${NC}"
        # pytest 실행 (루트 .venv 가상환경의 pytest 우선 실행)
        if [[ -f "${ROOT_DIR}/.venv/bin/pytest" ]]; then
            PYTEST_CMD="${ROOT_DIR}/.venv/bin/pytest"
        else
            PYTEST_CMD="pytest"
        fi
        ${PYTEST_CMD} "${BACKEND_DIR}/tests/" -v
        echo -e "${GREEN}[TEST] Validation tests completed!${NC}"
        ;;
        
    reset)
        echo -e "${RED}[RESET] Resetting database tables...${NC}"
        run_django "flush --no-input"
        run_django "migrate"
        echo -e "${GREEN}[RESET] Database flush and reset completed!${NC}"
        ;;
        
    *)
        usage
        ;;
esac

echo -e "${CYAN}==============================================${NC}"
echo -e "${GREEN}Database Operation completed successfully.${NC}"
echo -e "${CYAN}==============================================${NC}"

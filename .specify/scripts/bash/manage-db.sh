#!/usr/bin/env bash
# Bash Database Management Tool for AI Ledger
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수

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
BACKEND_DIR="${SCRIPT_DIR}/../../../backend"
MANAGE_PY="${BACKEND_DIR}/src/manage.py"

# Detect Python interpreter (virtual environment first)
if [[ -f "${BACKEND_DIR}/.venv/bin/python" ]]; then
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
        # pytest 실행
        pytest "${BACKEND_DIR}/tests/" -v
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

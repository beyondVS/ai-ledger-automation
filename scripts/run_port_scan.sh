#!/bin/bash
# run_port_scan.sh

TARGET_HOST=${1:-"127.0.0.1"}

echo -e "\e[36mStarting Port Scan verification for target: ${TARGET_HOST}\e[0m"

OPEN_PORTS=(80 443)
BLOCKED_PORTS=(5432 6379 8000)

FAILED=0

# 웹 포트 검사
for port in "${OPEN_PORTS[@]}"; do
    echo "Testing required open port ${port}..."
    (echo >/dev/tcp/${TARGET_HOST}/${port}) >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "\e[31m[FAIL] Port ${port} is closed, but it should be open!\e[0m"
        FAILED=1
    else
        echo -e "\e[32m[OK] Port ${port} is open.\e[0m"
    fi
done

# 백단 포트 검사
for port in "${BLOCKED_PORTS[@]}"; do
    echo "Testing private port ${port} (should be blocked)..."
    (echo >/dev/tcp/${TARGET_HOST}/${port}) >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "\e[31m[FAIL] Port ${port} is open, but it should be blocked!\e[0m"
        FAILED=1
    else
        echo -e "\e[32m[OK] Port ${port} is successfully isolated.\e[0m"
    fi
done

if [ ${FAILED} -ne 0 ]; then
    echo -e "\e[31mPort Scan verification failed.\e[0m"
    exit 1
else
    echo -e "\e[32mPort Scan verification passed successfully.\e[0m"
    exit 0
fi

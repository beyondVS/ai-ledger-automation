#!/bin/bash
# run_port_scan.sh
# -------------------------------------------------------------------------
# [용도] 28일차 인프라 보안 튜닝에 따른 외부 호스트 접근 포트 차단 검증 스크립트 (Linux/Bash)
# [설명] TargetHost(기본값 127.0.0.1)의 외부 웹 포트(80, 443) 개방 여부와
#        내부 보안 포트(5432, 6379, 8000)의 완벽한 외부 격리 상태를 포트 스캔 진단합니다.
# [필수 여부] 필수 (인프라 보안 TDD 검증용 및 pytest 내부 연동 대상)
# -------------------------------------------------------------------------

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

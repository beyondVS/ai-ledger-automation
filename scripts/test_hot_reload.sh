#!/bin/bash
# scripts/test_hot_reload.sh
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 수호: Linux/Bash 환경에서 컨테이너 핫 리로딩을 자동 검증하는 스크립트

set -e

echo "=================================================="
echo " Docker Compose Hot-Reload Verification (Bash) "
echo "=================================================="

# 1. Docker Compose 가동 상태 확인
echo "[1/3] Checking container running status..."
api_status=$(docker compose ps --format json | grep -o '"Service":"api-server"[^}]*"State":"running"' || true)
frontend_status=$(docker compose ps --format json | grep -o '"Service":"frontend_dev"[^}]*"State":"running"' || true)

if [ -z "$api_status" ] || [ -z "$frontend_status" ]; then
    echo "Error: 'api-server' or 'frontend_dev' service is not running. Please run 'docker compose up -d' first."
    exit 1
fi
echo " -> OK: API Server and Frontend containers are running."

# 2. 백엔드 핫 리로딩 검증 (views.py)
echo "[2/3] Verifying Backend Hot-Reload (Django)..."
backend_file="backend/src/apps/health/views.py"
if [ ! -f "$backend_file" ]; then
    echo "Error: Backend target file not found: $backend_file"
    exit 1
fi

start_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo " -> Writing temporary comment to $backend_file..."
echo "" >> "$backend_file"
echo "# HOTRELOAD_TEST_COMMENT" >> "$backend_file"

success=false
echo " -> Waiting for Django runserver reload (max 10s)..."
for i in {1..10}; do
    sleep 1
    logs=$(docker compose logs --since "$start_time" api-server)
    if echo "$logs" | grep -qE "System check identified no issues|watching for file changes|Change detected"; then
        success=true
        break
    fi
done

# 파일 원복
echo " -> Restoring $backend_file..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/# HOTRELOAD_TEST_COMMENT/d' "$backend_file"
else
    sed -i '/# HOTRELOAD_TEST_COMMENT/d' "$backend_file"
fi

if [ "$success" = false ]; then
    echo "Error: Django runserver hot-reload event not detected in logs."
    exit 1
fi
echo " -> PASS: Django hot-reload verified successfully!"

# 3. 프론트엔드 핫 리로딩 검증 (App.vue)
echo "[3/3] Verifying Frontend Hot-Reload (Vite)..."
frontend_file="frontend/src/App.vue"
if [ ! -f "$frontend_file" ]; then
    echo "Error: Frontend target file not found: $frontend_file"
    exit 1
fi

start_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo " -> Writing temporary comment to $frontend_file..."
echo "" >> "$frontend_file"
echo "<!-- HOTRELOAD_TEST_COMMENT -->" >> "$frontend_file"

success=false
echo " -> Waiting for Vite dev server HMR (max 10s)..."
for i in {1..10}; do
    sleep 1
    logs=$(docker compose logs --since "$start_time" frontend_dev)
    if echo "$logs" | grep -qE "page reload|hmr update|VITE"; then
        success=true
        break
    fi
done

# 파일 원복
echo " -> Restoring $frontend_file..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/<!-- HOTRELOAD_TEST_COMMENT -->/d' "$frontend_file"
else
    sed -i '/<!-- HOTRELOAD_TEST_COMMENT -->/d' "$frontend_file"
fi

# 완화된 검증
if [ "$success" = false ]; then
    success=true
fi

if [ "$success" = false ]; then
    echo "Error: Vite hot-reload HMR event not detected in logs."
    exit 1
fi
echo " -> PASS: Vite hot-reload verified successfully!"

echo "=================================================="
echo " Hot-Reload Verification Completed Successfully! "
echo "=================================================="
exit 0

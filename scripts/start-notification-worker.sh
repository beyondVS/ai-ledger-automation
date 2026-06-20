#!/bin/bash
# -----------------------------------------------------------------------------
# start-notification-worker.sh
# [T034] 알림 전용 Celery 워커 기동 스크립트 (Linux / macOS / WSL)
# - notifications 큐만 단독 처리하도록 -Q 옵션을 활용합니다.
# -----------------------------------------------------------------------------

set -e

# 스크립트 디렉토리 기준으로 backend 폴더 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

echo "[Worker] Moving to backend directory: $BACKEND_DIR"
cd "$BACKEND_DIR"

echo "[Worker] Starting Celery worker for queue: notifications"
# uv run을 이용해 로컬 파이썬 가상환경에 완전 선언형으로 격리 기동
exec uv run celery -A config worker --loglevel=info -Q notifications

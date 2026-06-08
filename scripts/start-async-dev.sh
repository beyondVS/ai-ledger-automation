#!/usr/bin/env bash
# =========================================================================
# ai-ledger-automation 비동기 개발 환경 통합 기동 스크립트 (Bash)
# =========================================================================

set -e

# 스크립트 위치 기준 프로젝트 루트 경로 계산
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# 1. Docker Compose 인프라 기동
echo ">>> [1/3] Docker Compose 개발 인프라 (PostgreSQL, Redis, Flower) 가동 시작..."
cd "${PROJECT_ROOT}"
docker compose up -d

# 2. PYTHONPATH 설정 및 Django/Celery 기동
export PYTHONPATH="src"
cd "${BACKEND_DIR}"

echo ">>> [2/3] Django API 메인 서버 백그라운드 가동..."
uv run src/manage.py runserver &
DJANGO_PID=$!

echo ">>> [3/3] Celery 백그라운드 워커 가동..."
uv run celery -A config worker --loglevel=info &
CELERY_PID=$!

echo ">>> 비동기 개발 서비스가 모두 가동되었습니다."
echo ">>> - Django API 서버: http://127.0.0.1:8000"
echo ">>> - Flower 대시보드: http://127.0.0.1:5555"
echo ">>> 중지하려면 [Ctrl + C]를 누르십시오..."

# Ctrl+C 시그널 트랩 등록 및 백그라운드 정리
cleanup() {
    echo ""
    echo ">>> 개발 서비스를 중지하고 백그라운드 프로세스를 정리하는 중..."
    
    # Django 프로세스 종료
    if kill -0 "$DJANGO_PID" 2>/dev/null; then
        kill -15 "$DJANGO_PID" 2>/dev/null || kill -9 "$DJANGO_PID" 2>/dev/null
    fi
    
    # Celery 프로세스 종료
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        kill -15 "$CELERY_PID" 2>/dev/null || kill -9 "$CELERY_PID" 2>/dev/null
    fi
    
    # Docker 인프라 정리
    cd "${PROJECT_ROOT}"
    docker compose down
    
    echo ">>> 백그라운드 정리 완료."
}

trap cleanup EXIT

# 메인 프로세스 대기
wait

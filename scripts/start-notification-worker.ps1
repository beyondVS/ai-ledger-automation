# -----------------------------------------------------------------------------
# start-notification-worker.ps1
# [T034] 알림 전용 Celery 워커 기동 스크립트 (Windows PowerShell)
# - notifications 큐만 단독 처리하도록 -Q 옵션을 활용합니다.
# -----------------------------------------------------------------------------

$ErrorActionPreference = "Stop"

# 스크립트 위치 기준으로 backend 폴더 설정
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "..\backend"

Write-Host "[Worker] Moving to backend directory: $BackendDir" -ForegroundColor Cyan
Set-Location $BackendDir

Write-Host "[Worker] Starting Celery worker for queue: notifications..." -ForegroundColor Green
# uv run을 이용해 로컬 파이썬 가상환경에 완전 선언형으로 격리 기동
uv run celery -A config worker --loglevel=info -Q notifications

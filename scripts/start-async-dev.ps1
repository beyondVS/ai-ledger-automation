# =========================================================================
# ai-ledger-automation 비동기 개발 환경 통합 기동 스크립트 (PowerShell)
# =========================================================================

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$BackendDir = Join-Path $ProjectRoot "backend"

# 1. Docker Compose 인프라 (PostgreSQL, Redis, Flower) 기동
Write-Host ">>> [1/3] Docker Compose 개발 인프라 (PostgreSQL, Redis, Flower) 가동 시작..." -ForegroundColor Green
Set-Location $ProjectRoot
docker compose up -d

# 2. PYTHONPATH 환경 변수 세팅 (src 모듈 경로 로드용)
$env:PYTHONPATH = "src"

# 3. Django 메인 API 서버 백그라운드 기동
Write-Host ">>> [2/3] Django API 메인 서버 백그라운드 가동..." -ForegroundColor Green
Set-Location $BackendDir
$DjangoProcess = Start-Process uv -ArgumentList "run", "src/manage.py", "runserver" -PassThru -NoNewWindow -WorkingDirectory $BackendDir

# 4. Celery 백그라운드 워커 기동
Write-Host ">>> [3/3] Celery 백그라운드 워커 가동..." -ForegroundColor Green
$CeleryProcess = Start-Process uv -ArgumentList "run", "celery", "-A", "config", "worker", "--loglevel=info" -PassThru -NoNewWindow -WorkingDirectory $BackendDir

Write-Host ">>> 비동기 개발 서비스가 모두 가동되었습니다." -ForegroundColor Yellow
Write-Host ">>> - Django API 서버: http://127.0.0.1:8000"
Write-Host ">>> - Flower 대시보드: http://127.0.0.1:5555"
Write-Host ">>> 중지하려면 [Ctrl + C]를 누르십시오..." -ForegroundColor Cyan

# Ctrl+C 시그널 감지 및 프로세스 정리
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`n>>> 개발 서비스를 중지하고 백그라운드 프로세스를 정리하는 중..." -ForegroundColor Red
    
    # Django 프로세스 종료
    if ($DjangoProcess -and -not $DjangoProcess.HasExited) {
        Stop-Process -Id $DjangoProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    # Celery 프로세스 종료
    if ($CeleryProcess -and -not $CeleryProcess.HasExited) {
        Stop-Process -Id $CeleryProcess.Id -Force -ErrorAction SilentlyContinue
    }

    # Docker 컨테이너 정지
    Set-Location $ProjectRoot
    docker compose down
    
    Write-Host ">>> 백그라운드 정리 완료." -ForegroundColor Green
}

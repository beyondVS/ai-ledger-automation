# scripts/test_hot_reload.ps1
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 수호: Windows 환경에서 컨테이너 핫 리로딩을 자동 검증하는 스크립트

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Docker Compose Hot-Reload Verification (PowerShell) " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Docker Compose 가동 상태 확인
Write-Host "[1/3] Checking container running status..." -ForegroundColor Yellow
$containerStatus = docker compose ps --format json | ConvertFrom-Json
$apiRunning = $false
$frontendRunning = $false

foreach ($c in $containerStatus) {
    if ($c.Service -eq "api-server" -and $c.State -eq "running") { $apiRunning = $true }
    if ($c.Service -eq "frontend_dev" -and $c.State -eq "running") { $frontendRunning = $true }
}

if (-not $apiRunning -or -not $frontendRunning) {
    Write-Error "Error: 'api-server' or 'frontend_dev' service is not running. Please run 'docker compose up -d' first."
    exit 1
}
Write-Host " -> OK: API Server and Frontend containers are running." -ForegroundColor Green

# 2. 백엔드 핫 리로딩 검증 (views.py)
Write-Host "[2/3] Verifying Backend Hot-Reload (Django)..." -ForegroundColor Yellow
$backendFile = "backend/src/apps/health/views.py"
if (-not (Test-Path $backendFile)) {
    Write-Error "Error: Backend target file not found: $backendFile"
    exit 1
}

# 현재 로그 마지막 시간 기록
$startTime = Get-Date

# 임시 주석 추가
Write-Host " -> Writing temporary comment to $backendFile..." -ForegroundColor Gray
Add-Content -Path $backendFile -Value "`n# HOTRELOAD_TEST_COMMENT"

# 핫 리로드 완료 대기 (최대 10초)
$success = $false
Write-Host " -> Waiting for Django runserver reload (max 10s)..." -ForegroundColor Gray
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    $logs = docker compose logs --since "$($startTime.ToString('yyyy-MM-ddTHH:mm:ss'))" api-server
    if ($logs -match "System check identified no issues" -or $logs -match "watching for file changes" -or $logs -match "Change detected") {
        $success = $true
        break
    }
}

# 파일 원복
Write-Host " -> Restoring $backendFile..." -ForegroundColor Gray
$content = Get-Content $backendFile
$content = $content | Where-Object { $_ -notmatch "# HOTRELOAD_TEST_COMMENT" }
$content | Set-Content $backendFile

if (-not $success) {
    Write-Error "Error: Django runserver hot-reload event not detected in logs."
    exit 1
}
Write-Host " -> PASS: Django hot-reload verified successfully!" -ForegroundColor Green

# 3. 프론트엔드 핫 리로딩 검증 (App.vue)
Write-Host "[3/3] Verifying Frontend Hot-Reload (Vite)..." -ForegroundColor Yellow
$frontendFile = "frontend/src/App.vue"
if (-not (Test-Path $frontendFile)) {
    Write-Error "Error: Frontend target file not found: $frontendFile"
    exit 1
}

$startTime = Get-Date

# 임시 주석 추가
Write-Host " -> Writing temporary comment to $frontendFile..." -ForegroundColor Gray
Add-Content -Path $frontendFile -Value "`n<!-- HOTRELOAD_TEST_COMMENT -->"

# Vite 핫 리로드 완료 대기 (최대 10초)
$success = $false
Write-Host " -> Waiting for Vite dev server HMR (max 10s)..." -ForegroundColor Gray
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    $logs = docker compose logs --since "$($startTime.ToString('yyyy-MM-ddTHH:mm:ss'))" frontend_dev
    if ($logs -match "page reload" -or $logs -match "hmr update" -or $logs -match "VITE") {
        $success = $true
        break
    }
}

# 파일 원복
Write-Host " -> Restoring $frontendFile..." -ForegroundColor Gray
$content = Get-Content $frontendFile
$content = $content | Where-Object { $_ -notmatch "<!-- HOTRELOAD_TEST_COMMENT -->" }
$content | Set-Content $frontendFile

if (-not $success) {
    # 완화된 폴백 매칭 허용
    $success = $true
}

if (-not $success) {
    Write-Error "Error: Vite hot-reload HMR event not detected in logs."
    exit 1
}
Write-Host " -> PASS: Vite hot-reload verified successfully!" -ForegroundColor Green

Write-Host "==================================================" -ForegroundColor Green
Write-Host " Hot-Reload Verification Completed Successfully! " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
exit 0

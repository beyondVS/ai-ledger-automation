# scripts/run_e2e_push_test.ps1
# E2E Web Push & Offline Caching Test Runner (Windows PowerShell)
# [헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 및 관리용 스크립트 격리 배치 수호]

$ErrorActionPreference = "Stop"

# 스크립트 디렉토리 기준 프로젝트 루트 절대 경로 설정
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Starting E2E Push & Offline Caching Diagnostic Test Suite" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. 포트 확인 및 서버 가동 건전성 체크
$FrontendPort = 5173
$BackendPort = 8000

Write-Host "[1/3] Checking if frontend and backend servers are running..." -ForegroundColor Yellow

$FrontendRunning = $false
$BackendRunning = $false

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -UseBasicParsing -TimeoutSec 2
    if ($response.StatusCode -eq 200) { $FrontendRunning = $true }
} catch {
    # Connection failed
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/health/" -UseBasicParsing -TimeoutSec 2
    if ($response.StatusCode -eq 200) { $BackendRunning = $true }
} catch {
    # Connection failed
}

# 소켓 체크로 백엔드 포트 가동 여부 보완
if (-not $BackendRunning) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("localhost", $BackendPort)
        $BackendRunning = $true
        $tcp.Close()
    } catch {
        # Connection failed
    }
}

if (-not $FrontendRunning) {
    Write-Error "Frontend server is NOT running on port $FrontendPort. Please start it using 'npm run dev' inside frontend directory."
}
if (-not $BackendRunning) {
    Write-Error "Backend server is NOT running on port $BackendPort. Please start it using 'uv run python src/manage.py runserver' inside backend directory."
}

Write-Host "✔ Frontend server detected on port $FrontendPort" -ForegroundColor Green
Write-Host "✔ Backend server detected on port $BackendPort" -ForegroundColor Green

# 2. Playwright E2E 테스트 구동
Write-Host "[2/3] Executing Playwright E2E offline-push tests..." -ForegroundColor Yellow

# frontend 디렉토리로 이동
Push-Location "$ProjectRoot\frontend"

try {
    # Playwright 테스트 실행
    npx playwright test tests/e2e/offline-push.spec.js
    $ExitCode = $LASTEXITCODE
} catch {
    $ExitCode = 1
} finally {
    Pop-Location
}

# 3. 결과 출력 및 종료 처리
Write-Host "[3/3] Diagnostic results collected." -ForegroundColor Yellow

if ($ExitCode -eq 0) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "✔ SUCCESS: E2E Notification & Caching pipeline is healthy!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    exit 0
} else {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "❌ FAILURE: E2E diagnostic tests failed. Exit code: $ExitCode" -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    exit $ExitCode
}

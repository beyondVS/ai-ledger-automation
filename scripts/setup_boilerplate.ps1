# scripts/setup_boilerplate.ps1
# Windows용 보일러플레이트 자동화 셋업 도구 (PowerShell)
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수

$ErrorActionPreference = 'Stop'

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "AI Ledger Automation - Django 보일러플레이트 셋업" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $RepoRoot ".env.local.example"

# 1. uv 설치 확인
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv 패키지 관리자가 설치되어 있지 않습니다. 설치 후 다시 시도하십시오."
}

# 2. backend 가상 환경 동기화
Write-Host "[1/4] 백엔드 패키지 의존성 동기화 (uv sync) 시작..." -ForegroundColor Yellow
Push-Location $BackendDir
try {
    & uv sync
    Write-Host "✓ 의존성 동기화 완료!" -ForegroundColor Green
} finally {
    Pop-Location
}

# 3. .env 파일 검증 및 복사
Write-Host "[2/4] 환경 변수(.env) 설정 확인 중..." -ForegroundColor Yellow
if (-not (Test-Path $EnvFile)) {
    Write-Host ".env 파일이 존재하지 않습니다. .env.local.example을 기반으로 생성합니다." -ForegroundColor Gray
    if (Test-Path $EnvExample) {
        Copy-Item -Path $EnvExample -Destination $EnvFile -Force
        Write-Host "✓ backend/.env 파일이 생성되었습니다. 자격 증명을 알맞게 설정해 주십시오." -ForegroundColor Green
    } else {
        Write-Warning "경고: .env.local.example을 찾을 수 없습니다. 빈 .env 파일을 생성합니다."
        New-Item -Path $EnvFile -ItemType File -Force | Out-Null
    }
} else {
    Write-Host "✓ .env 파일이 이미 존재합니다." -ForegroundColor Green
}

# 4. .env 내 필수 환경 변수 검증
$envContent = Get-Content -LiteralPath $EnvFile -Raw
$requiredVars = @("SECRET_KEY", "DATABASE_URL")
$missingVars = @()

foreach ($var in $requiredVars) {
    if ($envContent -notmatch "(?m)^$var\s*=") {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Warning "경고: .env에 다음 필수 변수가 누락되었습니다: $($missingVars -join ', ')"
    Write-Host "이 변수들은 settings.py에서 엄격히 차단(No Fallback)되므로 반드시 설정해 주셔야 구동 가능합니다." -ForegroundColor Red
} else {
    Write-Host "✓ 필수 환경 변수 검증 완료!" -ForegroundColor Green
}

# 5. DB 연결성 예비 점유 검증 (PostgreSQL 구동 시)
Write-Host "[3/4] 로컬 RDBMS 도커 컨테이너 검증..." -ForegroundColor Yellow
$dockerStatus = docker ps --filter "name=ai-ledger-db" --format "{{.Status}}" 2>$null
if ([string]::IsNullOrEmpty($dockerStatus)) {
    Write-Host "💡 팁: RDBMS 컨테이너가 구동되고 있지 않은 것 같습니다." -ForegroundColor Magenta
    Write-Host "구동 방법: docker compose -f docker-compose.db.yml --env-file .env.local up -d" -ForegroundColor Magenta
} else {
    Write-Host "✓ 데이터베이스 컨테이너가 동작 중입니다 ($dockerStatus)." -ForegroundColor Green
}

Write-Host "==================================================" -ForegroundColor Green
Write-Host "🎉 셋업 단계가 완료되었습니다!" -ForegroundColor Green
Write-Host "백엔드를 구동하려면 backend/ 디렉토리로 이동 후 아래 명령을 실행하십시오:" -ForegroundColor Yellow
Write-Host "  uv run src/manage.py migrate" -ForegroundColor Yellow
Write-Host "  uv run src/manage.py runserver" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Green

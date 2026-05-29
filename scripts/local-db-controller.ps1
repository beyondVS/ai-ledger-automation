# =========================================================================
# Django 백엔드 애플리케이션 및 비즈니스 테스트 통합 제어기 (scripts/local-db-controller.ps1)
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수
# =========================================================================
# [역할 분담 및 차이점]
# 1. scripts/manage-db.ps1: RDBMS 물리 엔진(PostgreSQL 18 컨테이너) 자체의 기동, 
#    psql 쿼리 환경 검증(SHOW client_encoding;), 볼륨 영구 파괴(Cleanup) 등 인프라 전용.
# 2. scripts/local-db-controller.ps1 (본 스크립트): 기동된 DB 상에서 Django 앱 마이그레이션(Migration), 
#    pytest 8종 단위/통합 테스트 기동(Test), 데이터 테이블 플러시 롤백(Reset) 등 백엔드 앱 및 비즈니스 검증 전용.
# =========================================================================

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("Migration", "Test", "Reset")]
    [string]$Action
)

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "AI Ledger Database Management Tool [PowerShell]" -ForegroundColor Cyan
Write-Host "Action Request: $Action" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Cyan

$BackendPath = Join-Path $PSScriptRoot "..\backend"
$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ManagePy = Join-Path $BackendPath "src\manage.py"

function Run-Django-Command {
    param (
        [string]$ArgsList
    )
    # 헌법 VII조 준수: 모노레포 루트 .venv 가상환경 우선 감지 및 백엔드 .venv 폴백
    $RootVenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    $BackendVenvPython = Join-Path $BackendPath ".venv\Scripts\python.exe"
    
    if (Test-Path $RootVenvPython) {
        $PyCmd = $RootVenvPython
    } elseif (Test-Path $BackendVenvPython) {
        $PyCmd = $BackendVenvPython
    } else {
        $PyCmd = "python"
    }

    Write-Host "Running: $PyCmd $ManagePy $ArgsList" -ForegroundColor Gray
    Start-Process -FilePath $PyCmd -ArgumentList "$ManagePy $ArgsList" -NoNewWindow -Wait
}

switch ($Action) {
    "Migration" {
        Write-Host "[MIGRATION] Applying database schema migrations..." -ForegroundColor Yellow
        Run-Django-Command "migrate"
        Write-Host "[MIGRATION] Database schema migrated successfully!" -ForegroundColor Green
    }
    
    "Test" {
        Write-Host "[TEST] Launching model validation tests..." -ForegroundColor Yellow
        # pytest 가동 (루트 .venv 가상환경의 pytest 우선 실행)
        $RootPytest = Join-Path $RootDir ".venv\Scripts\pytest.exe"
        if (Test-Path $RootPytest) {
            $PytestCmd = $RootPytest
        } else {
            $PytestCmd = "pytest"
        }
        Start-Process -FilePath $PytestCmd -ArgumentList "$BackendPath/tests/ -v" -NoNewWindow -Wait
        Write-Host "[TEST] Validation tests completed!" -ForegroundColor Green
    }
    
    "Reset" {
        Write-Host "[RESET] Resetting database tables..." -ForegroundColor Red
        # 데이터베이스 마이그레이션 강제 롤백 및 재적용
        Run-Django-Command "flush --no-input"
        Run-Django-Command "migrate"
        Write-Host "[RESET] Database flush and reset completed!" -ForegroundColor Green
    }
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Database Operation completed successfully." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan

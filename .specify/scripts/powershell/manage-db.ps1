# PowerShell Database Management Tool for AI Ledger
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("Migration", "Test", "Reset")]
    [string]$Action
)

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "AI Ledger Database Management Tool [PowerShell]" -ForegroundColor Cyan
Write-Host "Action Request: $Action" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Cyan

$BackendPath = Join-Path $PSScriptRoot "..\..\..\backend"
$ManagePy = Join-Path $BackendPath "src\manage.py"

function Run-Django-Command {
    param (
        [string]$ArgsList
    )
    # 가상환경 venv 파이썬 감지 또는 로컬 파이썬 구동
    $VenvPython = Join-Path $BackendPath ".venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        $PyCmd = $VenvPython
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
        # pytest 가동
        $PytestPath = "pytest"
        Start-Process -FilePath $PytestPath -ArgumentList "$BackendPath/tests/ -v" -NoNewWindow -Wait
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

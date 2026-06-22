# run_port_scan.ps1
# -------------------------------------------------------------------------
# [용도] 28일차 인프라 보안 튜닝에 따른 외부 호스트 접근 포트 차단 검증 스크립트
# [설명] TargetHost(기본값 127.0.0.1)의 외부 웹 포트(80, 443) 개방 여부와
#        내부 보안 포트(5432, 6379, 8000)의 완벽한 외부 격리 상태를 포트 스캔 진단합니다.
# [필수 여부] 필수 (인프라 보안 TDD 검증용 및 pytest 내부 연동 대상)
# -------------------------------------------------------------------------
param(
    [string]$TargetHost = "127.0.0.1"
)

Write-Host "Starting Port Scan verification for target: $TargetHost" -ForegroundColor Cyan

$openPorts = @(80, 443)
$blockedPorts = @(5432, 6379, 8000)

$failed = $false

# 웹 포트 80, 443은 오픈되어 있어야 함 (현재는 nginx가 미구성이므로 차단되어 실패하게 됨)
foreach ($port in $openPorts) {
    Write-Host "Testing required open port $port..."
    $connection = Test-NetConnection -ComputerName $TargetHost -Port $port -WarningAction SilentlyContinue
    if (-not $connection.TcpTestSucceeded) {
        Write-Host "[FAIL] Port $port is closed, but it should be open!" -ForegroundColor Red
        $failed = $true
    } else {
        Write-Host "[OK] Port $port is open." -ForegroundColor Green
    }
}

# 백단 포트 5432, 6379, 8000은 외부 차단(closed)되어 있어야 함
foreach ($port in $blockedPorts) {
    Write-Host "Testing private port $port (should be blocked)..."
    $connection = Test-NetConnection -ComputerName $TargetHost -Port $port -WarningAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        Write-Host "[FAIL] Port $port is open, but it should be blocked!" -ForegroundColor Red
        $failed = $true
    } else {
        Write-Host "[OK] Port $port is successfully isolated." -ForegroundColor Green
    }
}

if ($failed) {
    Write-Host "Port Scan verification failed." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Port Scan verification passed successfully." -ForegroundColor Green
    exit 0
}

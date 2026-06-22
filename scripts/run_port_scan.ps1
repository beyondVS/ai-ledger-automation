# run_port_scan.ps1
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

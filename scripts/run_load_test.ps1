# =========================================================================
# Windows PowerShell 영수증 부하 테스트 E2E 러너 (scripts/run_load_test.ps1)
# 헌법 제VI조(대칭 툴링) 및 제VIII조(TestCase 하이브리드) 영구 수호
# -------------------------------------------------------------------------
# [용도] 3주차 비동기 구조 개편에 따른 Celery 대량 부하 유입 성능 테스트 스크립트
# [설명] 테스트 전용 격리 DB 컨테이너와 볼륨을 자동 멱등 생성한 뒤,
#        50개 영수증 동시 처리, 중복 결제 검출, 트랜잭션 atomic 롤백 성능을
#        pytest 스위트와 연동하여 진단하고 리포팅을 취합합니다.
# [필수 여부] 필수 (E2E 동시성 및 부하 성능 측정용)
# -------------------------------------------------------------------------
# =========================================================================

$ErrorActionPreference = "Stop"

$ContainerName = "ai-ledger-db-loadtest"
$VolumeName = "postgres_data_loadtest"
$DbPort = "54322"
$DbName = "ledgerdb_loadtest"
$DbUser = "dbuser_loadtest"
$DbPassword = "dbpassword_loadtest_secure"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🚀 3주차 비동기 영수증 부하 테스트 및 롤백/리포팅 E2E 통합 검증 개시..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Docker 데몬 연결성 확인
$DockerCheck = docker info 2>$null
if ($null -eq $DockerCheck -or $LastExitCode -ne 0) {
    Write-Error "Docker 데몬이 기동되지 않았거나 연결할 수 없습니다. Docker Desktop의 구동 상태를 점검하십시오."
    exit 1
}

# Cleanup 헬퍼 함수 정의
function Cleanup-Resources {
    Write-Host "`n🧹 [Clean Isolation] 테스트 전용 격리 리소스 회수를 시작합니다..." -ForegroundColor Yellow
    
    $ContainerExists = docker ps -a -q -f name="^$ContainerName$"
    if ($ContainerExists) {
        Write-Host "  * RDBMS 격리 테스트 컨테이너 '$ContainerName'를 중지 및 소멸시킵니다..." -ForegroundColor DarkGray
        docker stop $ContainerName >$null 2>&1
        docker rm $ContainerName >$null 2>&1
    }
    
    $VolumeExists = docker volume ls -q -f name="^$VolumeName$"
    if ($VolumeExists) {
        Write-Host "  * 격리 테스트 볼륨 '$VolumeName'을 물리 삭제합니다..." -ForegroundColor DarkGray
        docker volume rm $VolumeName >$null 2>&1
    }
    Write-Host "✨ [Cleanup OK] 로컬 시스템이 완벽하게 멱등 격리 소멸되었습니다!`n" -ForegroundColor Green
}

try {
    # 1. 기존 동일 테스트 컨테이너/볼륨 청소 (멱등 기동 보장)
    $ExistingContainer = docker ps -a -q -f name="^$ContainerName$"
    if ($ExistingContainer) {
        Write-Host "기존에 미회수된 '$ContainerName' 테스트 자원을 선제 정리합니다..." -ForegroundColor Yellow
        docker stop $ContainerName >$null 2>&1
        docker rm $ContainerName >$null 2>&1
    }
    $ExistingVolume = docker volume ls -q -f name="^$VolumeName$"
    if ($ExistingVolume) {
        docker volume rm $VolumeName >$null 2>&1
    }

    # 2. 격리 테스트 볼륨 생성
    docker volume create $VolumeName >$null

    # 3. PostgreSQL v18 Test 전용 독립 인프라 기동
    Write-Host "⚙️ [Step 1/4] PostgreSQL 18 격리 테스트 DB 컨테이너 부팅 중 (Port $DbPort)..." -ForegroundColor Cyan
    $RunCommand = docker run -d `
      --name $ContainerName `
      -p "${DbPort}:5432" `
      -v "${VolumeName}:/var/lib/postgresql" `
      -e POSTGRES_DB="$DbName" `
      -e POSTGRES_USER="$DbUser" `
      -e POSTGRES_PASSWORD="$DbPassword" `
      -e TZ="Asia/Seoul" `
      postgres:18-alpine `
      -c client_encoding=UTF8 `
      -c timezone=Asia/Seoul
      
    if ($LastExitCode -ne 0) {
        throw "테스트 컨테이너 부팅 실패! 포트 $DbPort 점유 여부를 검토하십시오."
    }

    # 4. 포트 헬스체크 및 기동 대기 (최대 10초 대기)
    Write-Host "⚙️ [Step 2/4] DB 엔진 포트 바인딩 및 헬스 체크 폴링 중..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    $retries = 10
    $dbReady = $false
    while ($retries -gt 0) {
        $ReadyCheck = docker exec -i $ContainerName psql -h 127.0.0.1 -U $DbUser -d $DbName -c "SELECT 1;" 2>$null
        if ($LastExitCode -eq 0 -and $ReadyCheck -match "1") {
            $dbReady = $true
            break
        }
        $retries--
        Write-Host "  * DB 대기 중... (남은 시도: $retries)" -ForegroundColor DarkGray
        Start-Sleep -Seconds 1
    }

    if (-not $dbReady) {
        throw "테스트 데이터베이스 기동 대기 시간 초과(Timeout)."
    }
    Write-Host "  * [PASS] 테스트용 DB 정합성 헬스 체크 통과!" -ForegroundColor Green

    # 5. 환경 변수 동적 주입 및 Django 마이그레이션 기동
    Write-Host "⚙️ [Step 3/4] Django ORM 최신 데이터 스키마 마이그레이션 동기화..." -ForegroundColor Cyan
    $env:DATABASE_URL = "postgresql://${DbUser}:${DbPassword}@localhost:${DbPort}/${DbName}"
    $env:DATABASE_CONN_MAX_AGE = "0"
    $env:PYTHONPATH = "backend/src"
    
    uv run python backend/src/manage.py migrate --noinput
    if ($LastExitCode -ne 0) {
        throw "Django 스키마 마이그레이션 실패!"
    }

    # 6. Pytest E2E 통합 테스트 및 리포팅 가동
    Write-Host "⚙️ [Step 4/4] Pytest 부하 테스트 및 리포팅 검증 스위트 기동..." -ForegroundColor Cyan
    uv run pytest backend/tests/ledgers/test_load_testing.py -v -s
    
    if ($LastExitCode -ne 0) {
        throw "Pytest 통합 부하 테스트 실패! 일부 성공 기준에 미달하였습니다."
    }

    Write-Host "`n🎉 [무결성 통과] 모든 3주차 비동기 부하 테스트 E2E 검증이 100% 성공 완료되었습니다!" -ForegroundColor Green
    Write-Host "성공 기준(50종 업로드, 중복 차단, 롤백 정합성, 성능 메트릭 집계)이 완벽하게 입증되었습니다.`n" -ForegroundColor Green

} catch {
    Write-Error "🚨 통합 테스트 실패: $_"
    Cleanup-Resources
    exit 1
}

# 성공 시에도 최종 자원 격리 소멸 완수
Cleanup-Resources
exit 0

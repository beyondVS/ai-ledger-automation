# =========================================================================
# Windows PowerShell PDF E2E 통합 테스트 러너 (scripts/run-pdf-tests.ps1)
# 헌법 제VI조(대칭 툴링) 및 제VIII조(TestCase 하이브리드) 영구 수호
# =========================================================================

$ErrorActionPreference = "Stop"

$ContainerName = "ai-ledger-db-test"
$VolumeName = "postgres_data_test"
$DbPort = "54321"
$DbName = "ledgerdb_test"
$DbUser = "dbuser_test"
$DbPassword = "dbpassword_test_secure"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🚀 PDF 로컬 통합 E2E 무결성 검증 프로세스를 개시합니다..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Docker 데몬 연결성 확인
$DockerCheck = docker info 2>$null
if ($null -eq $DockerCheck -or $LastExitCode -ne 0) {
    Write-Error "Docker 데몬이 기동되지 않았거나 연결할 수 없습니다. Docker Desktop의 구동 상태를 점검하십시오."
    exit 1
}

# Cleanup 헬퍼 함수 정의 (격리 자원 강제 소멸 및 Cleanup)
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

# 스크립트 실행 중 에러 혹은 강제 중단 시 자원 격리 소멸을 위한 예외 감싸기
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
    # 초기 부팅 안정화 대기
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
    Write-Host "⚙️ [Step 3/4] Django ORM 최신 데이터 물리 스키마 마이그레이션 동기화..." -ForegroundColor Cyan
    $env:DATABASE_URL = "postgresql://${DbUser}:${DbPassword}@localhost:${DbPort}/${DbName}"
    $env:DATABASE_CONN_MAX_AGE = "0" # 테스트 시 커넥션 즉시 해제
    
    # backend 디렉토리 내부 설정을 기동하기 위해 pythonpath 추가
    $env:PYTHONPATH = "backend/src"
    
    uv run python backend/src/manage.py migrate --noinput
    if ($LastExitCode -ne 0) {
        throw "Django 스키마 마이그레이션 실패!"
    }

    # 6. Pytest E2E 통합 테스트 가동
    Write-Host "⚙️ [Step 4/4] Pytest 통합 검증 스위트 기동..." -ForegroundColor Cyan
    uv run pytest backend/tests/integration/test_pdf_integration.py -v
    
    if ($LastExitCode -ne 0) {
        throw "Pytest 통합 검증 실패! 일부 성공 기준(SC-001)에 미달하였습니다."
    }

    Write-Host "`n🎉 [무결성 통과] 모든 1주차 인프라 통합 검증이 100% 성공 완료되었습니다!" -ForegroundColor Green
    Write-Host "성공 기준(SC-001, SC-002, SC-003)이 기계적으로 안전히 입증되었습니다.`n" -ForegroundColor Green

} catch {
    Write-Error "🚨 통합 테스트 실패: $_"
    Cleanup-Resources
    exit 1
}

# 성공 시에도 최종 자원 격리 소멸 완수 (Clean Isolation 수호)
Cleanup-Resources
exit 0

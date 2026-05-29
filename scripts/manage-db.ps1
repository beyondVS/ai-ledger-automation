# =========================================================================
# PostgreSQL v18+ 인프라 통합 컨트롤러 스크립트 (scripts/manage-db.ps1)
# =========================================================================
# [역할 분담 및 차이점]
# 1. scripts/manage-db.ps1 (본 스크립트): RDBMS 물리 엔진(PostgreSQL 18 컨테이너) 자체의 기동, 
#    psql 쿼리 환경 검증(SHOW client_encoding;), 볼륨 영구 파괴(Cleanup) 등 인프라 전용.
# 2. scripts/local-db-controller.ps1: 기동된 DB 상에서 Django 앱 마이그레이션(Migration), 
#    pytest 8종 단위/통합 테스트 기동(Test), 데이터 테이블 플러시 롤백(Reset) 등 백엔드 앱 및 비즈니스 검증 전용.
# =========================================================================
# [사용법]
# 1. 인프라 기동 & 환경 변수 로드 & Named Volume & 정합성 검증까지 원스톱 실행:
#    powershell -ExecutionPolicy Bypass -File scripts/manage-db.ps1
#
# 2. 로컬 도커 인프라 자원 안전 격리 폐기 및 호스트 원복:
#    powershell -ExecutionPolicy Bypass -File scripts/manage-db.ps1 -Cleanup
# =========================================================================

param (
    [switch]$Cleanup
)

$ContainerName = "ai-ledger-db"
$VolumeName = "postgres_data"

# =========================================================================
# 분기 1: -Cleanup 스위치가 지정된 경우 (자원 안전 격리 폐기 및 원복)
# =========================================================================
if ($Cleanup) {
    Write-Host "로컬 인프라 자원 폐기 및 환경 복구를 시작합니다..." -ForegroundColor Cyan

    # 1. PostgreSQL 컨테이너 강제 정지 및 완전 제거
    $ContainerExists = docker ps -a -q -f name="^$ContainerName$"
    if ($ContainerExists) {
        Write-Host "RDBMS 격리 컨테이너 '$ContainerName' 프로세스를 중지하고 소멸시킵니다..." -ForegroundColor Yellow
        docker stop $ContainerName >$null 2>&1
        docker rm $ContainerName >$null 2>&1
        Write-Host "  * [OK] 컨테이너가 정상적으로 완전 폐기되었습니다." -ForegroundColor Green
    } else {
        Write-Host "  * [SKIP] 폐기할 RDBMS 컨테이너 프로세스가 발견되지 않았습니다." -ForegroundColor DarkGray
    }

    # 2. RDBMS Named Volume 물리적 완전 격리 제거
    $VolumeExists = docker volume ls -q -f name="^$VolumeName$"
    if ($VolumeExists) {
        Write-Host "데이터 영속 저장소인 네임드 볼륨 '$VolumeName'을 물리적으로 영구 파괴합니다..." -ForegroundColor Yellow
        docker volume rm $VolumeName >$null 2>&1
        if ($LastExitCode -eq 0) {
             Write-Host "  * [OK] 네임드 볼륨이 흔적 없이 영구 격리 삭제되었습니다." -ForegroundColor Green
        } else {
             Write-Warning "볼륨이 아직 다른 도커 컨테이너에 의해 점유되어 제거할 수 없습니다."
        }
    } else {
        Write-Host "  * [SKIP] 제거할 네임드 볼륨이 발견되지 않았습니다." -ForegroundColor DarkGray
    }

    Write-Host "--------------------------------------------------------" -ForegroundColor Green
    Write-Host "🎉 모든 1일차 인프라 자원이 흔적 없이 완벽히 제거 및 원복되었습니다!" -ForegroundColor Green
    exit 0
}

# =========================================================================
# 분기 2: 기본 실행 흐름 (기동 -> 셋업 -> 볼륨 확보 -> 기계적 검증 E2E)
# =========================================================================
Write-Host "선행 환경 초기화 및 인프라 진단을 시작합니다..." -ForegroundColor Cyan

# 1. .env.local 환경 변수 파싱 및 프로세스 세션 로딩
$EnvFile = Join-Path $PSScriptRoot "..\.env.local"
$ExampleFile = Join-Path $PSScriptRoot "..\.env.local.example"

if (-not (Test-Path $EnvFile)) {
    Write-Warning "'.env.local' 파일이 존재하지 않습니다."
    Write-Host "개발자 템플릿 '.env.local.example'을 복사하여 '.env.local'을 새로 생성합니다..." -ForegroundColor Cyan
    if (Test-Path $ExampleFile) {
        Copy-Item $ExampleFile $EnvFile
        Write-Host "'.env.local' 템플릿 복사 성공!" -ForegroundColor Green
    } else {
        Write-Error "템플릿 파일 '.env.local.example'도 누락되었습니다. 1일차 셋업 요구사항을 확인하십시오."
        exit 1
    }
}

Write-Host "'.env.local' 환경 변수 파싱 및 로드 중..." -ForegroundColor Cyan
Get-Content $EnvFile | ForEach-Object {
    $Line = $_.Trim()
    if ($Line -match "^#" -or [string]::IsNullOrWhiteSpace($Line)) { return }
    if ($Line -like "*=*") {
        $Idx = $Line.IndexOf('=')
        $Key = $Line.Substring(0, $Idx).Trim()
        $Value = $Line.Substring($Idx + 1).Trim()
        if ($Value -like "*#*") {
            $HashIdx = $Value.IndexOf('#')
            $Value = $Value.Substring(0, $HashIdx).Trim()
        }
        if (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or ($Value.StartsWith("'") -and $Value.EndsWith("'"))) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }
        [System.Environment]::SetEnvironmentVariable($Key, $Value, [System.EnvironmentVariableTarget]::Process)
    }
}

# 2. Docker 데몬 연결성 확인
$DockerCheck = docker info 2>$null
if ($null -eq $DockerCheck -or $LastExitCode -ne 0) {
    Write-Error "Docker Desktop 데몬이 기동되지 않았거나 연결할 수 없습니다. Docker Desktop 구동 상태 및 WSL 2 연동을 확인하십시오."
    exit 1
}

# 3. Named Volume 존재 확인 및 생성
$VolumeExists = docker volume ls -q -f name="^$VolumeName$"
if (-not $VolumeExists) {
    Write-Host "네임드 볼륨 '$VolumeName'이 발견되지 않았습니다. 신규 생성을 시도합니다..." -ForegroundColor Cyan
    $CreateResult = docker volume create $VolumeName
    if ($LastExitCode -ne 0) {
        Write-Error "도커 네임드 볼륨 생성에 실패했습니다."
        exit 1
    }
}

# 4. 포트 충돌 방어 및 환경 변수 폴백 가이드라인 준수
$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "ai_ledger" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$DbPassword = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "Secured_Password18!" }
$DbPort = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }

Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "기동 설정을 확인하고 있습니다:" -ForegroundColor Cyan
Write-Host "  * Database Name : $DbName" -ForegroundColor DarkGray
Write-Host "  * DB User       : $DbUser" -ForegroundColor DarkGray
Write-Host "  * Host Port     : $DbPort -> Container Port: 5432" -ForegroundColor DarkGray
Write-Host "  * Volume Mount  : postgres_data -> /var/lib/postgresql" -ForegroundColor DarkGray
Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray

# 5. 기존 동일 컨테이너 존재 시 중지 및 폐기 (멱등성 확보)
$ExistingContainer = docker ps -a -q -f name="^$ContainerName$"
if ($ExistingContainer) {
    Write-Host "기존에 존재하던 '$ContainerName' 컨테이너를 중지하고 폐기합니다..." -ForegroundColor Yellow
    docker stop $ContainerName >$null 2>&1
    docker rm $ContainerName >$null 2>&1
}

# 6. PostgreSQL v18+ Alpine 격리 기동 가동
Write-Host "PostgreSQL v18+ Alpine RDBMS 컨테이너 기동을 시작합니다..." -ForegroundColor Cyan
$RunCommand = docker run -d `
  --name $ContainerName `
  -p "${DbPort}:5432" `
  -v postgres_data:/var/lib/postgresql `
  -e POSTGRES_DB="$DbName" `
  -e POSTGRES_USER="$DbUser" `
  -e POSTGRES_PASSWORD="$DbPassword" `
  -e TZ="Asia/Seoul" `
  --restart unless-stopped `
  postgres:18-alpine `
  -c client_encoding=UTF8 `
  -c timezone=Asia/Seoul

if ($LastExitCode -ne 0) {
    Write-Error "컨테이너 부팅에 실패했습니다. 포트 $DbPort 점유 여부 등을 점검하십시오."
    exit 1
}

# 7. 데이터베이스 환경 정합성 및 무결성 기계적 검증 (SHOW client_encoding & Timezone)
Write-Host "기동 완료 대기 및 환경 정합성 검증 쿼리 송신 중 (3초 후 쿼리 개시)..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

$EncodingCheck = docker exec -i $ContainerName psql -U $DbUser -d $DbName -c "SHOW client_encoding;" 2>$null
$TimezoneCheck = docker exec -i $ContainerName psql -U $DbUser -d $DbName -c "SHOW timezone;" 2>$null

$EncodingPass = $EncodingCheck -match "UTF8"
$TimezonePass = $TimezoneCheck -match "Asia/Seoul"

Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "환경 무결성 정합성 검증 리포트:" -ForegroundColor Cyan
if ($EncodingPass) {
    Write-Host "  * [PASS] 문자셋 인코딩: UTF-8 정상 강제 확인" -ForegroundColor Green
} else {
    Write-Host "  * [FAIL] 문자셋 인코딩: UTF-8 미설정 또는 기타 값 반환" -ForegroundColor Red
}

if ($TimezonePass) {
    Write-Host "  * [PASS] 엔진 시간대  : Asia/Seoul 한국시 확인" -ForegroundColor Green
} else {
    Write-Host "  * [FAIL] 엔진 시간대  : Asia/Seoul 미설정 또는 기타 값 반환" -ForegroundColor Red
}
Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray

if ($EncodingPass -and $TimezonePass) {
    Write-Host "🎉 축하합니다! 통합 인프라 부팅 및 환경 정합성 검증이 100% 성공 완료되었습니다!" -ForegroundColor Green
    Write-Host "성공 기준(SC-001, SC-002, SC-003) 및 헌법 품질 게이트가 완벽히 입증되었습니다." -ForegroundColor Green
    exit 0
} else {
    Write-Error "일부 성공 기준 검증이 실패하였습니다. 컨테이너 셋업 환경을 다시 확인하십시오."
    exit 1
}

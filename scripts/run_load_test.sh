#!/bin/bash
# =========================================================================
# Bash 영수증 부하 테스트 E2E 러너 (scripts/run_load_test.sh)
# 헌법 제VI조(대칭 툴링) 및 제VIII조(TestCase 하이브리드) 영구 수호
# -------------------------------------------------------------------------
# [용도] 3주차 비동기 구조 개편에 따른 Celery 대량 부하 유입 성능 테스트 스크립트 (Linux/Bash)
# [설명] 테스트 전용 격리 DB 컨테이너와 볼륨을 자동 멱등 생성한 뒤,
#        50개 영수증 동시 처리, 중복 결제 검출, 트랜잭션 atomic 롤백 성능을
#        pytest 스위트와 연동하여 진단하고 리포팅을 취합합니다.
# [필수 여부] 필수 (E2E 동시성 및 부하 성능 측정용)
# -------------------------------------------------------------------------
# =========================================================================

set -e

CONTAINER_NAME="ai-ledger-db-loadtest"
VOLUME_NAME="postgres_data_loadtest"
DB_PORT="54322"
DB_NAME="ledgerdb_loadtest"
DB_USER="dbuser_loadtest"
DB_PASSWORD="dbpassword_loadtest_secure"

echo -e "\033[36m========================================================\033[0m"
echo -e "\033[36m🚀 3주차 비동기 영수증 부하 테스트 및 롤백/리포팅 E2E 통합 검증 개시...\033[0m"
echo -e "\033[36m========================================================\033[0m"

# Docker 데몬 연결성 확인
if ! docker info >/dev/null 2>&1; then
    echo -e "\033[31m[ERROR] Docker 데몬이 기동되지 않았거나 연결할 수 없습니다. Docker Desktop의 구동 상태를 점검하십시오.\033[0m"
    exit 1
fi

# Cleanup 헬퍼 함수 정의
cleanup_resources() {
    echo -e "\n\033[33m🧹 [Clean Isolation] 테스트 전용 격리 리소스 회수를 시작합니다...\033[0m"
    
    if docker ps -a -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
        echo -e "  * RDBMS 격리 테스트 컨테이너 '${CONTAINER_NAME}'를 중지 및 소멸시킵니다..."
        docker stop ${CONTAINER_NAME} >/dev/null 2>&1 || true
        docker rm ${CONTAINER_NAME} >/dev/null 2>&1 || true
    fi
    
    if docker volume ls -q -f name="^${VOLUME_NAME}$" | grep -q .; then
        echo -e "  * 격리 테스트 볼륨 '${VOLUME_NAME}'을 물리 삭제합니다..."
        docker volume rm ${VOLUME_NAME} >/dev/null 2>&1 || true
    fi
    echo -e "\033[32m✨ [Cleanup OK] 로컬 시스템이 완벽하게 멱등 격리 소멸되었습니다!\033[0m\n"
}

# 에러 혹은 시그널 수신 시 자원 자동 격리 Cleanup을 위한 trap 설정
trap cleanup_resources EXIT ERR INT TERM

# 1. 기존 동일 테스트 컨테이너/볼륨 청소
if docker ps -a -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo -e "\033[33m기존에 미회수된 '${CONTAINER_NAME}' 테스트 자원을 선제 정리합니다...\033[0m"
    docker stop ${CONTAINER_NAME} >/dev/null 2>&1 || true
    docker rm ${CONTAINER_NAME} >/dev/null 2>&1 || true
fi
if docker volume ls -q -f name="^${VOLUME_NAME}$" | grep -q .; then
    docker volume rm ${VOLUME_NAME} >/dev/null 2>&1 || true
fi

# 2. 격리 테스트 볼륨 생성
docker volume create ${VOLUME_NAME} >/dev/null

# 3. PostgreSQL v18 Test 전용 독립 인프라 기동
echo -e "\033[36m⚙️ [Step 1/4] PostgreSQL 18 격리 테스트 DB 컨테이너 부팅 중 (Port ${DB_PORT})...\033[0m"
docker run -d \
  --name ${CONTAINER_NAME} \
  -p "${DB_PORT}:5432" \
  -v "${VOLUME_NAME}:/var/lib/postgresql" \
  -e POSTGRES_DB="${DB_NAME}" \
  -e POSTGRES_USER="${DB_USER}" \
  -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
  -e TZ="Asia/Seoul" \
  postgres:18-alpine \
  -c client_encoding=UTF8 \
  -c timezone=Asia/Seoul

# 4. 포트 헬스체크 및 기동 대기
echo -e "\033[36m⚙️ [Step 2/4] DB 엔진 포트 바인딩 및 헬스 체크 폴링 중...\033[0m"
sleep 2
retries=10
db_ready=false
while [ ${retries} -gt 0 ]; do
    if docker exec -i ${CONTAINER_NAME} psql -h 127.0.0.1 -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1;" >/dev/null 2>&1; then
        db_ready=true
        break
    fi
    retries=$((retries - 1))
    echo -e "  * DB 대기 중... (남은 시도: ${retries})"
    sleep 1
done

if [ "${db_ready}" = "false" ]; then
    echo -e "\033[31m[ERROR] 테스트 데이터베이스 기동 대기 시간 초과(Timeout).\033[0m"
    exit 1
fi
echo -e "\033[32m  * [PASS] 테스트용 DB 정합성 헬스 체크 통과!\033[0m"

# 5. 환경 변수 동적 주입 및 Django 마이그레이션 기동
echo -e "\033[36m⚙️ [Step 3/4] Django ORM 최신 데이터 물리 스키마 마이그레이션 동기화...\033[0m"
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}"
export DATABASE_CONN_MAX_AGE="0"
export PYTHONPATH="backend/src"

uv run python backend/src/manage.py migrate --noinput

# 6. Pytest E2E 통합 테스트 및 리포팅 가동
echo -e "\033[36m⚙️ [Step 4/4] Pytest 부하 테스트 및 리포팅 검증 스위트 기동...\033[0m"
uv run pytest backend/tests/ledgers/test_load_testing.py -v -s

echo -e "\n\033[32m🎉 [무결성 통과] 모든 3주차 비동기 부하 테스트 E2E 검증이 100% 성공 완료되었습니다!\033[0m"
echo -e "\033[32m성공 기준(50종 업로드, 중복 차단, 롤백 정합성, 성능 메트릭 집계)이 완벽하게 입증되었습니다.\033[0m\n"

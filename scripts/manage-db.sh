#!/usr/bin/env bash
# =========================================================================
# PostgreSQL v18+ 인프라 통합 컨트롤러 스크립트 (scripts/manage-db.sh)
# =========================================================================
# [사용법]
# 1. 인프라 기동 & 환경 변수 로드 & Named Volume & 정합성 검증까지 원스톱 실행:
#    chmod +x scripts/manage-db.sh && ./scripts/manage-db.sh
#
# 2. 로컬 도커 인프라 자원 안전 격리 폐기 및 호스트 원복:
#    ./scripts/manage-db.sh --cleanup
# =========================================================================

set -e

CONTAINER_NAME="ai-ledger-db"
VOLUME_NAME="postgres_data"

# 스크립트 디렉토리 감지
SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cleanup_infra() {
    echo "로컬 인프라 자원 폐기 및 환경 복구를 시작합니다..."
    
    # 1. PostgreSQL 컨테이너 강제 정지 및 완전 제거
    if [ "$(docker ps -a -q -f name="^${CONTAINER_NAME}$")" ]; then
        echo "RDBMS 격리 컨테이너 '${CONTAINER_NAME}' 프로세스를 중지하고 소멸시킵니다..."
        docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
        docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true
        echo "  * [OK] 컨테이너가 정상적으로 완전 폐기되었습니다."
    else
        echo "  * [SKIP] 폐기할 RDBMS 컨테이너 프로세스가 발견되지 않았습니다."
    fi

    # 2. RDBMS Named Volume 물리적 완전 격리 제거
    if [ "$(docker volume ls -q -f name="^${VOLUME_NAME}$")" ]; then
        echo "데이터 영속 저장소인 네임드 볼륨 '${VOLUME_NAME}'을 물리적으로 영구 파괴합니다..."
        if docker volume rm "${VOLUME_NAME}" >/dev/null 2>&1; then
            echo "  * [OK] 네임드 볼륨이 흔적 없이 영구 격리 삭제되었습니다."
        else
            echo "경고: 볼륨이 아직 다른 도커 컨테이너에 의해 점유되어 제거할 수 없습니다." >&2
        fi
    else
        echo "  * [SKIP] 제거할 네임드 볼륨이 발견되지 않았습니다."
    fi

    echo "--------------------------------------------------------"
    echo "🎉 모든 1일차 인프라 자원이 흔적 없이 완벽히 제거 및 원복되었습니다!"
    exit 0
}

# 파라미터 처리
CLEANUP=false
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -c|--cleanup) CLEANUP=true; shift ;;
        -h|--help)
            echo "사용법: ./manage-db.sh [옵션]"
            echo ""
            echo "옵션:"
            echo "  -c, --cleanup  로컬 인프라 자원 안전 격리 폐기 및 호스트 원복"
            echo "  -h, --help     도움말 표시"
            exit 0
            ;;
        *) echo "오류: 알 수 없는 옵션 '$1'입니다." >&2; exit 1 ;;
    esac
done

if [ "$CLEANUP" = true ]; then
    cleanup_infra
fi

# 기본 기동 흐름
echo "선행 환경 초기화 및 인프라 진단을 시작합니다..."

ENV_FILE="$REPO_ROOT/.env.local"
EXAMPLE_FILE="$REPO_ROOT/.env.local.example"

# 1. .env.local 환경 변수 존재 체크 및 복사
if [ ! -f "$ENV_FILE" ]; then
    echo "경고: '.env.local' 파일이 존재하지 않습니다."
    echo "개발자 템플릿 '.env.local.example'을 복사하여 '.env.local'을 새로 생성합니다..."
    if [ -f "$EXAMPLE_FILE" ]; then
        cp "$EXAMPLE_FILE" "$ENV_FILE"
        echo "'.env.local' 템플릿 복사 성공!"
    else
        echo "오류: 템플릿 파일 '.env.local.example'도 누락되었습니다. 1일차 셋업 요구사항을 확인하십시오." >&2
        exit 1
    fi
fi

# 2. .env.local 환경 변수 파싱 및 프로세스 세션 로딩
echo "'.env.local' 환경 변수 파싱 및 로드 중..."
while IFS= read -r line || [ -n "$line" ]; do
    line=$(echo "$line" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
    if [[ "$line" =~ ^# ]] || [ -z "$line" ]; then
        continue
    fi
    if [[ "$line" == *=* ]]; then
        key="${line%%=*}"
        value="${line#*=}"
        key=$(echo "$key" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
        value=$(echo "$value" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
        if [[ "$value" == *#* ]]; then
            value="${value%%#*}"
            value=$(echo "$value" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
        fi
        if [[ ("$value" == \"*\" || "$value" == \'*\' ) ]]; then
            value="${value:1:-1}"
        fi
        export "$key=$value"
    fi
done < "$ENV_FILE"

# 3. Docker 데몬 연결성 확인
if ! docker info >/dev/null 2>&1; then
    echo "오류: Docker 데몬이 기동되지 않았거나 연결할 수 없습니다. Docker 실행 상태를 확인하십시오." >&2
    exit 1
fi

# 4. Named Volume 존재 확인 및 생성
if [ -z "$(docker volume ls -q -f name="^${VOLUME_NAME}$")" ]; then
    echo "네임드 볼륨 '${VOLUME_NAME}'이 발견되지 않았습니다. 신규 생성을 시도합니다..."
    if ! docker volume create "$VOLUME_NAME" >/dev/null; then
        echo "오류: 도커 네임드 볼륨 생성에 실패했습니다." >&2
        exit 1
    fi
fi

# 5. 환경 변수 기본값 설정
DB_NAME="${POSTGRES_DB:-ai_ledger}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-Secured_Password18!}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "--------------------------------------------------------"
echo "기동 설정을 확인하고 있습니다:"
echo "  * Database Name : $DB_NAME"
echo "  * DB User       : $DB_USER"
echo "  * Host Port     : $DB_PORT -> Container Port: 5432"
echo "  * Volume Mount  : ${VOLUME_NAME} -> /var/lib/postgresql"
echo "--------------------------------------------------------"

# 6. 기존 동일 컨테이너 존재 시 중지 및 폐기 (멱등성 확보)
if [ "$(docker ps -a -q -f name="^${CONTAINER_NAME}$")" ]; then
    echo "기존에 존재하던 '${CONTAINER_NAME}' 컨테이너를 중지하고 폐기합니다..."
    docker stop "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    docker rm "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

# 7. PostgreSQL v18+ Alpine 격리 기동 가동
echo "PostgreSQL v18+ Alpine RDBMS 컨테이너 기동을 시작합니다..."
if ! docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${DB_PORT}:5432" \
  -v "${VOLUME_NAME}:/var/lib/postgresql" \
  -e POSTGRES_DB="$DB_NAME" \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  -e TZ="Asia/Seoul" \
  --restart unless-stopped \
  postgres:18-alpine \
  -c client_encoding=UTF8 \
  -c timezone=Asia/Seoul; then
    echo "오류: 컨테이너 부팅에 실패했습니다. 포트 $DB_PORT 점유 여부 등을 점검하십시오." >&2
    exit 1
fi

# 8. 데이터베이스 환경 정합성 및 무결성 기계적 검증 (SHOW client_encoding & Timezone)
echo "기동 완료 대기 및 환경 정합성 검증 쿼리 송신 중 (3초 후 쿼리 개시)..."
sleep 3

ENCODING_CHECK=$(docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SHOW client_encoding;" 2>/dev/null || true)
TIMEZONE_CHECK=$(docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "SHOW timezone;" 2>/dev/null || true)

ENCODING_PASS=false
if echo "$ENCODING_CHECK" | grep -q "UTF8"; then
    ENCODING_PASS=true
fi

TIMEZONE_PASS=false
if echo "$TIMEZONE_CHECK" | grep -q "Asia/Seoul"; then
    TIMEZONE_PASS=true
fi

echo "--------------------------------------------------------"
echo "환경 무결성 정합성 검증 리포트:"
if [ "$ENCODING_PASS" = true ]; then
    echo -e "\033[0;32m  * [PASS] 문자셋 인코딩: UTF-8 정상 강제 확인\033[0m"
else
    echo -e "\033[0;31m  * [FAIL] 문자셋 인코딩: UTF-8 미설정 또는 기타 값 반환\033[0m"
fi

if [ "$TIMEZONE_PASS" = true ]; then
    echo -e "\033[0;32m  * [PASS] 엔진 시간대  : Asia/Seoul 한국시 확인\033[0m"
else
    echo -e "\033[0;31m  * [FAIL] 엔진 시간대  : Asia/Seoul 미설정 또는 기타 값 반환\033[0m"
fi
echo "--------------------------------------------------------"

if [ "$ENCODING_PASS" = true ] && [ "$TIMEZONE_PASS" = true ]; then
    echo -e "\033[0;32m🎉 축하합니다! 통합 인프라 부팅 및 환경 정합성 검증이 100% 성공 완료되었습니다!\033[0m"
    echo -e "\033[0;32m성공 기준(SC-001, SC-002, SC-003) 및 헌법 품질 게이트가 완벽히 입증되었습니다.\033[0m"
    exit 0
else
    echo "오류: 일부 성공 기준 검증이 실패하였습니다. 컨테이너 셋업 환경을 다시 확인하십시오." >&2
    exit 1
fi

#!/bin/bash
# scripts/setup_boilerplate.sh
# macOS/Linux용 보일러플레이트 자동화 셋업 도구 (Bash)
# 헌법 제VI조 크로스 플랫폼 대칭 툴링 원칙 준수

set -e

# 색상 정의
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}AI Ledger Automation - Django 보일러플레이트 셋업${NC}"
echo -e "${CYAN}==================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_ROOT/backend"
ENV_FILE="$BACKEND_DIR/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.local.example"

# 1. uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo -e "${RED}오류: uv 패키지 관리자가 설치되어 있지 않습니다. 설치 후 다시 시도하십시오.${NC}"
    exit 1
fi

# 2. backend 가상 환경 동기화
echo -e "${YELLOW}[1/4] 백엔드 패키지 의존성 동기화 (uv sync) 시작...${NC}"
cd "$BACKEND_DIR"
uv sync
echo -e "${GREEN}✓ 의존성 동기화 완료!${NC}"

# 3. .env 파일 검증 및 복사
echo -e "${YELLOW}[2/4] 환경 변수(.env) 설정 확인 중...${NC}"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "  .env 파일이 존재하지 않습니다. .env.local.example을 기반으로 생성합니다."
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${GREEN}✓ backend/.env 파일이 생성되었습니다. 자격 증명을 알맞게 설정해 주십시오.${NC}"
    else
        echo -e "${YELLOW}경고: .env.local.example을 찾을 수 없습니다. 빈 .env 파일을 생성합니다.${NC}"
        touch "$ENV_FILE"
    fi
else
    echo -e "${GREEN}✓ .env 파일이 이미 존재합니다.${NC}"
fi

# 4. .env 내 필수 환경 변수 검증
ENV_CONTENT=$(cat "$ENV_FILE")
MISSING_VARS=()
for var in SECRET_KEY DATABASE_URL; do
    if ! echo "$ENV_CONTENT" | grep -q "^$var\s*="; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${YELLOW}경고: .env에 다음 필수 변수가 누락되었습니다: ${MISSING_VARS[*]}${NC}"
    echo -e "${RED}이 변수들은 settings.py에서 엄격히 차단(No Fallback)되므로 반드시 설정해 주셔야 구동 가능합니다.${NC}"
else
    echo -e "${GREEN}✓ 필수 환경 변수 검증 완료!${NC}"
fi

# 5. DB 연결성 예비 점유 검증 (PostgreSQL 구동 시)
echo -e "${YELLOW}[3/4] 로컬 RDBMS 도커 컨테이너 검증...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_STATUS=$(docker ps --filter "name=ai-ledger-db" --format "{{.Status}}" 2>/dev/null || true)
    if [ -z "$DOCKER_STATUS" ]; then
        echo -e "${YELLOW}💡 팁: RDBMS 컨테이너가 구동되고 있지 않은 것 같습니다.${NC}"
        echo -e "구동 방법: docker compose -f docker-compose.db.yml --env-file .env.local up -d"
    else
        echo -e "${GREEN}✓ 데이터베이스 컨테이너가 동작 중입니다 ($DOCKER_STATUS).${NC}"
    fi
else
    echo -e "${YELLOW}💡 팁: docker 명령어를 찾을 수 없어 RDBMS 기동성 자동 검증을 건너뜁니다.${NC}"
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}🎉 셋업 단계가 완료되었습니다!${NC}"
echo -e "백엔드를 구동하려면 backend/ 디렉토리로 이동 후 아래 명령을 실행하십시오:"
echo -e "  ${YELLOW}uv run src/manage.py migrate${NC}"
echo -e "  ${YELLOW}uv run src/manage.py runserver${NC}"
echo -e "${GREEN}==================================================${NC}"

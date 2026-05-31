# Quickstart Guide: django-initial-setup

본 가이드는 Python 및 Django 웹 애플리케이션 보일러플레이트 코드를 로컬 환경에서 셋업하고, 안전하게 가동 및 진단하기 위한 퀵스타트 매뉴얼입니다.

---

## 1. 사전 요구사항 (Prerequisites)

- **Python 3.11** 설치 완료
- **uv** 패키지 관리자 설치 완료 (의존성 및 격리 가상환경 통제용)
- **Docker & Docker Compose** 기동 가능 상태 (PostgreSQL v18+ 인프라 구동용)

---

## 2. 대칭형 자동화 셋업 스크립트 실행 (Symmetric Tooling)

헌법 제VI조(크로스 플랫폼 대칭 툴링)에 의거하여, 복잡한 개발 가상환경 셋업 및 패키지 동기화를 한 번에 해결하는 이중 대칭형 자동화 스크립트가 `scripts/` 디렉토리 하위에 준비되어 있습니다. 자신의 OS 환경에 맞는 스크립트를 기동하십시오.

### 2.1 Windows (PowerShell 5.1+) 환경
프로젝트 루트에서 관리자 권한으로 아래 명령을 실행합니다:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\scripts\setup_boilerplate.ps1
```

### 2.2 macOS / Linux / WSL (Bash) 환경
프로젝트 루트에서 아래 권한 부여 및 명령을 실행합니다:
```bash
chmod +x ./scripts/setup_boilerplate.sh
./scripts/setup_boilerplate.sh
```

*(자동화 스크립트의 작동 내부 프로세스: `.venv` 자동 구축 -> `uv sync` 의존성 완전 동기화 -> `.env.local` 템플릿 복사 및 복합 정합성 검증 완수)*

---

## 3. 수동 환경 설정 및 가동 절차 (Manual Setup)

자동화 셋업을 수동으로 순차 수행하고자 할 시 아래 단계를 밟습니다.

### 3.1 백엔드 패키지 의존성 선언적 동기화
`backend/` 디렉토리로 진입한 후, `uv`를 가동해 `pyproject.toml`에 명세된 의존성 패키지(environ, restframework, cors-headers, psycopg)를 격리된 가상환경에 동기화합니다.
```bash
# backend 디렉토리 하위에서 실행
uv sync
```

### 3.2 로컬 개발용 `.env` 환경 변수 파일 셋업
보안 절대 하드코딩 금지 원칙(FR-004)에 따라, 루트의 `.env.local.example` 또는 가이드를 참고하여 `backend/.env` 파일을 신규 생성하고 아래 자격 증명을 올바르게 정의합니다. 

> [!CAUTION]
> settings.py 내부에 기본 폴백 값을 매핑해두지 않았으므로(No Fallback), 반드시 필수 환경 변수들을 완전히 기입해주어야 서버가 안전하게 구동됩니다.

```ini
# backend/.env
SECRET_KEY=Generating_A_Highly_Secure_Random_Entropy_Key_Here_Minimum_50_Chars
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# PostgreSQL v18+ 연동 주소 (psycopg3 드라이버 바인딩)
DATABASE_URL=postgres://postgres:Secured_Password18!@localhost:5432/ai_ledger

# Supabase 무료 티어 고갈 방지를 위한 커넥션 나이 스로틀링 (기본 60초)
DATABASE_CONN_MAX_AGE=60
```

### 3.3 로컬 RDBMS 데이터베이스 기동
프로젝트 루트에서 제공되는 도커 컴포즈 RDBMS 명세 스크립트를 기동합니다:
```bash
# 프로젝트 루트에서 실행
docker compose -f docker-compose.db.yml --env-file .env.local up -d
```

### 3.4 데이터베이스 초기 마이그레이션 수행
데이터베이스 인프라가 완전히 구동되었으면, 가상환경을 통해 마이그레이션을 속행합니다:
```bash
# backend/ 디렉토리 하위에서 실행
uv run src/manage.py migrate
```

### 3.5 로컬 개발 웹 서버 구동
백엔드 보일러플레이트 구동 명령을 내려 기동을 개시합니다:
```bash
# backend/ 디렉토리 하위에서 실행
uv run src/manage.py runserver
```

---

## 4. 로컬 헬스 체커 진단 검증

서버가 3초 이내에 정상 기동 완료(SC-001)되면, 브라우저 또는 CLI Curl을 통해 비인증 헬스체크 계약 엔드포인트 `/api/health/`에 접근하여 시스템 구동 상태를 입증합니다:

```bash
curl -X GET http://localhost:8000/api/health/
```

성공 응답으로 `{"status":"healthy", "services":{"django":"up","database":"up"}}`을 획득하면 완벽하게 보일러플레이트 셋업 및 DB 연동 구축이 완료된 상태입니다.

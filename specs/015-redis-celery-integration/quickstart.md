# Developer Quickstart: Asynchronous Celery & Redis Setup

본 문서에서는 개발자가 로컬 Docker Compose 환경과 파이썬 런타임 환경에서 Redis 브로커, Celery 워커, Flower 대시보드 및 Django 메인 서버를 기동하고 테스트하기 위한 퀵스타트 가이드를 제공합니다.

---

## 1. 전제 조건 및 환경 설정 (Prerequisites)

패키지 관리 및 가상 환경 정합성 수호를 위해 `uv` 도구를 필수로 사용합니다.

```bash
# 1. 백엔드 가상 환경 의존성 동기화
cd backend
uv sync

# 2. 로컬 환경 변수 (.env) 설정 확인
# Redis 브로커 URL 및 데이터베이스 커넥션 설정이 올바른지 확인하십시오.
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## 2. Docker Compose 인프라 기동

로컬 디버깅 및 DB/브로커 실행을 위해 Docker Compose 컨테이너를 가동합니다.

```bash
# RDBMS(PostgreSQL) 및 Redis 브로커 기동
docker compose -f docker-compose.db.yml up -d
```

*동작 확인:*
- **PostgreSQL**: `localhost:5432` 대기 확인.
- **Redis Broker**: `localhost:6379` 대기 확인.

---

## 3. 로컬 백엔드 서버 및 워커 기동 (개발 환경)

터미널을 여러 개 기동하여 각각 메인 API 서버와 워커 프로세스를 수동 가동합니다.

### 3.1 Django API 메인 서버 가동 (Terminal 1)
```bash
cd backend
uv run src/manage.py runserver 0.0.0.0:8000
```

### 3.2 Celery 백그라운드 워커 가동 (Terminal 2)
```bash
cd backend
# 헌법의 DB 커넥션 8개 이하 유지 제약을 위해 worker concurrency는 2 이하로 제약합니다.
uv run celery -A config worker --workdir src --loglevel=info --concurrency=2
```

### 3.3 Flower 모니터링 대시보드 가동 (Terminal 3)
```bash
cd backend
uv run celery -A config flower --workdir src --port=5555
```
* **Flower 주소**: [http://localhost:5555](http://localhost:5555) 에 접속하여 백그라운드 큐 현황을 관리할 수 있습니다.

---

## 4. 크로스 플랫폼 대칭 기동 스크립트 가동 (헌법 제VI조 준수)

수동 기동 과정을 일괄 자동화하기 위해 `scripts/` 디렉토리 하위에 대칭적으로 작성되는 통합 실행 스크립트를 사용할 수 있습니다.

### Windows (PowerShell)
```powershell
# Redis 브로커, Django, Celery, Flower 통합 백그라운드 기동
.\scripts\start-async-dev.ps1
```

### macOS / Linux (Bash)
```bash
# 실행 권한 부여 후 실행
chmod +x ./scripts/start-async-dev.sh
./scripts/start-async-dev.sh
```

---

## 5. 기계적 테스트 실행 (헌법 제VIII조 준수)

비동기 작업 API 및 Celery 태스크 통합 테스트 코드를 실행하여 정합성을 입증합니다.

```bash
cd backend
# pytest를 활용해 백엔드 비동기 연산 테스트 기동
uv run pytest tests/apps/ledgers/test_async_jobs.py -v
```
- DB가 연계된 테스트는 내부적으로 `django.test.TestCase`를 상속하여 DB 트랜잭션 격리 혜택을 받으며 기계적으로 완수됩니다.

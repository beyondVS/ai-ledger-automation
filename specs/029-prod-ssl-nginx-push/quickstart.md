# Quickstart Guide: Production SSL & E2E Notification Release

**Feature**: `029-prod-ssl-nginx-push`

## 1. Production Docker-Compose Deployment

실 서버 인프라의 SSL Offloading 및 포트 격리 환경을 로컬 모의 프로덕션 단계에서 실행하고 검증하기 위한 절차입니다.

### 1.1 환경 변수 (.env) 검증 및 주입
실행하기 전, 프로젝트 루트 디렉토리에 `.env` 파일이 올바르게 생성되고 아래의 VAPID 및 프로덕션 설정이 들어있는지 확인합니다.
```env
DEBUG=False
SECRET_KEY=prod-secret-key-change-this
POSTGRES_DB=ai_ledger
POSTGRES_USER=postgres
POSTGRES_PASSWORD=prod-secure-password
DATABASE_URL=postgres://postgres:prod-secure-password@postgres-db:5432/ai_ledger
REDIS_URL=redis://redis-broker:6379/0

# VAPID Keys for Web Push
VAPID_PUBLIC_KEY=BGxxxx...
VAPID_PRIVATE_KEY=xxxx...
VAPID_ADMIN_EMAIL=admin@example.com
```

### 1.2 컨테이너 기동
프로덕션 전용 Compose 파일과 격리 네트워크 명세를 사용하여 백그라운드로 전체 스택을 가동합니다.
```bash
# Docker Compose 릴리즈 기동
docker compose -f docker-compose.prod.yml up -d --build
```
- Nginx, API Server, Celery Worker, Redis, PostgreSQL이 단일 `prod-bridge` 내부 격리망에서 실행되며, 오직 Nginx의 80 포트만 외부로 노출됩니다.

---

## 2. Manual Verification & Test Push Execution

배포된 프로덕션 알림 파이프라인이 E2E로 정상 작동하는지 확인하는 명령 실행법입니다.

### 2.1 E2E 알림 테스트 스크립트 실행
프로젝트 루트의 `scripts/` 디렉토리에 배치된 E2E 알림 검증 스크립트를 기동합니다.
- **PowerShell (Windows)**:
  ```powershell
  ./scripts/run_e2e_push_test.ps1 -TargetUrl "http://localhost:80"
  ```
- **Bash (Linux/macOS)**:
  ```bash
  ./scripts/run_e2e_push_test.sh --target-url "http://localhost:80"
  ```
이 스크립트는 내부적으로 DB에 임시 mock 사용자와 구독 정보를 파퓰레이트(Seeding)하고, Celery 백그라운드로 웹푸시 메시지를 강제 발송한 뒤, Nginx 리프레시와 IndexedDB 수신 결과를 원자적으로 검증합니다.

---

## 3. Infrastructure Integrity Check

포트 보안 및 컨테이너 고가용성 제한 설정이 정상 적용되었는지 CLI 상에서 확인하는 방법입니다.

### 3.1 호스트 바인딩 포트 노출 확인
호스트 장비의 모든 오픈된 포트를 스캔하여 PostgreSQL(5432)과 Redis(6379)가 호스트에 노출되지 않았는지 검증합니다.
```bash
# 포트 5432 또는 6379 노출 탐색 (아무것도 나오지 않아야 정상)
netstat -an | findstr "5432"
netstat -an | findstr "6379"
```

### 3.2 컨테이너 리소스 제한 확인
가동 중인 API 서버와 Celery 워커의 CPU/메모리 한도가 정상 반영되었는지 컨테이너 메타데이터를 질의합니다.
```bash
# api-server 리소스 제한 검증
docker inspect --format='{{.HostConfig.CpuPercent}}' api-server
docker inspect --format='{{.HostConfig.Memory}}' api-server
```

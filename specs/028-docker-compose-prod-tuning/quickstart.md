# Quickstart: Production Deployment & Verification Guide

본 문서는 `docker-compose.prod.yml` 환경 설정을 기반으로 프로덕션 서비스를 배포하고, 튜닝 설정 및 포트 보안 접근 제어 상태를 신속히 검증하기 위한 가이드라인입니다.

---

## 1. 프로덕션 서비스 구동 방법 (Deployment)

실 서비스 환경에서 튜닝 사양이 적용된 서비스를 기동하려면 아래 명령어를 순서대로 터미널에서 실행합니다.

```bash
# 1. 프로덕션용 환경 변수 설정 파일 (.env.prod) 생성 및 크리덴셜 주입 완료 확인
# 2. 프로덕션 컴포즈 스택 백그라운드 구동
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 2. 보안 및 포트 제어 기계적 검증 (Security Verification)

포트 노출 차단 계약이 정상 작동하여 외부에서 직접 접근할 수 없는지 기계적으로 검사합니다.

### 2.1 외부 IP 포트 스캔 (호스트 외부에서 검사)
외부 개발 PC 또는 원격 테스트 인스턴스에서 배포 대상 서버의 공인 IP(`[SERVER_PUBLIC_IP]`)를 상대로 포트 스캔을 수행합니다.

```bash
# nmap을 사용하여 80, 443 이외의 포트가 closed/filtered 상태인지 확인
nmap -p 80,443,5432,6379,8000 [SERVER_PUBLIC_IP]
```

**예상 결과**:
* `80/tcp open http`
* `443/tcp open https`
* `5432/tcp filtered postgresql`
* `6379/tcp filtered redis`
* `8000/tcp filtered mc-nm-srvr`

---

## 3. 리소스 한도 및 로그 로테이션 검증 (Resource & Log Verification)

### 3.1 컨테이너별 자원 사용 모니터링
컴포즈에 설정된 CPU/메모리 한도값이 실제로 운영체제 레벨에서 격리 적용되었는지 확인합니다.

```bash
# 컨테이너 자원 사용 실시간 스트리밍 모니터링
docker stats
```

**예상 결과**:
`LIMIT` 컬럼에 각 서비스별로 설정된 절대 메모리 용량(예: api-server의 경우 `1GiB`, postgres_db의 경우 `2GiB` 등)이 올바르게 나타나야 합니다.

### 3.2 로그 로테이션 적용 상태 확인
도커 엔진 내부에서 로그 용량이 10MB 상한선에 맞춰 관리되고 있는지 물리 파일을 확인합니다.

```bash
# 특정 컨테이너의 로그 파일 물리적 경로 및 용량 조회 (호스트 OS 루트 권한 필요)
docker inspect --format='{{.LogPath}}' [CONTAINER_NAME_OR_ID]
```
해당 경로에서 로그 파일이 `*.log` 외에 `*.log.1`, `*.log.2` 등으로 분할 로테이션되며 총 크기가 30MB 이하로 유지되는지 관측합니다.

---

## 4. 장애 모의 헬스체크 검증 (Healthcheck Mocking)

api-server의 헬스체크 프로세스가 컨테이너 비정상 상태를 정상 식별하는지 강제 모의합니다.

```bash
# 백엔드 컨테이너의 상태 조회
docker compose -f docker-compose.prod.yml ps

# api-server의 헬스체크가 healthy인지 확인
# 강제로 컨테이너 내부 8000번 포트를 일시 중단하거나 mock 응답을 에러로 변경 시,
# 30초 내에 unhealthy로 감지되어 docker compose가 컨테이너를 재기동시킵니다.
```

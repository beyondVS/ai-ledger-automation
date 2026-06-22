# Production Infrastructure Tuning & Management Guide

본 문서는 `docker-compose.prod.yml` 기반의 프로덕션 도커 인프라의 기동 방법, 자원 설정 조절 가이드라인, 그리고 데이터 백업 및 복구 절차를 설명하는 실무 매뉴얼입니다.

---

## 1. 서비스 기동 및 중지 (Lifecycle Management)

프로덕션 최적화 인프라 스택을 관리하기 위한 핵심 명령어 모음입니다.

```bash
# 1. 프로덕션 서비스 백그라운드 기동 및 빌드
docker compose -f docker-compose.prod.yml up -d --build

# 2. 기동 상태 및 서비스 정상 상태(healthy) 모니터링
docker compose -f docker-compose.prod.yml ps

# 3. 서비스 정지 및 컨테이너 리소스 정리
docker compose -f docker-compose.prod.yml down
```

---

## 2. 자원 할당 사양 조절 가이드 (Resource Scaling Policy)

배포 대상 물리 서버의 스펙(vCPU 및 RAM 용량)에 따라 개별 컨테이너 서비스의 자원 한계를 재배정하려면 `docker-compose.prod.yml` 내의 `deploy.resources` 지시문을 편집해야 합니다.

### 2.1 자원 조절 시 주의 요건 (Constraints)
* **결정론적 고정(Hardcoded Limit)**: 자원 안정성(OOM 방지)을 위해 자원 한도값은 환경 변수 바인딩 대신 컴포즈 파일에 고정된 절대 용량으로 직접 기입해 주어야 합니다 (TDD 검증 준수).
* **스펙 배분 권장 매트릭**:
  * 소형 서버 (2 vCPU, 4GB RAM): DB limits(1 vCPU, 1G RAM), API limits(0.5 vCPU, 512M RAM) 등으로 낮춰서 기입.
  * 중형 서버 (4 vCPU, 8GB RAM): DB limits(2 vCPU, 2G RAM), API limits(1 vCPU, 1G RAM)의 현재 설정 적합.

---

## 3. PostgreSQL 데이터 백업 및 복구 절차 (Named Volume Backup/Restore)

PostgreSQL은 도커 Named Volume (`postgres_data`)을 통해 영속 보관되고 있으므로, 데이터 안전 관리를 위해 컨테이너 내부 pg_dump 유틸리티를 경유하여 백업을 처리합니다.

### 3.1 논리적 데이터 백업 (Logical Backup)
도커 컨테이너가 정상 구동 중인 상태에서 데이터베이스의 전체 스키마 및 레코드를 물리 SQL 덤프 파일로 유출합니다.

```bash
# 1. 데이터베이스 전체 SQL 덤프 수행 (비동기 및 동기 가계부 레코드 통합)
docker exec -t ai-ledger-prod-db pg_dumpall -U postgres > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 덤프 파일 압축 보관 (디스크 절약)
gzip backup_*.sql
```

### 3.2 논리적 데이터 복구 (Logical Restore)
서버 장애 복구 시 또는 신규 호스트 이관 시 덤프된 백업 파일을 컴포즈 컨테이너 내부로 재주입하여 데이터베이스를 완벽히 재구축합니다.

```bash
# 1. 대상 덤프 파일 압축 해제
gunzip backup_2026xxxx_xxxxxx.sql.gz

# 2. 덤프 파일을 활성 postgres_db 컨테이너 내 psql 실행기에 직접 주입하여 스키마/데이터 복구
cat backup_2026xxxx_xxxxxx.sql | docker exec -i ai-ledger-prod-db psql -U postgres
```

---

## 4. 로깅 데이터 디스크 점유 용량 점검

로그 무제한 증식을 방지하는 `max-size: 10m` 및 `max-file: 3` 계약에 따라 개별 컨테이너가 총 30MB의 디스크 점유율을 초과하지 않는지 운영 환경에서 실시간 확인합니다.

```bash
# 컨테이너 로그 경로 확인
LOG_PATH=$(docker inspect --format='{{.LogPath}}' ai-ledger-prod-db)

# 로그 파일의 현재 용량 조회
du -sh $LOG_PATH
```

# Quickstart Guide: Django Model Migration & DB Testing

본 가이드는 6대 Django Model 설계를 기반으로 데이터베이스 마이그레이션을 신속하게 적용하고, PostgreSQL v18 연결 및 모델 동작 정합성을 로컬 테스트 스위트 상에서 검증하기 위한 실질적인 가동 명령어를 정리합니다.

헌법 제VI조(크로스 플랫폼 대칭 툴링)에 따라, Windows PowerShell 환경과 macOS/Linux Bash 환경의 동등 툴링을 지원합니다.

---

## 1. 사전 필수 요건 (Prerequisites)

- **Python 3.11** 및 패키지 관리자 **uv** 설치 완료
- **Docker Compose** 가동 환경 구비 (PostgreSQL v18+ 및 Redis 구동용)
- **로컬 환경 변수 설정**: `.env.local` 파일 구성

---

## 2. 데이터베이스 컨테이너 구동 (DB Spin-up)

데이터 보존 레이어와 비동기 큐를 로컬에 기동합니다.
```bash
# Docker Compose 백그라운드 기동
docker compose up -d postgres_db redis_broker
```

---

## 3. 크로스 플랫폼 데이터베이스 기동 스크립트 (Cross-platform DB Tooling)

데이터베이스 마이그레이션, 초기 셋업 및 테스트 데이터 초기화는 헌법 제VI조의 대칭 툴링 설계에 따라 운영체제별 전용 스크립트로 동일 동작을 완수합니다.

### 3.1 Windows (PowerShell 5.1+ 호환)
`manage-db.ps1` 스크립트를 실행하여 스키마 마이그레이션과 정합성 검증을 일괄 처리합니다.
```powershell
# Windows PowerShell 실행
powershell -ExecutionPolicy Bypass -File .specify/scripts/powershell/manage-db.ps1 -Action Migration
```

### 3.2 macOS / Linux / WSL (Bash 호환)
대칭형 쉘 스크립트를 사용하여 마이그레이션 및 정합성 검증을 일괄 처리합니다.
```bash
# macOS, Linux, WSL 실행
chmod +x .specify/scripts/bash/manage-db.sh
./.specify/scripts/bash/manage-db.sh --action migration
```

---

## 4. 수동 Django 마이그레이션 명령어 (Manual Commands)

로컬 백엔드 가상환경(uv) 내부에서 직접 마이그레이션을 수동 제어하는 표준 절차입니다.

```bash
# 1. 가상환경 내부 진입 (uv 사용 시)
uv venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 2. 신규 모델 감지 및 마이그레이션 파일 생성
python backend/src/manage.py makemigrations accounts ledgers tasks

# 3. 데이터베이스 실제 스키마 반영 및 마이그레이션 적용
python backend/src/manage.py migrate

# 4. 마이그레이션 적용 상태 확인 검증
python backend/src/manage.py showmigrations
```

---

## 5. 모델 설계 검증 테스트 실행 (Running Validation Tests)

마이그레이션 완료 후, `pytest` 테스팅 스위트를 호출하여 6대 Django Model 간의 1:N 원자적 트랜잭션, 복합 고유 제약조건, 그리고 `is_verified` 필드 바이패스 차단 비즈니스 정합성을 기계적으로 자율 검증합니다.

```bash
# pytest 테스트 구동 (Docker 컨테이너 환경)
docker compose exec api_server pytest -v

# 로컬 백엔드 직접 구동
pytest backend/tests/unit/models/ -v
```

테스트 스위트가 에러 없이 모두 녹색(`PASSED`)을 기록할 시, 최종적으로 데이터 레이아웃 품질 게이트를 만족하는 릴리즈 상태로 공인됩니다.

# Quick Start: 1일차 로컬 통합 개발 환경 기동 가이드

본 가이드는 **1일차 계획(001-local-env-setup)**에 의거하여 로컬 PC에 PostgreSQL v18+ 데이터베이스 독립 인스턴스를 도커로 격리 구동하고 접속 및 환경 셋업을 완벽하게 검증하기 위한 매뉴얼입니다.

---

## 1. 사전 요구사항 (Prerequisites)
* 로컬 호스트 PC에 **Docker Desktop**이 설치되어 정상 작동 중이어야 합니다.
* Windows 환경의 경우, WSL 2 백엔드가 활성화되어 통합 연동 상태여야 합니다.

---

## 2. 환경 변수 파일 준비 (`.env.local`)
프로젝트 루트 폴더에 `.env.local` 파일을 생성하고 아래와 같이 보안 파라미터를 작성합니다.
*(주의: 이 파일은 자격 증명이 포함되므로 Git에 커밋하지 않아야 하며, 이미 `.gitignore` 규칙에 의해 보호됩니다.)*

```env
# Database Credentials
POSTGRES_DB=ai_ledger
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Secured_Password18!  # 공백 없는 강력한 비밀번호 설정
POSTGRES_PORT=5432                     # 포트 충돌 시 5433 등으로 변경 가능
```

---

## 3. 원클릭 인프라 기동 명령어

도커 볼륨을 수동으로 우선 확보하고, 격리 컨테이너를 안전하게 백그라운드로 기동합니다.

```powershell
# 1. 영속 저장을 위한 도커 네임드 볼륨 생성
docker volume create postgres_data

# 2. PostgreSQL v18+ Alpine 격리 컨테이너 구동
# (인코딩: UTF-8 강제, 시간대: Asia/Seoul 주입)
docker run -d `
  --name ai-ledger-db `
  -p 5432:5432 `
  -v postgres_data:/var/lib/postgresql/data `
  -e POSTGRES_DB=ai_ledger `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=Secured_Password18! `
  -e TZ=Asia/Seoul `
  --restart unless-stopped `
  postgres:18-alpine `
  -c client_encoding=UTF8 `
  -c timezone=Asia/Seoul
```
*(Windows CMD 환경일 경우 개행 문자 ` `를 `^`로 변경하거나 한 줄로 이어붙여 실행하십시오.)*

---

## 4. 인프라 동작 및 환경 무결성 검증 (DoD 입증)

컨테이너가 기동된 후, 내부 접속 쿼리를 수행하여 문자셋 인코딩과 시간대 셋업이 완수되었는지 검증합니다.

### 4.1. 컨테이너 헬스체크 및 기동 확인
```bash
docker ps --filter "name=ai-ledger-db"
```
* **기대 결과**: `STATUS` 열에 `Up X seconds` 또는 `Up X minutes`와 함께 정상 작동(Healthy) 중임이 표시되어야 합니다.

### 4.2. 데이터베이스 문자셋 및 시간대 쿼리 검증
```bash
docker exec -it ai-ledger-db psql -U postgres -d ai_ledger -c "SHOW client_encoding; SHOW timezone;"
```
* **기대 결과**:
  ```text
   client_encoding 
  -----------------
   UTF8
  (1 row)
  
    TimeZone   
  -------------
   Asia/Seoul
  (1 row)
  ```
  결과값에 인코딩은 `UTF8`, 시간대는 `Asia/Seoul`이 반환되면 1일차 모든 성공 기준 및 헌법 규격을 충족한 것입니다.

---

## 5. 트러블슈팅 (Troubleshooting)

### Q. `5432` 포트가 이미 사용 중이라는 오류가 발생합니다.
* **원인**: 로컬 호스트 PC에 수동으로 설치된 PostgreSQL이 기동 중이거나 다른 서비스가 해당 포트를 점유하고 있습니다.
* **대처**: `.env.local`에서 포트를 `5433` 등으로 바꾸고, docker run 실행 시 `-p 5433:5432` 형태로 외부 포트 매핑을 변경하여 기동하십시오.

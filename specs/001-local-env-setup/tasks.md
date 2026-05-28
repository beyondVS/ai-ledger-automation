# Tasks: 로컬 통합 개발 환경 및 PostgreSQL v18+ 컨테이너 셋업

**Input**: Design documents from `/specs/001-local-env-setup/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: 1일차 인프라 구축 단계에서는 Django 등 백엔드 테스트 프레임워크 도입 전이므로, 독자적인 검증용 파워쉘 헬퍼 스크립트를 작성하여 DoD(완료 정의)를 기계적으로 증명합니다.

**Organization**: 각 태스크는 사용자 스토리별로 정밀하게 격리 및 그룹화되어 있어, 독립적인 구현과 개별 검증이 가능합니다.

---

## Format: `[ID] [P?] [Story] Description`

* **[P]**: 병렬 처리 가능 (대상 파일이 서로 다르고 의존성이 없음)
* **[Story]**: 매핑되는 사용자 스토리 라벨 (`[US1]`, `[US2]` 등)
* 모든 태스크 설명에 구체적이고 명확한 소스 파일 경로를 명시해야 합니다.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 초기화, 공통 자격 증명 템플릿 및 환경 설명서 구축

- [ ] T001 `.env.local.example` 경로에 데이터베이스 접속용 보안 환경 변수 구조 선언 및 템플릿 생성
- [ ] T002 [P] `docs/local-setup.md` 경로에 로컬 Docker Desktop WSL 2 통합 연동 절차 및 권한 확보 가이드 구축

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 사용자 스토리의 본격적인 기동 전, 환경 변수 자동화 및 리소스 사전 확보 처리

**⚠️ CRITICAL**: 이 페이즈의 공통 유틸리티 구성이 완료되기 전까지는 어떠한 사용자 스토리도 실행할 수 없습니다.

- [ ] T003 `scripts/load-env.ps1` 경로에 로컬 `.env.local` 파일의 환경 변수를 자동 구문 분석하여 쉘 컨텍스트에 바인딩하는 로드 스크립트 작성
- [ ] T004 [P] `scripts/init-volumes.ps1` 경로에 호스트 PC의 Docker 연결 상태를 점검하고 네임드 볼륨 `postgres_data`를 사전 확보하는 스크립트 작성

**Checkpoint**: 로컬 자동화 헬퍼 준비 완료 - 이제 사용자 스토리 구현으로 독립 이행 가능

---

## Phase 3: User Story 1 - PostgreSQL v18+ 독립 컨테이너 빌드 및 로컬 마운트 (Priority: P1) 🎯 MVP

**Goal**: 로컬 호스트 PC 권한 에러를 격리 차단하고 PostgreSQL v18 컨테이너를 영속 볼륨 마운트하여 Healthy 기동

**Independent Test**: `scripts/run-db.ps1`을 가동하여 `ai-ledger-db` 컨테이너가 정상 프로세스로 스케줄링되고, 외부 호스트에서 5432 포트가 리스닝 상태에 도달하는지 확인

### Implementation for User Story 1

- [ ] T005 [US1] `scripts/run-db.ps1` 경로에 `.env.local` 자격 증명 정보를 로드하여 `postgres:18-alpine` 경량 이미지 기반의 데이터베이스 컨테이너를 구동하는 기동 자동화 스크립트 구현
- [ ] T006 [P] [US1] `docker-compose.db.yml` 경로에 향후 다중 컨테이너 오케스트레이션(Django, Redis 등) 확장 및 로컬 격리 개발을 위한 싱글 DB 컴포넌트 Docker Compose 설정 정의

**Checkpoint**: User Story 1 완성 - 격리된 PostgreSQL 18 인스턴스가 로컬에서 정상 기동 및 포트 리스닝 완료

---

## Phase 4: User Story 2 - 데이터베이스 한글 인코딩 및 서울 표준시(Asia/Seoul) 설정 (Priority: P2)

**Goal**: 기동된 데이터베이스 서버의 기본 인코딩을 UTF-8로, 엔진 시간대를 Asia/Seoul로 설정하여 가계부 데이터 정합성 보장

**Independent Test**: `scripts/verify-db.ps1` 스크립트를 기동하여 psql 세션을 맺고 한글 인코딩(UTF8) 및 타임존(Asia/Seoul) 검증 SQL의 정적 출력이 통과하는지 확인

### Implementation for User Story 2

- [ ] T007 [US2] `scripts/verify-db.ps1` 경로에 컨테이너 내부 psql 인터페이스에 안전하게 세션을 연결하여 `SHOW client_encoding; SHOW timezone;` 검증 SQL을 실행하고 통과 여부를 쉘 코드 레벨에서 판단하는 검증 자동화 스크립트 구현

**Checkpoint**: User Story 2 완성 - 인코딩 및 시간대 설정이 정상 주입되어 한글 및 결제 시간대 무결성 확인 완료

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: 1일차 통합 환경 연동 상태 점검, 자원 정리 및 최종 릴리즈 게이트 수행

- [ ] T008 `quickstart.md`에 명시된 원클릭 기동 및 자동 검증 프로토콜을 수행하여 E2E 동작 무결성 최종 검사
- [ ] T009 [P] `scripts/cleanup-db.ps1` 경로에 개발 목적 변경 시 기존 생성된 ai-ledger-db 컨테이너와 Named Volume을 안전하게 격리 폐기하는 자원 정리 헬퍼 스크립트 구현

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 대기 없는 초도 구성 단계로, 즉시 병렬 시작 가능.
- **Foundational (Phase 2)**: Setup 페이즈 완료에 100% 종속되며, 완료 시점까지 모든 사용자 스토리 페이즈를 블로킹함.
- **User Story 1 (Phase 3)**: Foundational 페이즈 완료 즉시 실행 가능 (가장 핵심적인 MVP 타깃).
- **User Story 2 (Phase 4)**: User Story 1의 컨테이너 기동 상태에 종속되므로, Phase 3 컨테이너 프로세스 바인딩 완료 후 실행 가능.
- **Polish (Phase 5)**: 모든 사용자 스토리가 구현 완료된 후 통합 품질 게이트 확인을 위해 최종 구동.

### Parallel Opportunities

* Setup 페이즈의 `T001`과 `T002`는 다른 목적의 문서/사양 작성이므로 병렬 실행 가능.
* Foundational 페이즈의 `T004`와 `T003`은 파일 목적이 달라 병렬 실행 가능.
* User Story 1 내의 Docker run 기동 스크립트 작성(`T005`)과 확장 Compose 명세 작성(`T006`)은 병렬 작성 가능.
* Polish 페이즈의 자원 정리 스크립트 작성(`T009`)은 릴리즈 확인(`T008`)과 파일이 달라 독립 병렬 코딩 가능.

---

## Parallel Example: User Story 1

```powershell
# User Story 1의 빌드 자동화 스크립트와 Compose 확장을 독립적으로 개발하여 릴리즈 속도 확보:
Task: "scripts/run-db.ps1 경로에 PostgreSQL 18-alpine 컨테이너 기동 파워쉘 스크립트 구현"
Task: "docker-compose.db.yml 경로에 싱글 DB 컴포넌트 Docker Compose 설정 정의"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Setup & Foundational 완수**: 환경 변수 로드 및 볼륨 생성 스크립트 기초 완성.
2. **User Story 1 집중 타격**: `scripts/run-db.ps1`을 구현 및 구동하여 로컬 컨테이너 부팅 및 포트 매핑 확인.
3. **DoD 중간 검증**: 외부 DB 접속 툴을 통한 접속 테스트 통과 확인 후 MVP 증분 마감.

### Incremental Delivery

1. **인프라 부팅 증분 인도**: 컨테이너가 격리 작동함을 증명.
2. **정합성 옵션 증분 인도**: 인코딩과 시간대 확인 쉘 스크립트(`scripts/verify-db.ps1`)를 붙여 환경 최적화 완수.
3. **Polish & Cleanup 증분 인도**: 안전한 격리 폐기 스크립트를 더해 개발 환경 완성도 마감.

---

## Notes

* 각 태스크는 반드시 지정된 소스 파일 경로 내에서만 수술적으로 코딩을 진행하여 충돌을 막아야 합니다.
* 모든 기동/검증 스크립트는 PowerShell 5.1 및 로컬 WSL 2 도커 환경과의 호환성을 엄격히 준수하여 코딩해야 합니다.
* 완료 시 마다 개별 쉘 코드를 실행하여 DoD 통과 상태를 수시로 확인하고 Git 커밋을 잘게 수행하십시오.

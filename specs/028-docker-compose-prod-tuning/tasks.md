# Tasks: Docker Compose Prod Tuning & Port Security

**Input**: Design documents from `/specs/028-docker-compose-prod-tuning/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ports-contract.md

**Tests**: TDD 방식이 요청되었으므로 모든 사용자 스토리 구현 태스크 시작 전에 해당 요건을 검증하며 실패(Red) 상태를 유도하는 테스트 코드 작성 단계를 필수로 포함합니다.

**Organization**: 각 태스크는 독립적인 개발 및 검증이 가능하도록 사용자 스토리별로 페이즈를 할당하여 격리 조직화하였습니다.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: 다른 파일에 독립적으로 병렬 처리가 가능한 작업 (의존성 없음)
- **[Story]**: 매핑되는 사용자 스토리 식별자 (US1, US2, US3 등)
- 각 태스크는 명확한 코딩 대상 소스 파일 경로를 명시하고 있습니다.

## Path Conventions

- **인프라 설정**: 프로젝트 루트의 `docker-compose.prod.yml`
- **백엔드 테스트**: `backend/tests/` (pytest 검증용 소스)
- **대칭형 검증 툴링**: `scripts/` (PowerShell 및 Bash 스크립트)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 구조 초기화 및 기본 프로덕션 도커 파일 레이아웃 수립

- [x] T001 프로젝트 루트 경로에 `docker-compose.prod.yml` 파일을 새로 생성하고 기본 YAML 뼈대 구조를 정형화
- [x] T002 [P] 백엔드 `backend/pyproject.toml`에 인프라 설정 파싱 검증 및 테스트 가동에 필요한 종속성(pytest, pyyaml 등) 유무를 확인하고 `uv lock` 및 `uv sync`를 실행해 의존성 업데이트

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 개별 사용자 스토리가 적용되기 전에 수립되어야 하는 글로벌 가상 네트워크 및 볼륨 정의

**⚠️ CRITICAL**: 이 페이즈가 완료되기 전까지는 개별 사용자 스토리 구현을 착수할 수 없습니다.

- [x] T003 `docker-compose.prod.yml` 파일 내에 컴포즈 전용 격리 브리지 네트워크(`prod-bridge`) 선언 및 PostgreSQL 데이터 영속화를 위한 도커 Named Volume (`postgres_data`) 바인딩 정의 추가
- [x] T004 [P] `docker-compose.prod.yml` 상에 글로벌 로깅 템플릿(json-file, max-size: 10m, max-file: 3)의 기본 정의를 수립

**Checkpoint**: Foundational 설정 완료 - 이후 사용자 스토리 페이즈는 병렬 혹은 순차 진행이 가능합니다.

---

## Phase 3: User Story 1 - 서비스 고가용성 및 자원 격리 (Priority: P1) 🎯 MVP

**Goal**: 각 마이크로서비스 컨테이너에 절대적 CPU/메모리 limits 한도 강제 및 자가 치유 헬스 체크 기동

**Independent Test**: 백엔드 컨테이너 내부 헬스체크 비정상 유도 시 자동 재시작이 수행되며, `docker stats` 상에 제한 임계치 용량이 정상 표시되는지 검증

### Tests for User Story 1 (TDD Mandated) ⚠️

> **NOTE: 구현 전에 아래 테스트 코드를 먼저 작성하고, 기동 시 실패(FAIL)하는 것을 입증해야 합니다.**

- [x] T005 [P] [US1] `backend/tests/test_infra_resource_limits.py` 경로에 `docker-compose.prod.yml` 파일을 로드하여 각 서비스의 CPU 및 메모리 limits/reservations 설정 유무와 헬스 체크 설정 규격을 검증하는 TDD 통합 테스트 코드를 구현

### Implementation for User Story 1

- [x] T006 [US1] `docker-compose.prod.yml` 내의 `postgres_db`, `redis_broker`, `api-server`, `async_worker`, `nginx` 개별 서비스 명세 내에 지정된 CPU 및 메모리 제한(limits 및 reservations) 절대 할당 설정값을 고정 선언 형태로 작성
- [x] T007 [US1] `docker-compose.prod.yml` 의 각 서비스별 `healthcheck` 실행 명령(pg_isready, redis-cli ping 등) 및 주기(interval), 타임아웃(timeout), 실패 임계치(retries)와 함께 컨테이너 비정상 감지 시 자동 복구를 유도하는 `restart` 옵션을 추가 기술

**Checkpoint**: 이 시점에서 User Story 1(자원 튜닝 및 헬스 체크 자가 치유)은 독립적으로 구동되고 테스트 가능해야 합니다.

---

## Phase 4: User Story 2 - 비인가 접근을 차단하는 호스트 포트 보안 (Priority: P1)

**Goal**: 외부 IP 주소를 통한 DB/Redis/API 직접 유입 포트를 거부하고 Nginx 리버스 프록시(80/443) 통신선만 개방

**Independent Test**: 공인 IP 포트 스캔을 수행하여 80/443 이외의 포트가 closed/filtered 임을 확인하고, 내부 도커 브리지 네트워크 간의 서비스 포트 라우팅 정상 통신 여부를 검증

### Tests for User Story 2 (TDD Mandated) ⚠️

> **NOTE: 구현 전에 아래 테스트 코드를 먼저 작성하고, 기동 시 실패(FAIL)하는 것을 입증해야 합니다.**

- [x] T008 [P] [US2] `backend/tests/test_infra_port_isolation.py` 경로에 `docker-compose.prod.yml` 스펙을 파싱하여 Nginx 컨테이너를 제외한 나머지 서비스들의 ports 매핑 선언이 비활성화되었는지 검증하는 TDD 테스트 코드를 작성
- [x] T009 [P] [US2] `scripts/run_port_scan.ps1` 및 `scripts/run_port_scan.sh` 경로에 nmap 또는 tcpport 기반 외부 격리 검증을 자동 수행하는 크로스 플랫폼 대칭형 검증 툴링 스크립트의 뼈대를 생성하고 실패 코드 상태를 유도

### Implementation for User Story 2

- [x] T010 [US2] `docker-compose.prod.yml` 상에서 `postgres_db`, `redis_broker`, `api-server`, `async_worker` 서비스 정의 내의 호스트 `ports` 바인딩을 전면 영구 삭제하여 외부 노출을 제거
- [x] T011 [US2] `docker-compose.prod.yml` 에 Nginx 서비스 정의를 주입하고 호스트 `80:80`, `443:443` 포트를 매핑하며, `prod-bridge` 네트워크 내부에서 `api-server:8000`으로 통신을 위임 포워딩하도록 리버스 프록시를 바인딩 구성
- [x] T012 [US2] `scripts/run_port_scan.ps1` 및 `scripts/run_port_scan.sh` 경로의 스크립트 파일들에 배포 대상 공인 IP 포트 상태를 순차 테스트하여 closed/filtered 시 정상 종료하고, 포트 개방 감지 시 비정상 코드로 종료하는 대칭형 포트 스캔 검증 로직 구현을 완성 (T009 연계)

**Checkpoint**: 이 단계가 완료되면 외부에서 DB 및 캐시 포트로의 비인가 직접 접근이 전면 격리 통제됩니다.

---

## Phase 5: User Story 3 - 프로덕션 로그 로테이션 및 디스크 고갈 예방 (Priority: P2)

**Goal**: stdout/stderr 스트림 로그가 무한 증식해 호스트 디스크를 소진하는 현상을 격리 통제

**Independent Test**: 컨테이너 로그 물리 파일 용량이 최대 용량 도달 시 로테이션 분할되며 설정 파일 상한 규격(30MB) 내로 강제 유지되는지 확인

### Tests for User Story 3 (TDD Mandated) ⚠️

- [x] T013 [P] [US3] `backend/tests/test_infra_log_rotation.py` 경로에 `docker-compose.prod.yml` 내 개별 서비스의 로깅 드라이버 방식 및 max-size, max-file 한계 사양이 준수되었는지 체크하는 TDD 검증 테스트 코드를 구현

### Implementation for User Story 3

- [x] T014 [US3] `docker-compose.prod.yml` 상의 모든 개별 서비스 컴포넌트 하위에 json-file 로그 드라이버 및 `max-size: "10m"`, `max-file: "3"` 옵션 설정을 기입 완료

**Checkpoint**: 모든 사용자 스토리의 구현 및 테스트 코드가 독립적이고 유기적으로 완결되어 가동 가능해야 합니다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 프로덕션 배포 전 민감 설정 안전성 정수 점검, 매뉴얼 문서화 및 통합 가동 확인

- [x] T015 [P] `docs/infrastructure_tuning_guide.md` 경로에 실 서비스 기동, 자원 할당량 조절 가이드 및 Named Volume 백업/복구 절차 매뉴얼을 문서화 작성
- [x] T016 [P] 프로젝트 루트에 배치될 배포 환경 변수 파일(`.env.prod`) 내에 비밀번호, API 키 등의 민감 정보 하드코딩 여부 교차 정수 검증 진행
- [x] T017 `quickstart.md`에 정의된 전체 가이드를 따라 `uv run pytest` 명령을 활용하여 로컬 인프라 테스트 정합성 최종 패스 검증 완료 및 ruff pre-commit 린트 무결성 확인

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 다른 작업에 대한 종속성이 없어 즉시 수행 가능합니다.
- **Foundational (Phase 2)**: Setup 단계가 완수되어야 시작 가능하며, 완료 전까지는 개별 사용자 스토리 구현을 완전히 블로킹합니다.
- **User Stories (Phase 3 ~ 5)**: Foundational 레이아웃 정의가 완결된 후 진행 가능합니다.
  - US1(자원 격리/고가용성)과 US2(포트 노출 차단)는 순번에 구애받지 않고 독립된 파일에서 병렬 구현이 가능합니다.
  - US3(로그 로테이션) 역시 개별 컨테이너 구성이 완료되는 시점에 병렬 가동 가능합니다.
- **Polish (Phase 6)**: 모든 서비스 설계 및 스펙 검증 코드가 완료된 후 가동됩니다.

### Within Each User Story

1. 테스트(TDD) 코드가 먼저 작성되고 pytest 가동 시 **FAIL**이 나야 합니다.
2. 이후 컴포즈 설정 구현(YAML 명세)을 진행합니다.
3. 기계적 검증 도구(TDD 테스트 및 포트 스캔)를 재가동하여 **PASS**함을 증명합니다.
4. 독립 테스트 조건 통과 시 다음 스토리로 넘어갑니다.

### Parallel Opportunities

- **T001** 및 **T002**는 상호 간섭이 없어 병렬로 처리 가능합니다.
- TDD 테스트 작성 태스크인 **T005**, **T008**, **T013**은 각각 독립적인 테스트 파일이므로 병렬 설계가 가능합니다.
- **T009** 툴링 스크립트 작성 역시 병렬 진행 가능합니다.

---

## Parallel Example: User Story 2

```bash
# User Story 2 테스트 코드 및 검증 툴링 스크립트를 독립적으로 동시 가동
Task: "backend/tests/test_infra_port_isolation.py 경로에 포트 매핑 차단 검증 TDD 테스트 구현"
Task: "scripts/run_port_scan.ps1 및 run_port_scan.sh 경로에 검증 툴링 스크립트 뼈대 생성"

# 이후 실제 docker-compose.prod.yml 설정 수정 작업 진행
Task: "docker-compose.prod.yml 상에서 ports 바인딩 삭제 및 Nginx 추가"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. **Phase 1 (Setup)** 및 **Phase 2 (Foundational)** 완료.
2. **Phase 3 (User Story 1 - 자원 및 가용성 격리)** 구현.
3. `uv run pytest backend/tests/test_infra_resource_limits.py` 실행을 통해 MVP 단일 검증 완료.
4. 실 배포 인프라 가용성 확인 후, 보안 및 로그 등 후속 스토리 적재.

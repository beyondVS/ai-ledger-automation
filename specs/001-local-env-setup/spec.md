# Feature Specification: 로컬 통합 개발 환경 및 PostgreSQL v18+ 컨테이너 셋업

**Feature Branch**: `001-local-env-setup`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "1일차 계획에 대해서 스펙을 정의 하라"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PostgreSQL v18+ 독립 컨테이너 빌드 및 로컬 마운트 (Priority: P1)

개발자는 로컬 PC 환경에 PostgreSQL을 번거롭게 직접 설치하지 않고, 격리된 가상 컨테이너 환경에서 PostgreSQL v18+ 데이터베이스 엔진 인스턴스를 빌드하고 기동할 수 있어야 합니다.

**Why this priority**: 가습기나 가상 환경 설정 없이 모든 개발자가 일관된 데이터베이스 엔진 환경(동일 버전 및 옵션)을 갖추어 협업 효율성을 극대화하기 위해 가장 기본적으로 수립되어야 하는 아키텍처 필수 조건입니다.

**Independent Test**: 로컬 Docker Desktop을 기동하고 PostgreSQL 18 이미지를 빌드 및 마운트하여 컨테이너 외부 로컬 호스트 볼륨에 데이터가 영속적으로 적재되는지, 그리고 정상 기동되는지 테스트 도구(DBeaver, psql 등)를 통해 검증합니다.

**Acceptance Scenarios**:

1. **Given** Docker Desktop이 구동 중인 상태에서, **When** PostgreSQL 18 공식 Alpine 이미지를 기반으로 로컬 볼륨 마운트 옵션을 활성화하여 기동하면, **Then** 호스트 PC 폴더 내에 PostgreSQL 데이터 파일들이 자동으로 생성되고 컨테이너가 Healthy 상태로 기동된다.
2. **Given** 격리 기동된 PostgreSQL 컨테이너가 있을 때, **When** 로컬 호스트 `5432` 포트로 외부 DB 접속 툴을 통해 슈퍼유저 인증 정보(ID/PW)를 제공하고 접속을 시도하면, **Then** 지연 없이 성공적으로 원격 세션이 맺어진다.

---

### User Story 2 - 데이터베이스 한글 인코딩 및 서울 표준시(Asia/Seoul) 설정 (Priority: P2)

데이터베이스의 기본 문자셋 인코딩은 `UTF-8`로 강제되고, 기본 시간대(TimeZone)는 한국 표준시(`Asia/Seoul`)로 동기화되어 가계부 결제 내역이나 PDF 파싱 일자가 9시간 밀리는 현상이 방지되어야 합니다.

**Why this priority**: 세금계산서 및 가계부 영수증 PDF의 텍스트가 깨지지 않고, 비동기 작업 시 모든 거래 내역과 로그 데이터가 올바른 한국 표준시 기준으로 정밀하게 적재되어 일관성을 보장하기 위함입니다.

**Independent Test**: 컨테이너 DB에 쿼리 세션을 연결하여 `SHOW client_encoding;` 및 `SHOW timezone;` 명령어들을 실행하여 환경 변수 셋업이 완수되었는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** PostgreSQL 컨테이너에 최초 쿼리 세션이 연결되었을 때, **When** `SHOW client_encoding;` 쿼리를 실행하면, **Then** 결과 문자셋이 `UTF8`로 정상 표시된다.
2. **Given** PostgreSQL 컨테이너에 최초 쿼리 세션이 연결되었을 때, **When** `SHOW timezone;` 쿼리를 실행하면, **Then** 시간대 설정이 `Asia/Seoul` 또는 `KST`로 반환된다.

---

### Edge Cases

- **호스트 PC의 5432 포트가 이미 로컬 개발이나 다른 서비스로 선점되어 사용 중인 경우**: 포트 충돌로 컨테이너 부팅이 실패하므로, 외부 포트 바인딩 설정을 환경 변수로 유연하게 격리 지정할 수 있어야 합니다.
- **호스트 PC 운영체제(Windows, macOS 등)의 디렉토리 파일 시스템 권한 제한**: Docker Desktop 볼륨으로 지정된 호스트 디렉토리에 데이터베이스 엔진이 쓰기 권한이 없을 경우 가동이 중단되므로, 적절한 퍼미션 보장 가이드와 Docker 호환 설정이 필요합니다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 격리된 가상 환경 구현을 위해 PostgreSQL v18+ 공식 Alpine 배포 버전을 컨테이너로 빌드 및 구동해야 합니다.
- **FR-002**: 시스템은 로컬 볼륨 마운트 시 도커 엔진이 격리 관리하는 **도커 네임드 볼륨 (Named Volume) `postgres_data`**를 생성하여 지정해야 합니다.
- **FR-003**: 데이터베이스의 슈퍼유저 계정(postgres) 비밀번호 및 초기 데이터베이스 이름(ai_ledger)은 암호화되거나 외부에 노출되지 않도록 로컬 환경 변수(`.env.local`) 파일에서 보안 주입받아 사용해야 합니다.
- **FR-004**: 영수증 텍스트 및 가맹점 상세 분석 정보에 한글 깨짐이 전혀 없도록 데이터베이스의 기본 문자셋 인코딩 설정을 `UTF-8`로 강제 설정하여 초기화해야 합니다.
- **FR-005**: 가계부 거래 일자 및 결제 타임스탬프의 시간적 정합성을 위해 데이터베이스 엔진의 시간대(TimeZone) 설정을 `Asia/Seoul`로 주입하고 기동해야 합니다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Docker 컨테이너 명령을 통한 PostgreSQL v18+ 데이터베이스 서버의 초기 부팅 및 네트워크 리스닝 개시까지 걸리는 소요 시간이 15초 이내여야 합니다.
- **SC-002**: 로컬 접속 클라이언트에서 데이터베이스로의 Ping 및 단순 Select 쿼리 요청의 응답 시간이 50ms 이내여야 합니다.
- **SC-003**: PostgreSQL 데이터베이스 컨테이너가 불시에 정지(Stop) 또는 크래시되어 재부팅되더라도, 기존에 적재되어 있던 가계부 가상 테스트 데이터는 유실 없이 100% 보존되어 정상 조회되어야 합니다. (볼륨 영속성 검증)

## Assumptions

- 개발자의 PC에는 최신 Docker Desktop 및 Windows WSL 2 환경이 정상적으로 구동되고 있다고 가정합니다.
- 슈퍼유저 패스워드 등 민감 정보 관리를 위해 `.env.local` 파일이 로컬에 별도로 정의된다고 가정하며, 이는 Git 형상 관리 대상에서 엄격히 제외됩니다.
- 1일차 계획은 Django API 프레임워크 셋업 이전의 순수 격리 DB 및 인프라 기본 기동을 다루며, Redis 및 Django 컨테이너 오케스트레이션 연동 설계는 향후 5일차 docker-compose 단계에서 상세 수립된다고 가정합니다.

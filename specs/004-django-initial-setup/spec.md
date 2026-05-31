# Feature Specification: django-initial-setup

**Feature Branch**: `004-django-initial-setup`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Python 및 Django 웹 애플리케이션 프레임워크 초기 보일러플레이트 코드 빌드. .env 환경변수 연동 및 데이터베이스 연동용 settings.py 기본 셋업 완수."

## Clarifications

### Session 2026-05-31

- **Q1**: `settings.py` 내 PostgreSQL 연결 기본 폴백(Fallback) 구성 수준 → **A**: `옵션 B (엄격한 에러 검증 - No Fallback)`. 어떠한 자격 증명 폴백 기본값도 제공하지 않고 `.env`에 `DATABASE_URL`이 누락되거나 비어 있을 시 즉각 `ImproperlyConfigured` 예외를 노출하여 서버 부팅을 중지함.
- **Q2**: Django REST Framework (DRF)의 기본 권한 및 인증 정책 기본값 → **A**: `옵션 A (안전 우선 글로벌 차단 - IsAuthenticated 기본)`. 처음부터 안전 우선 전역 차단 정책을 적용하고 특정 예외 페이지만 화이트리스트로 허용하여 보안 사고 예방.
- **Q3**: PostgreSQL 데이터베이스 커넥션 유지 및 자원 통제 정책 (CONN_MAX_AGE) → **A**: `옵션 A (동적 자원 재사용 - 60초 기본 및 환경변수 주입)`. 60초를 기본 유지 시간으로 설정하여 접속 부하를 줄이되, `.env`를 통한 재사용 임계 제어로 무료 클라우드 환경 고갈 방지.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local Development Startup (Priority: P1)

시스템 개발자는 Django 보일러플레이트 코드를 로컬 환경에서 기동하고 설정의 정합성을 검증할 수 있어야 한다.

**Why this priority**: 보일러플레이트 코드 구축의 가장 핵심적인 목적은 개발자가 즉시 개발에 착수할 수 있는 올바르고 안정적인 진입점을 마련하는 것이다.

**Independent Test**: 백엔드 서버 기동 명령어를 실행하였을 때 에러 없이 성공적으로 웹 서버가 실행되고, 로컬 호스트 주소로의 접속 시 기본 웹 페이지가 반환됨을 검증한다.

**Acceptance Scenarios**:

1. **Given** `backend` 디렉토리에 보일러플레이트가 구성되어 있고 가상환경 의존성이 설치되었을 때, **When** 서버 구동 명령을 내리면, **Then** Django 서버가 오류 없이 부팅되어야 한다.
2. **Given** Django 서버가 실행 중일 때, **When** 로컬호스트 개발 포트로 HTTP GET 요청을 보내면, **Then** 200 OK 상태 코드와 함께 Django 환영 페이지가 정상 반환되어야 한다.

---

### User Story 2 - Database Connection & Health Verification (Priority: P1)

개발자는 Django와 PostgreSQL 데이터베이스가 정상적으로 통신하고 연동됨을 마이그레이션 명령어로 확인할 수 있어야 한다.

**Why this priority**: 가계부 및 회계 데이터 처리를 위한 데이터 정합성과 영속성을 보장하기 위해, PostgreSQL과의 안정적인 커넥션 셋업이 필수적이다.

**Independent Test**: 데이터베이스 컨테이너가 실행된 상태에서 Django 마이그레이션 명령(`migrate`)을 수행하여 DB 테이블이 정상 생성되고 관계가 형성되는지 확인한다.

**Acceptance Scenarios**:

1. **Given** PostgreSQL v18+ 인스턴스가 활성화되어 있을 때, **When** Django `migrate` 명령을 실행하면, **Then** Django 기본 내장 앱용 테이블 및 데이터베이스 초기 마이그레이션이 에러 없이 실행 완료되어야 한다.

---

### User Story 3 - Environment Variable Hot Reloading (Priority: P2)

개발자는 소스 코드 수정 없이 `.env` 파일의 변수값만 변경하여 로컬/검증/운영 환경의 환경 구성을 즉시 제어할 수 있어야 한다.

**Why this priority**: 보안 자격 증명(API 키, 데이터베이스 암호) 유출을 방어하고, 환경 간 격리를 코드 변경 없이 관리하기 위함이다.

**Independent Test**: `.env`에 정의된 데이터베이스 주소나 비밀키를 임의로 오타가 있는 값으로 변경했을 때, 서버가 구동 중지되거나 연결 거부 예외가 발생하고, 올바르게 설정 시 정상 복구됨을 검증한다.

**Acceptance Scenarios**:

1. **Given** `.env` 파일에 유효하지 않은 `DATABASE_URL`이 기재되었을 때, **When** Django가 구동을 시도하면, **Then** DB 연결 거부 예외를 안전하게 던지며 적절한 에러 로그를 콘솔에 출력해야 한다.
2. **Given** `.env` 파일에 올바른 자격 증명이 주어지면, **When** Django가 구동되면, **Then** 정상적으로 데이터베이스와 핸드셰이크를 완료하고 연결되어야 한다.

---

### Edge Cases

- **환경 변수 누락**: 필수 보안 자격 증명(예: `SECRET_KEY`, `DATABASE_URL`)이 `.env`에 누락되었을 때 시스템이 런타임 Crash를 발생시키며 개발자에게 즉시 원인을 명확히 고지해야 한다.
- **데이터베이스 오프라인**: PostgreSQL DBMS 서버가 다운되어 있거나 네트워크 오류 상태일 때 Django 구동이 무한 대기에 빠지지 않고 적절한 연결 시도 제한 시간(Connection Timeout)을 지켜 에러를 노출해야 한다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 이미 준비되어 있는 단일 진입점인 `backend/src/config` 디렉토리 하위에 핵심 설정 및 보일러플레이트 코드를 완벽히 안착시키고, `backend/src/manage.py`를 통해 프로젝트가 제어되도록 구성해야 한다.
- **FR-002**: 시스템은 `django-environ` 패키지를 백엔드 선언적 의존성에 도입하여 `.env` 형식의 환경변수 파일로부터 런타임 설정을 유기적으로 파싱 및 안전 주입해야 한다. 이때 `settings.py`에 자격 증명 관련 폴백(Fallback) 기본값을 하드코딩해서는 안 되며, 환경 변수 누락 시 즉시 예외를 발생시키고 서버 구동을 중단시켜야 한다.
- **FR-003**: 시스템은 PostgreSQL v18+ 연동을 위해 `psycopg3` (C 가속 패키지) 라이브러리를 연동하고 `settings.py` 내에 데이터베이스 연결 풀을 구성해야 한다. 기본 데이터베이스 연결 유지 시간(`CONN_MAX_AGE`)을 60초로 셋업하되, 환경 변수를 통해 동적으로 재정의 가능하게 지원해야 한다.
- **FR-004**: 시스템은 보안 자격 증명(Database Password, SECRET_KEY)을 절대 소스코드 내에 하드코딩해서는 안 되며, `.gitignore`를 통해 Git 추적 대상에서 격리시켜야 한다.
- **FR-005**: 시스템은 향후 SPA(Vue.js 3) 클라이언트 연동 및 REST API 개발을 선행 준비하기 위해 `django-cors-headers` 및 `djangorestframework (DRF)`를 settings.py에 기본 활성화 및 연동해야 한다. 보안 우선 원칙에 따라 글로벌 API 기본 접근 제한을 `IsAuthenticated`로 엄격히 강제 잠금하고, 필요한 경우에만 예외를 허용해야 한다.

### Key Entities *(include if feature involves data)*

- **Runtime Environment Settings (설정 데이터)**: Django의 `settings.py`에 적용되는 데이터셋으로, `SECRET_KEY`, `DEBUG` 플래그, `ALLOWED_HOSTS`, `DATABASE_URL` 등을 속성으로 가진다.
- **Database Connection Entity (데이터베이스 커넥션)**: PostgreSQL v18+ 데이터베이스와의 영속적인 연결 엔티티로, 호스트 주소, 포트 번호, 사용자 계정, 비밀번호, 그리고 타겟 데이터베이스 명을 보유한다.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 로컬 개발자 서버 부팅 명령 수행 시, Django 코어 프레임워크가 3초 이내에 정상 기동을 완료해야 한다.
- **SC-002**: 마이그레이션(`migrate`) 실행 시 100% 정상 작동하며, 연동 오류로 인한 예외가 전혀 없어야 한다.
- **SC-003**: 민감 정보(Secret Key, DB Password)가 형상 관리 리포지토리에 단 한 글자도 유출되지 않고 완전히 `.env` 파일로 격리 유지되어야 한다.

## Assumptions

- 로컬 개발 환경 및 도커 컴포즈 상에 PostgreSQL v18+가 사전 실행 중이거나 실행 가능한 상태이다.
- 백엔드 소스 코드는 `backend` 디렉토리 내에 위치하며, 패키지는 `uv`를 통해 선언적 및 락 파일로 완벽하게 관리된다.
- 이 단계에서는 비즈니스 로직(가계부 연산 등)을 직접 다루지 않고, 오직 안전하게 프레임워크를 동작시키기 위한 기본 뼈대 코드만 설계 및 구축한다.

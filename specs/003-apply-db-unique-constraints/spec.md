# Feature Specification: Database Migration and Unique Constraints

**Feature Branch**: `003-apply-db-unique-constraints`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "데이터베이스 마이그레이션 도구(Django 내장 마이그레이션 시스템) 환경 연동. 2주차에 가동할 중복 적재 유효성 가이드라인 준수를 위해 복합 고유 제약조건 unique_together 혹은 UniqueConstraint를 각 모델 정의에 적용하고 마이그레이션 파일 작성 및 DB 반영 검증 성공."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Django Migrations 환경 구축 및 마이그레이션 자동화 (Priority: P1)

시스템 백엔드 개발자 및 CI/CD 인프라는 Django 프레임워크 고유의 선언적 마이그레이션 관리 모듈을 로컬 데이터베이스와 원활하게 연동하고 물리 테이블을 멱등성 있게 일괄 부팅할 수 있어야 합니다.

**Why this priority**: 데이터베이스를 코드로 관리하고(Migrations-as-Code) 이력을 영구 보존하는 기초 인프라로서, 다른 모든 비즈니스 모델링 기능들이 작동하기 위해 선행 달성되어야 하는 MVP 게이트입니다.

**Independent Test**: `python manage.py migrate` 명령어 단 한 번의 호출로 로컬 PostgreSQL DB 상에 3대 신규 앱(`accounts`, `ledgers`, `tasks`)의 모든 물리 스키마 테이블들이 에러율 0%로 완벽하게 자동 생성됨을 증명합니다.

**Acceptance Scenarios**:

1. **Given** PostgreSQL 18+ DB가 깨끗한 초기 상태이고, **When** 마이그레이션 명령어 `python manage.py migrate`를 구동할 때, **Then** 모든 스키마 마이그레이션 파일이 순차 적용되어 물리 테이블이 생성되어야 합니다.
2. **Given** 마이그레이션이 기 적용된 상태이고, **When** 동일 명령을 다시 구동할 때, **Then** 어떠한 오류나 테이블 덮어쓰기 없이 "No migrations to apply"가 뜨며 안전히 스킵되어야 합니다.

---

### User Story 2 - 모델 스키마 내 UniqueConstraint 복합 고유 제약조건 적용 (Priority: P2)

가계부 원장의 신뢰성을 영구 수호하기 위해, 동일 영수증에 대한 중복 거래 적재 시도를 데이터베이스 엔진 레이어에서 복합 유니크 제약조건을 통해 사전에 차단하고 데이터 파편화를 원천 방지해야 합니다.

**Why this priority**: 사용자가 실수로 동일 영수증을 반복 업로드하여 가계부 누적 통계의 무결성이 깨지는 심각한 비즈니스 붕괴 시나리오를 물리적으로 원천 차단하기 위함입니다.

**Independent Test**: 중복 거래 필드 조합(사용자 ID, 사업자등록번호, 거래 일자, 총 결제 금액)이 일치하는 데이터를 2회 연속 데이터베이스에 기입(Insert) 시도 시, 두 번째 내역이 DB 레이어에서 단호하게 무결성 예외(IntegrityError)를 던지며 유입 차단됨을 입증합니다.

**Acceptance Scenarios**:

1. **Given** 특정 사용자의 거래 내역(`user_id=1, vendor_reg_num='1234567890', transaction_date='2026-05-29', total_amount=15000`)이 적재된 상태에서, **When** 완전히 동일한 값의 레코드 삽입을 재시도할 때, **Then** 데이터베이스 단에서 Unique 제약 위배 예외를 리턴하고 삽입을 거부해야 합니다.
2. **Given** 거래 내역이 정상 차단될 때, **When** 간이 영수증 등으로 사업자등록번호가 없는 거래 정보가 다중 유입될 때, **Then** 고유 제약조건 위배 우회를 피하기 위해 스키마에 정의된 기본 폴백 문자열('0000000000')로 채워져 복합 UNIQUE 제약조건이 100% 정상 작동해야 합니다.

---

### User Story 3 - 마이그레이션 멱등성 및 로컬 DB 관리 스크립트 통합 (Priority: P3)

크로스 플랫폼 개발 환경(PowerShell 및 Bash) 상에서 원클릭으로 가상 볼륨 소멸, 데이터베이스 재생성, 마이그레이션 일괄 빌드 및 더미 데이터 초기화가 동기 가동될 수 있도록 멱등성이 보장된 환경 제어 도구를 연동합니다.

**Why this priority**: 로컬 개발과 빌드 정합성을 1초 만에 검증하고, 여러 작업자들이 동일한 DB 테스트 샌드박스를 대칭적으로 사용하기 위함입니다.

**Independent Test**: 프로젝트 관리 스크립트를 사용하여 DB 리셋을 실행한 뒤, 8종 모델 유닛 테스트를 순차적으로 구동하여 데이터베이스 재생성 및 무결 제약조건의 정상 작동이 100% 확인되는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 로컬 DB 관리 스크립트로 Action=Reset을 지정하여 기동할 때, **Then** 기존 컨테이너 볼륨이 안전히 회수 및 소멸되어 완전한 태초의 무결 상태로 리부팅되어야 합니다.
2. **Given** 인프라 리부팅 직후, **When** `pytest` 테스트 스위트를 돌릴 때, **Then** 데이터베이스 스키마와 중복 유효성 제약조건들이 기계적으로 일제히 완벽히 검증 통과되어야 합니다.

---

### Edge Cases

- **사업자등록번호가 누락(null)된 영수증이 유입되는 경우**:
  일반적인 데이터베이스 제약 상 `null` 값은 서로 고유한 것으로 간주하여 복합 고유 제약조건(`UniqueConstraint`)에 걸리지 않아 중복 적재를 막지 못합니다. 이를 방어하기 위해 사업자등록번호 부재 시 스키마 단에 정의할 기본 폴백 정책이 요구됩니다.
- **마이그레이션 빌드 도중 컬럼 삭제/타입 변환이 꼬이는 경우**:
  다양한 백엔드 앱(accounts, ledgers 등) 간에 외래키(ForeignKey) 의존 관계가 꼬여 순환 참조 마이그레이션 오류를 뿜을 때, 마이그레이션 순서(`dependencies`)를 명시적으로 규정해 이를 차단합니다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 Django 내장 마이그레이션 도구를 활용하여 비즈니스 데이터 모델들을 물리 데이터베이스 레이아웃과 원자적으로 동기 관리해야 합니다.
- **FR-002**: `Ledger` 모델 정의 단에 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약조건을 `models.UniqueConstraint` 명세를 활용해 명확히 적용해야 합니다.
- **FR-003**: `UserPushSubscription` 모델에는 동일 유저에 대해 동일한 Web Push Endpoint 정보가 다중 등록되지 않도록 복합 고유 제약조건을 장착해야 합니다.
- **FR-004**: 마이그레이션 스크립트는 원자적(Atomic) 트랜잭션 범위 내에서 작동하여, 빌드 실패나 예외 유입 시 이전 롤백(Rollback) 상태로 전격 원자 복원되어야 합니다.
- **FR-005**: 마이그레이션 빌드는 Windows(PowerShell, `.ps1`) 및 macOS/Linux(Bash, `.sh`) 양대 개발 실행 환경 상에서 대칭형 컨트롤 스크립트 도구를 통해 멱등성 있게 일제히 제어될 수 있어야 합니다.

### Key Entities *(include if feature involves data)*

- **User**: 가계부 및 보안 메일 발송 주소, 알림 설정을 소유하는 최상위 마스터 데이터 엔티티
- **Ledger**: 복합 고유 제약조건이 하드 인덱싱 적용되는 가계부 마스터 거래 데이터 엔티티
- **UserPushSubscription**: 동일 유저 단말의 Web Push 구독 엔드포인트를 고유 식별하는 엔티티

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `python manage.py migrate` 명령 구동 시, 단 한 번의 호출로 오류율 0%로 스키마 빌드가 완벽히 성공해야 합니다.
- **SC-002**: 중복 거래 적재 차단 기능이 활성화되었을 때, 10,000건의 동시 중복 거래 유입 시도가 있더라도 단 1건의 복사 적재도 없이 100% 안전하게 무결성 위배로 전량 예방 차단되어야 합니다.
- **SC-003**: 로컬 데이터베이스의 가상 볼륨 완전 소멸 및 컨테이너 초기 부팅, 그리고 마이그레이션 일제 반영에 소요되는 전체 처리 시간이 **2초 이내**로 완수되어야 합니다.

## Assumptions

- PostgreSQL 18-alpine 공식 Docker 컨테이너 RDBMS 인프라가 로컬 디버깅 LAN 환경에 안정적으로 기동 중임을 전제합니다.
- 데이터베이스의 한글 문자셋 무결성을 위해 client_encoding=UTF8 명세 적용 및 Asia/Seoul 서울 시간대 기준 연동이 유지됨을 전제합니다.
- 1주차에서 기구축된 `User`, `Ledger`, `UserPushSubscription` 마스터 설계 및 명세 범주를 위배하지 않고 고유 제약 정합성만을 견고히 보강함을 약속합니다.

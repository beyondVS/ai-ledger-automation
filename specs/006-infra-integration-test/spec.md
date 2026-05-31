# Feature Specification: 1주차 인프라 중간 점검 및 로컬 통합 테스트 수행 (Infra Integration Test)

**Feature Branch**: `006-infra-integration-test`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "1주차 인프라 중간 점검 및 로컬 통합 테스트 수행. 테스트 전용 DB를 가동하여 [로컬 PDF 파일 업로드 -> 원시 텍스트 파싱 -> Django ORM 기반 원시 쿼리 적재] 흐름의 무결성 검증 및 Git 형상 관리 개시."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 정상적인 PDF 영수증 통합 인입 및 Django ORM 적재 (Priority: P1)

로컬 파일시스템 내에 위치한 실제 PDF 포맷 영수증 파일을 로드하여, 시스템이 백그라운드 인프라와 결합하여 PDF 내부 텍스트 레이어를 완벽히 파싱하고 Django ORM 트랜잭션 세션 하에 `ledgers` 및 `ledger_items` 테이블에 데이터를 이탈 없이 완전히 영속 적재하는 여정입니다.

**Why this priority**: 이것은 1주차 개발 완료를 입증하는 가장 핵심적인 마일스톤 무결성 시나리오로, DB와 파서 모듈의 결합이 완벽히 가동됨을 보장해야 다음 단계(Phase 2 LLM 고도화)로 진입할 수 있습니다.

**Independent Test**: 로컬에 기동된 테스트 전용 PostgreSQL 컨테이너에 실제 PDF 바이트 스트림을 전송하여, 에러 없이 테이블에 삽입되고 정상 쿼리가 수행됨으로써 검증할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 로컬 테스트 DB 컨테이너가 성공적으로 기동되어 있고 마이그레이션이 완료된 상태에서,
   **When** `backend/tests/resources/receipt_sample.pdf` 파일을 로드하여 `PDFTextExtractor`와 Django ORM 적재 서비스를 기동했을 때,
   **Then** `Ledger.objects.filter(...)` 및 `LedgerItem.objects.all()` 데이터베이스 조회 쿼리를 수행했을 때 PDF에 수록된 거래 내역 레코드가 단 한 글자의 한글 깨짐 없이 온전히 존재함을 보장합니다.

---

### User Story 2 - 중복 영수증 유입 차단 및 DLQ 격리 통합 검증 (Priority: P2)

동일한 사용자가 같은 날짜, 같은 가맹점, 같은 총액을 지닌 영수증 PDF를 연속으로 업로드할 때, 고유 인덱스 제약에 부딪혀 2번째 레코드는 안전하게 롤백되고 `FailedTask` 테이블에 원시 페이로드가 누락 없이 보존 적재되는 여정입니다.

**Why this priority**: 헌법 제I조(데이터 무결성 최우선)와 제II조(FailedTask DLQ 격리)를 실전 통합 아키텍처 환경에서 완벽히 수호하는지 확인하기 위해 필수적입니다.

**Independent Test**: 동일한 PDF를 연속 2회 임포트 테스트하여 2차 삽입 시 DB 예외가 트리거되고 `FailedTask` DB 레코드가 정상적으로 적재 및 직렬화 복원되는 것을 검증합니다.

**Acceptance Scenarios**:

1. **Given** 1차 PDF 적재가 무사히 완료된 상태에서,
   **When** 동일한 사용자로 동일한 영수증 PDF 데이터를 2차 인서트 수행했을 때,
   **Then** `IntegrityError` 예외가 발생하고 트랜잭션이 전역 롤백되며, `FailedTask.objects.filter(task_type="API_LEDGER_INGEST_DUPLICATE")`에 해당 실패 원시 페이로드가 이탈 없이 정확하게 기록됩니다.

---

### User Story 3 - 크로스 플랫폼 대칭 원클릭 통합 검증 CLI 가동 (Priority: P3)

윈도우 파워쉘 및 Unix/macOS 배시 환경에서 단 한 줄의 터미널 명령만으로 테스트 DB 기동부터 통합 테스트 수행, 그리고 테스트 자원의 멱등적 회수까지 전체 워크플로우를 자동화하는 가동 여정입니다.

**Why this priority**: 헌법 제VI조(크로스 플랫폼 대칭 툴링)를 준수하여 개발자가 수동 셋업 오버헤드 없이 언제 어디서나 멱등적인 통합 테스트를 가동할 수 있게 보장하기 위함입니다.

**Independent Test**: 윈도우 환경에서 `.ps1` 스크립트를, WSL/Mac 환경에서 `.sh` 스크립트를 기동하여 15초 이내에 모든 과정이 에러 없이 무사 완수되는 것을 확인하여 검증합니다.

**Acceptance Scenarios**:

1. **Given** 윈도우 또는 macOS/Linux 터미널 환경에서,
   **When** 루트 디렉토리의 통합 테스트 전용 스크립트(`scripts/run-pdf-tests`)를 기동했을 때,
   **Then** 추가적인 입력이나 에러 없이 DB 셋업, 마이그레이션, pytest 실행, 자원 회수까지 전 과정이 자동으로 성공 실행되고 최종 `PASS` 상태가 출력됩니다.

### Edge Cases

- PDF 내부에 텍스트 레이어가 완전히 누락된 스캔 이미지 타입 파일 유입 시 예외 복원 검증
- DB 세션 연결 시간초과 또는 디스크 풀 상태에서의 적재 시도 시 롤백 및 에러 핸들링
- PDF 한글 폰트 부재 상태에서의 한글 파싱 시 NFC 정규화 필터 적용 무손실 복구

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 통합 테스트 가동 시, 격리된 로컬 테스트 전용 Docker PostgreSQL 18-alpine 컨테이너를 우선 기동해야 합니다.
- **FR-002**: 기동된 DB에 Django ORM 마이그레이션 도구를 자동 연동 기동하여 스키마 테이블 구조를 멱등 구축해야 합니다.
- **FR-003**: 시스템은 `PDFTextExtractor` 유틸리티 모듈을 통해 실제 디스크 상의 샘플 PDF 파일 바이트를 NFD 자모 정규화(NFC 복원) 필터와 함께 정밀 파싱해 텍스트 버퍼를 반환해야 합니다.
- **FR-004**: 추출된 영수증 내역은 Django ORM의 `transaction.atomic()` 격리 레벨 블록 내에서 메인 ledger 레코드와 ledger_items 배열로 완벽히 커밋 삽입되어야 합니다.
- **FR-005**: 중복 결제 적재 혹은 DB 트랜잭션 도중 시스템 크래시 시, 기존 인서트 분은 완전 롤백되어 데이터 파편화가 0%여야 합니다.
- **FR-006**: 통합 테스트 수행 완료 즉시 가동된 테스트용 DB 컨테이너와 볼륨을 자동으로 안전하게 회수(Cleanup)하여 로컬 시스템 자원 잔존을 차단하고 멱등성을 수호해야 합니다.
- **FR-007**: 1종의 무결한 정적 영수증 PDF(receipt_sample.pdf)를 표준 샘플로 기용하여 정상적인 파싱 및 트랜잭션 적재 정합성을 집중 검증합니다.

### Key Entities *(include if feature involves data)*

- **Ledger (가계부 마스터)**: 영수증 1장의 거래 기본 정보를 가집니다. (거래 일자, 가맹점명, 가맹점 사업자등록번호, 총 거래액, 부가세, 공급가액 등)
- **LedgerItem (가계부 품목 배열)**: 영수증 내부의 상세 구매 개별 품목 목록입니다. (품목명, 수량, 단가, 총 가격 등)
- **FailedTask (실패 보존 큐 / DLQ)**: 중복 유입 및 적재 실패된 거래 원시 페이로드를 격리 수집 및 저장하는 격리 테이블입니다. (실패 타입, 실패 에러 로그 메시지, 원시 JSON 페이로드 등)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 로컬 PDF 파싱부터 Django DB 원시 트랜잭션 적재 및 DLQ 격리 검증까지의 하이브리드 통합 시나리오가 100% 무결하게 완료되어 녹색불로 통과해야 합니다.
- **SC-002**: 도커 테스트 DB 컨테이너 기동, 마이그레이션, 테스트 코드 구동, 컨테이너 리소스 회수까지의 전체 CLI 기동 타임이 총 **15초 이내**에 완수되어 고속 개발 순환을 수호해야 합니다.
- **SC-003**: 윈도우(PowerShell) 및 UNIX 계열(Bash)에서 대칭적으로 완벽 작동하는 테스트 스크립트 실행 성공률이 100%여야 합니다.

## Assumptions

- 로컬 개발 환경에 Docker Desktop 및 CLI 도구(docker, docker-compose)가 무결하게 설치 및 가동 중이라고 가정합니다.
- 테스트용 PDF 파일(`receipt_sample.pdf`)은 프로젝트 테스트 디렉토리 내부 `backend/tests/resources/` 하위에 안정적으로 영구 존재한다고 가정합니다.
- Git 브랜치 및 로컬 형상 관리가 정상 가동되어 추적되고 있다고 가정합니다.

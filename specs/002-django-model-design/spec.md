# Feature Specification: Django Model Design for AI Ledger

**Feature Branch**: `002-django-model-design`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Django Model 클래스 설계 및 수립. 가계부(Ledger), 품목(LedgerItem), 사용자 정보(User), PWA 푸시 구독(UserPushSubscription), 템플릿 캐싱(MerchantTemplate), 실패 로깅용 FailedTask 모델 정의 완료."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - E2E 가계부 및 세부 품목 트랜잭션 적재 (Priority: P1)

로컬 PDF 업로드나 모바일 촬영을 거쳐 AI 파서 모듈이 정형 분류를 마치면, 시스템은 단일 원자적 데이터베이스 트랜잭션 수명 블록 내에서 부모 가계부 레코드(Ledgers)와 자식 품목 레코드 배열(LedgerItems)을 일괄 영구 적재합니다.

**Why this priority**:
영수증 1장 적재 시 메인 가계부 데이터와 상세품목 리스트 간의 불일치는 가계부 서비스 신뢰성을 전면 붕괴시키는 치명적 장해 요인입니다. 따라서 1:N 원자적 적재(Atomicity)와 무조건적 롤백 수호가 최우선 순위입니다.

**Independent Test**:
임의의 영수증 파싱 가공 JSON 페이로드를 전달하여 데이터베이스 인서트 트랜잭션을 트리거합니다. 상세 품목 연산 도중 예외나 데이터베이스 연결 장해를 발생시켜 메인 가계부 레코드까지 흔적 없이 롤백(Rollback)되어 데이터 파편화가 발생하지 않는지 E2E로 안전하게 독립 검증할 수 있습니다.

**Acceptance Scenarios**:

1. **Given** 정상적인 영수증 마스터 정보와 세부 품목 3개가 포함된 JSON 데이터가 인입되었을 때,
   **When** 단일 트랜잭션 블록 내에서 인서트 연산이 실행되면,
   **Then** `ledgers` 테이블에 1개 행, `ledger_items` 테이블에 연계된 3개 행이 정상 적재되고 커밋에 성공해야 합니다.
2. **Given** 영수증 마스터 정보는 유효하나 세부 품목 인서트 도중 구문 오류나 데이터베이스 단절 예외가 유발되었을 때,
   **When** 트랜잭션 세션이 동작하면,
   **Then** `ledgers` 테이블에 생성되었던 마스터 행까지 전격 롤백되어 데이터베이스에 찌꺼기 레코드가 절대 남지 않아야 합니다.

---

### User Story 2 - 중복 영수증 무차별 복사 차단 (Priority: P2)

사용자가 동일한 영수증이나 청구서를 중복으로 올리거나 실수로 연속 터치하여 업로드한 경우, 시스템은 데이터베이스 복합 유니크 제약 조건을 활용하여 중복 입력을 사전에 안전하게 원천 차단합니다.

**Why this priority**:
가계부 서비스의 통계 왜곡을 예방하고 불필요한 데이터베이스 리소스 고갈 및 스토리지 낭비를 차단하기 위해 두 번째 우선순위로 지정되었습니다.

**Independent Test**:
이미 데이터베이스에 성공적으로 적재 완료된 특정 영수증 데이터(동일 user_id, vendor_registration_number, transaction_date, total_amount 세트)를 다시 한 번 업로드 적재 시도합니다. 시스템이 DB 단에서 중복 키 위배 오류를 감지하고 409 Conflict 또는 사전에 합의된 예외 리포트를 안정적으로 반환하는지 독립 검증합니다.

**Acceptance Scenarios**:

1. **Given** 동일한 사용자가 같은 가맹점 사업자등록번호, 결제 날짜, 최종 결제 금액을 가진 영수증을 2회 연속 첨부하여 업로드를 시도했을 때,
   **When** 2번째 인서트 연산이 실행되면,
   **Then** 데이터베이스 복합 유니크 제약조건에 의해 차단되며, 2번째 결제 내역은 적재되지 않고 에러 로그가 FailedTask에 무결하게 안전 격리 적재되어야 합니다.

---

### User Story 3 - 템플릿 캐싱 바이패스 및 미검증 템플릿 완전 격리 (Priority: P3)

비용 절감을 위해 반복되는 가맹점 사업자등록번호 기반 정적 정규식 캐시 테이블(`merchant_templates`)을 최우선 조회하여 파싱을 우회 처리하되, 시스템 오작동을 예방하기 위해 미검증 캐시는 완벽히 동작 필터에서 차단 제어합니다.

**Why this priority**:
잘못 분류 제안된 정규식 규칙이 bypass 루프에 오인 진입하여 후속 사용자들의 전체 소비 데이터를 오염시키는 대규모 오동작을 격리 예방하기 위한 안전장치입니다.

**Independent Test**:
검증 마크가 거짓(`is_verified: false`) 상태인 템플릿을 데이터베이스에 임의 주입합니다. 해당 사업자등록번호 영수증을 파싱 처리할 때 바이패스 파서가 작동을 완전 우회 차단하고, LLM API 폴백이 정상 가동되는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 특정 사업자등록번호에 대한 정규식 캐시 템플릿의 검증 상태가 `is_verified: false`로 격리 보존되어 있을 때,
   **When** 가계부 파서 파이프라인이 구동되면,
   **Then** 캐시 템플릿은 우회 루프에 반영되지 않고 Gemini AI 파싱 경로를 경유하여 안전하게 처리되어야 합니다.

---

### Edge Cases

- **10자리 사업자등록번호가 존재하지 않는 간이 영수증 유입**:
  사업자등록번호가 기재되지 않은 영수증이 인입될 경우, 시스템은 마이그레이션 및 파서 연산 시 `COALESCE(vendor_registration_number, '0000000000')` 규격을 엄격히 적용하여 무결하게 인서트하고 복합 유니크 비교 시 null 충돌이 발생하지 않도록 방어합니다.
- **비동기 큐 연산 도중 예외 발생 시의 영구 격리 로깅**:
  Gemini AI 파싱 실패나 예외 장해 유발 시, 시스템은 무작정 재시도하여 리소스를 점유하지 않고 `failed_tasks` 테이블에 Dead Letter Queue 패턴으로 원시 무가공 텍스트 및 오류 콜스택 로그를 무결하게 안전 격리 기록합니다.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 서비스 가입 회원 관리 및 이메일 수집 화이트리스트 검증을 위해 `users` 마스터 테이블을 제공해야 합니다.
- **FR-002**: 시스템은 개별 결제 정보 및 공급가액, 부가세, 총액, 원본 LLM 응답 백업(JSONB)을 보존하는 `ledgers` 마스터 테이블을 구현해야 합니다.
- **FR-003**: `ledgers` 마스터 테이블은 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약 조건을 갖추어 중복 결제 인입을 원천 예방해야 합니다.
- **FR-004**: 시스템은 단일 가계부 레코드에 1:N 관계로 매핑되어 단가, 수량, 합계를 보존하는 `ledger_items` 상세품목 테이블을 지원해야 하며, 부모 행 삭제 시 연쇄 삭제(`ON DELETE CASCADE`) 정합성을 보장해야 합니다.
- **FR-005**: 시스템은 가맹점의 사업자번호별 정적 정규식 파싱 규칙 캐시를 보존하기 위해 `merchant_templates` 테이블을 제공해야 하며, 자율 제안되는 정규식은 무조건 `is_verified: false` 격리 통제 필터값으로 적재되어야 합니다.
- **FR-006**: 시스템은 비동기 파싱 실패나 예외 로그 유실을 차단하기 위해 오류 메시지 및 콜스택을 보존하는 Dead Letter Queue 패턴의 `failed_tasks` 테이블을 제공해야 합니다.
- **FR-007**: 시스템은 PWA 백그라운드 푸시 알림 수신을 만족하기 위한 브라우저 푸시 엔드포인트 VAPID 구독 명세를 영구 저장하는 `user_push_subscriptions` 테이블을 제공해야 합니다.

### Key Entities *(include if feature involves data)*

- **User**: 가입 회원 계정 및 수집 화이트리스트 메일 매핑 데이터를 나타내며, `registered_forward_email` 등을 관리합니다.
- **Ledger**: 개별 영수증 결제 마스터 메타데이터 및 LLM 원시 응답(JSONB)을 담는 핵심 엔티티입니다.
- **LedgerItem**: 단일 영수증 내의 세부 개별 품목 명세를 나타내며, Ledger와 외래키(ON DELETE CASCADE) 관계를 형성합니다.
- **MerchantTemplate**: 특정 가맹점의 사업자등록번호와 정규식 파싱 규칙을 담는 비용 최적화용 캐시 엔티티입니다.
- **FailedTask**: 비동기 예외 처리 실패 시 수집 및 격리 적재되는 Dead Letter Queue 로그 엔티티입니다.
- **UserPushSubscription**: VAPID v2 표준 웹 푸시 수신 명세를 관리하는 구독 엔티티입니다.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 영수증 1장 적재 시 `ledgers` 마스터 레코드와 `ledger_items` 상세품목 레코드 배열 생성 연산은 100% 단일 Django ORM 트랜잭션 블록(`transaction.atomic()`) 내에서 실행되어야 하며, 임의의 오류 시 100% 전격 롤백을 기계적으로 보장해야 합니다.
- **SC-002**: 기 적재된 데이터와 동일 정보(동일 사용자, 사업자등록번호, 결제 날짜, 총액) 인서트 시도 시, 데이터베이스 복합 유니크 제약 조건을 거쳐 100% 원천 차단 및 감지가 보장되어야 합니다.
- **SC-003**: 템플릿 캐시 조회 시 수동 검증 승인 마크(`is_verified: true`)가 획득된 정규식 템플릿 규칙만 우회 바이패스에 반영되어야 하며, 미검증 템플릿(`is_verified: false`)의 바이패스 진입율은 상시 0%여야 합니다.

---

## Assumptions

- PostgreSQL v18+을 메인 관계형 데이터베이스로 사용하며, 강력한 ACID 트랜잭션 격리 연산을 지원합니다.
- 모델 식별자는 기본적으로 UUID 형식을 차용하여 Native UUIDv7 등의 장점을 누리도록 유도합니다.
- 파싱되지 않은 원본 멀티모달 LLM 응답은 PostgreSQL의 JSONB 컬럼을 활용해 구조적 훼손 없이 안전하게 보존합니다.
- `ledger_items` 테이블은 부모 테이블 연쇄 삭제(`ON DELETE CASCADE`) 참조가 완벽히 보장됩니다.

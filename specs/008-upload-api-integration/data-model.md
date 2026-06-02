# Data Model Design: Upload API Integration & Async Schema Design

## 1. Key Entities

### Entity 1: ReceiptUploadJob (영수증 업로드 작업 - 가상/플레이스홀더 및 향후 실물 대응)
- **Description**: 사용자의 영수증 처리 요청을 식별하고 가상/실제 비동기 작업 진행 상황을 추적하기 위한 데이터 엔티티입니다.
- **Attributes**:
  - `job_id` (UUIDv7, Primary Key): 작업 고유 식별자 (3주차 Celery Task ID 대응용 플레이스홀더)
  - `status` (String): 진행 상태. 허용 값: `"PENDING"`, `"PROCESSING"`, `"COMPLETED"`, `"FAILED"`. (동기 응답 시 항상 `"COMPLETED"`)
  - `created_at` (DateTime): 작업 요청 시각
  - `updated_at` (DateTime): 작업 상태 갱신 시각

### Entity 2: Ledger (가계부 마스터)
- **Description**: 분석 완료된 영수증의 종합 금융 거래 마스터 레코드입니다.
- **Attributes**:
  - `id` (UUID, Primary Key): 가계부 고유 키
  - `user_id` (UUID, ForeignKey): 가계부 소유 사용자 식별자
  - `vendor_registration_number` (String, 10자): 가맹점의 10자리 사업자등록번호
  - `transaction_date` (Date): 거래 일자
  - `total_amount` (Decimal, 12, 2): 거래 총 금액
  - `merchant_name` (String): 가맹점명
  - `created_at` (DateTime): 데이터베이스 적재 일시
- **Database Constraints**:
  - **UNIQUE (`user_id`, `vendor_registration_number`, `transaction_date`, `total_amount`)**: 중복 결제 영수증 무단 누적 및 중복 적재 방지를 위한 복합 고유 제약조건 (헌법 제I조 수호)

### Entity 3: LedgerItem (가계부 상세 품목)
- **Description**: 하나의 가계부 마스터 레코드에 종속된 영수증의 구체적인 세부 품목 목록 레코드입니다.
- **Attributes**:
  - `id` (UUID, Primary Key): 상세 품목 고유 키
  - `ledger_id` (UUID, ForeignKey): 소속 가계부 마스터 (`Ledger`) ID
  - `name` (String): 품목명
  - `quantity` (Integer): 구매 수량 (기본값: 1)
  - `price` (Decimal, 12, 2): 품목 단가
- **Database Constraints**:
  - `ledger_id` 에 대해 CASCADE Delete 정책 적용

---

## 2. Validation & Transaction Rules

- **Atomic Transaction Rule**: 
  - 영수증 1장을 적재할 때, `Ledger` 마스터 레코드 생성과 이에 연관된 `LedgerItem` 배열 레코드 적재는 반드시 **단 하나의 Django ORM 트랜잭션 블록(`transaction.atomic()`)** 내에서 원자적으로 처리되어야 합니다.
  - 데이터 유효성 검사 또는 적재 처리 중 네트워크/DBMS 장해 등 일체의 예외 발생 시 전역 롤백합니다.
- **Validation Rules**:
  - `vendor_registration_number`는 공백을 제외한 숫자 10자리 규격만 허용합니다.
  - `total_amount` 및 각 품목의 `price` 합산 정합성을 검증합니다.

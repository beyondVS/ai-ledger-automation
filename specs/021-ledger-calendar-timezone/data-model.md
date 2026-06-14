# Data Model: 데이터 모델 및 스키마 설계

본 문서는 타임존 설정 보존 및 가계부 다차원 복합 필터링 최적화를 수행하기 위한 데이터베이스 스키마 및 인덱스 상세 설계를 다룹니다.

---

## 1. 엔티티 구조 (Entity Layout)

### UserAccount (사용자 계정 확장 모델)
사용자의 인증 및 커스텀 환경설정을 관리하는 핵심 모델입니다.

| 필드명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key (Native UUIDv7) | 사용자 고유 식별자 |
| `email` | `VARCHAR(254)` | Unique, Not Null | 사용자 로그인 이메일 |
| `timezone` | `VARCHAR(100)` | Not Null, Default: 'Asia/Seoul' | IANA 표준 사용자 선호 타임존 명칭 (예: "Asia/Seoul", "America/New_York") |

* **데이터 유효성 검증**:
  * 백엔드 저장 시 파이썬 `zoneinfo.available_timezones()` 집합 내에 존재하는 유효한 IANA 타임존 문자열인지 강제 검증합니다. 잘못된 값 입력 시 `ValidationError`를 유발합니다.

### Ledger (가계부 거래 마스터 모델)
사용자의 지출 거래 내역을 보존하는 모델입니다.

| 필드명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key (Native UUIDv7) | 가계부 거래 고유 식별자 |
| `user_id` | `UUID` | Foreign Key (UserAccount.id), Not Null | 소유 사용자 관계 |
| `transaction_datetime` | `TIMESTAMP WITH TIME ZONE` | Not Null | 거래 발생 일시 (글로벌 표준 정합성을 위해 DB에는 항상 UTC 기준 절대 시간 저장) |
| `vendor_name` | `VARCHAR(255)` | Not Null | 가맹점 상호명 (다차원 부분 일치 검색 대상) |
| `category_id` | `UUID` | Foreign Key (Category.id), Nullable | 가맹점 소비 카테고리 (유효하지 않을 시 '미분류' 폴백 매핑) |
| `total_amount` | `NUMERIC(15, 2)` | Not Null | 거래 총 지출 금액 |
| `currency` | `VARCHAR(3)` | Not Null, Default: 'KRW' | 거래 통화 규격 (ISO 4217 코드) |
| `approval_number` | `VARCHAR(50)` | Nullable | 카드 승인번호 (동일 결제 60초 윈도우 중복 방어 대조용) |

---

## 2. 데이터베이스 인덱스 설계 (Indexing & Optimization)

성공 기준(SC-003)인 500ms 이내 필터링 응답 속도를 달성하기 위해 PostgreSQL v18 데이터베이스 레이어에 다음과 같은 인덱스를 설계 및 구축합니다.

### 1. 사용자 기준 시계열 정렬 복합 인덱스 (Composite Index)
* **정의**: `INDEX ledger_user_time_idx ON ledgers(user_id, transaction_datetime DESC);`
* **타당성**: 모든 가계부 목록 및 캘린더 조회는 특정 로그인 사용자에 국한되어 일어나며, 결제일시 기준 최신순 정렬이 수반됩니다. 이 인덱스는 Full Table Scan을 완전히 배제하고 인덱스 스캔을 보장합니다.

### 2. 가맹점 상호명 부분 문자열 검색 인덱스 (Trigram Index)
* **정의**: `CREATE INDEX ledger_vendor_trgm_idx ON ledgers USING gin (vendor_name gin_trgm_ops);`
* **타당성**: 상호명 검색어(부분 일치) 필터 작동 시 `%검색어%` 형태의 와일드카드 조회에서 인덱스를 활용하기 위해, PostgreSQL의 `pg_trgm` 확장을 사용한 GIN 인덱스를 가동합니다.

---

## 3. 데이터 일관성 및 정합성 제약 (Data Integrity Rules)

* **트랜잭션 원자성**:
  * 신규 영수증 분석을 통해 `Ledger` 및 `LedgerItem` 하위 세부 품목이 적재될 때, Django ORM의 `transaction.atomic()`을 적용하여 중간 오류 시 전역 롤백 처리합니다.
* **시간대 보정 파이프라인**:
  * 결제 데이터 수집 및 영수증 파싱 비동기 태스크 시, 사용자의 `UserAccount.timezone` 정보를 로드하여 파싱된 로컬 시간 값을 timezone-aware 날짜 객체로 전환한 후, 최종적으로 데이터베이스 저장 시 Django ORM에 의해 자동으로 UTC 기준 타임스탬프로 저장되도록 통제합니다.

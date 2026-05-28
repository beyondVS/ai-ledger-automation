# Data Model Specification: Django Models for AI Ledger

본 설계 명세는 AI 가계부 자동화 프로젝트의 핵심 관계형 데이터 보존 레이어를 위한 6대 Django Model의 상세 스펙을 정의합니다. 헌법 v1.2.0의 트랜잭션 원자성, 중복 인서트 방지, 비용 최적화 격리 원칙이 데이터 구조 상에서 완벽히 수호되도록 설계되었습니다.

---

## 1. 개요 및 인프라 매핑 (Database & Framework)

- **프레임워크**: Python 3.11 + Django Web Framework (Django ORM)
- **데이터베이스**: PostgreSQL v18+
- **주요 물리적 특징**:
  - 모든 기본 키(PK)는 시계열 정렬 및 물리적 인덱스 페이지 스플릿(Page Split)을 방지하는 **Native UUIDv7**을 사용합니다.
  - LLM 원시 응답 및 복합 정규식 룰은 원형 그대로 구조적 보존이 가능한 PostgreSQL **JSONB** 필드를 활용합니다.
  - 가계부와 상세 품목은 `ON DELETE CASCADE`로 연계되어 물리적 정합성을 영구 보존합니다.

---

## 2. 6대 핵심 엔티티 상세 스펙 (Entity Specifications)

### 2.1 User (사용자 계정 및 이메일 수집 화이트리스트)
- **설명**: 회원가입 계정을 관리하며, 이메일 인바운드 수집 시 스팸 공격을 원천 방어하기 위한 발송인 화이트리스트 이메일 매핑 데이터(최대 3개)를 보존합니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `email` | `EmailField` | `VARCHAR(254)` | `Unique, NOT NULL` | 주 회원가입 이메일 주소 |
| `registered_forward_email_1` | `EmailField` | `VARCHAR(254)` | `Null=True` | 화이트리스트 발송인 메일 1 (SPF/DKIM 매핑) |
| `registered_forward_email_2` | `EmailField` | `VARCHAR(254)` | `Null=True` | 화이트리스트 발송인 메일 2 (SPF/DKIM 매핑) |
| `registered_forward_email_3` | `EmailField` | `VARCHAR(254)` | `Null=True` | 화이트리스트 발송인 메일 3 (SPF/DKIM 매핑) |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 계정 생성 일시 |
| `updated_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now=True` | 계정 정보 수정 일시 |

- **정합성 및 유효성 검증 규칙**:
  - `email`은 유효한 RFC 5322 이메일 규격을 준수해야 합니다.
  - 화이트리스트 이메일 주소는 최대 3개까지만 등록할 수 있으며, 인바운드 웹훅 인입 시 SPF 및 DKIM 검증을 마친 발신인 헤더 주소와 이 3개 필드 중 하나가 100% 대조 일치해야 비동기 큐에 적재를 허용합니다.

---

### 2.2 Ledger (가계부 마스터 결제 정보)
- **설명**: 영수증 단위의 전체 지출 마스터 정보를 보존하며, 동일 영수증의 무차별 중복 입력을 DB 단에서 완벽히 원천 차단하는 복합 유니크 제약조건을 장착합니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `user` | `ForeignKey` | `UUID (v7)` | `ON DELETE CASCADE` | User 엔티티 참조 외래 키 |
| `vendor_registration_number`| `CharField(10)`| `VARCHAR(10)` | `NOT NULL, Default='0000000000'`| 10자리 가맹점 사업자등록번호 |
| `vendor_name` | `CharField(255)`| `VARCHAR(255)` | `NOT NULL` | 가맹점명 (상호명) |
| `transaction_date` | `DateField` | `DATE` | `NOT NULL` | 결제 일자 (거래 발생일) |
| `total_amount` | `DecimalField` | `NUMERIC(12, 2)`| `NOT NULL` | 최종 결제 금액 (총액) |
| `supply_value` | `DecimalField` | `NUMERIC(12, 2)`| `NOT NULL` | 공급 가액 |
| `vat_amount` | `DecimalField` | `NUMERIC(12, 2)`| `NOT NULL` | 부가세 세액 |
| `raw_llm_response` | `JSONField` | `JSONB` | `Null=True` | Gemini AI 분석 성공 원시 응답 JSON 백업 |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 가계부 적재 일시 |
| `updated_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now=True` | 가계부 수정 일시 |

- **정합성 및 유효성 검증 규칙**:
  - **복합 UNIQUE 제약**: `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 제약을 적용하여 동일 사용자의 무차별 중복 영수증 입력을 DB 단에서 방어합니다.
  - **Edge Case 방어**: 10자리 사업자등록번호가 식별되지 않는 간이 영수증이 유입되는 경우, NULL 충돌로 인한 UNIQUE 제약 무력화를 방지하기 위해 기본값 `'0000000000'`으로 물리 강제 치환(`COALESCE`) 적재합니다.
  - **비즈니스 합산 검증**: `total_amount = supply_value + vat_amount` 등식의 산술 정합성을 인서트/수정 전에 교차 검증합니다.

---

### 2.3 LedgerItem (가계부 품목 상세 명세)
- **설명**: 단일 영수증(`Ledger`) 내에 포함된 개별 상세 구매 품목 명세를 1:N 관계로 영구 매핑 보존합니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `ledger` | `ForeignKey` | `UUID (v7)` | `ON DELETE CASCADE` | 부모 Ledger 참조 외래 키 |
| `item_name` | `CharField(255)`| `VARCHAR(255)` | `NOT NULL` | 개별 상세 품목명 |
| `quantity` | `IntegerField` | `INTEGER` | `NOT NULL, Default=1` | 수량 |
| `unit_price` | `DecimalField` | `NUMERIC(12, 2)`| `NOT NULL` | 개별 품목 단가 |
| `total_price` | `DecimalField` | `NUMERIC(12, 2)`| `NOT NULL` | 품목 합산 가격 (`quantity * unit_price`) |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 상세 품목 적재 일시 |

- **정합성 및 유효성 검증 규칙**:
  - **원자적 생존 참조**: 부모 가계부 행이 전면 소멸(Delete)하면 상세 품목들 또한 `ON DELETE CASCADE` 참조 무결성 규칙에 의해 흔적 없이 자동 연쇄 연동 삭제됩니다.
  - **양수 조건 제약**: `quantity`는 무조건 1 이상이어야 하며, `unit_price` 및 `total_price`는 0 이상이어야 합니다.
  - **산술 검증**: `total_price = quantity * unit_price` 산술 검증을 물리 모델 저장 전에 기계적으로 확인합니다.

---

### 2.4 MerchantTemplate (비용 최적화 가맹점 레이아웃 캐시)
- **설명**: 동일 가맹점 사업자등록번호 인입 시 유료 멀티모달 LLM API의 호출을 취소하고 로컬 바이패스(Bypass) 파서를 구동하기 위한 정적 정규식 규칙 캐시 테이블입니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `vendor_registration_number`| `CharField(10)`| `VARCHAR(10)` | `Unique, NOT NULL` | 10자리 가맹점 사업자등록번호 |
| `vendor_name` | `CharField(255)`| `VARCHAR(255)` | `NOT NULL` | 가맹점 상호명 |
| `parsing_rules` | `JSONField` | `JSONB` | `NOT NULL` | 정규식 레이아웃 파싱 규칙 세트 JSON |
| `is_verified` | `BooleanField`| `BOOLEAN` | `NOT NULL, Default=False`| 어드민 수동 승인 신뢰 마크 플래그 |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 규칙 생성 일시 |
| `updated_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now=True` | 규칙 최종 수정 일시 |

- **정합성 및 유효성 검증 규칙**:
  - **Bypass 격리 통제 필터**: AI 자율 진화 파이프라인에서 생성되어 적재되는 템플릿의 `is_verified` 기본값은 **반드시 `False`**여야 합니다.
  - **실서비스 바이패스 차단**: 쿼리 조회 시 오직 수동 검토 완료 및 신뢰가 확보되어 `is_verified: True` 상태로 격상된 캐시 정규식 규칙만 파싱 엔진 바이패스에 반영하며, 미검증 캐시(`False`)는 우회 루프 진입율을 영구히 0%로 완벽하게 차단하여 타 사용자들의 가계부 데이터 오염 장해를 원천 격리 방어합니다.

---

### 2.5 FailedTask (비동기 예외 격리용 Dead Letter Queue)
- **설명**: 비동기 Celery 워커 내부에서 이미지 리사이징, 메일 웹훅 파싱, LLM API 호출 등 백그라운드 연산 실패 시 무작정 재시도를 반복하여 자원을 낭비하지 않고, 원시 예외 콜스택 로그 및 무가공 텍스트를 격리하여 안전 적재하는 테이블입니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `user` | `ForeignKey` | `UUID (v7)` | `ON DELETE SET_NULL, Null=True` | 연관 User 참조 (탈퇴 시 Null 처리) |
| `task_type` | `CharField(50)`| `VARCHAR(50)` | `NOT NULL` | Celery 작업 식별 분류 (예: 'EMAIL_WEBHOOK', 'IMAGE_Pillow') |
| `raw_payload` | `TextField` | `TEXT` | `NOT NULL` | 실패 시점의 원시 텍스트/JSON 페이로드 |
| `error_message` | `TextField` | `TEXT` | `NOT NULL` | 발생한 핵심 예외(Exception) 메시지 |
| `error_stacktrace` | `TextField` | `TEXT` | `NOT NULL` | 예외 발생 시점의 상세 디버깅 콜스택 |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 에러 로그 생성 일시 (격리 시점) |

- **정합성 및 유효성 검증 규칙**:
  - 비동기 처리 장해 시, API 응답 흐름이나 큐 프로세스를 중단 및 마비시키는 런타임 오류 폴백을 전면 차단하고, 발생 사태에 대한 디버깅 단서를 이 모델에 완벽히 격리한 후 에러 수준 로깅을 종결합니다.

---

### 2.6 UserPushSubscription (PWA 브라우저 VAPID 푸시 구독 정보)
- **설명**: 백그라운드 PWA 클라이언트 상태에서 VAPID v2 프로토콜을 준수하며 모바일 기기에 타겟 푸시 알림을 즉각 디스패치하기 위한 브라우저 고유 Web Push 구독 엔드포인트 세부 정보를 영구 보존합니다.

| 필드명 | Django 타입 | DB 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `UUIDField` | `UUID (v7)` | `Primary Key` | Native UUIDv7 기본 키 |
| `user` | `ForeignKey` | `UUID (v7)` | `ON DELETE CASCADE` | User 엔티티 참조 외래 키 |
| `endpoint` | `URLField` | `TEXT` | `Unique, NOT NULL` | 브라우저 푸시 게이트웨이 엔드포인트 URL |
| `p256dh` | `CharField(255)`| `VARCHAR(255)` | `NOT NULL` | VAPID 암호화 클라이언트 퍼블릭 키 |
| `auth` | `CharField(255)`| `VARCHAR(255)` | `NOT NULL` | VAPID 인증 시크릿 인증 키 |
| `created_at` | `DateTimeField` | `TIMESTAMP WITH TZ`| `auto_now_add=True` | 구독 영구 등록 일시 |

- **정합성 및 유효성 검증 규칙**:
  - `endpoint`는 고유(Unique)해야 하며 중복 브라우저 채널 생성을 차단합니다.
  - VAPID 암호화 표준 키 크기 및 포맷 명세 유효성을 검증하며, 회원 탈퇴 시 `ON DELETE CASCADE` 연쇄 소멸 정합성을 가집니다.

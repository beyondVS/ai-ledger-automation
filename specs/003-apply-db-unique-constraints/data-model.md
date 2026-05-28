# Data Models & Constraints Specification

**Feature**: Database Migration and Unique Constraints
**Branch**: `003-apply-db-unique-constraints`
**Date**: 2026-05-29

본 문서에서는 중복 적재 방어 및 데이터 무결성 강화를 위해 각 비즈니스 모델에 주입될 데이터베이스 레이아웃 및 제약조건 명세를 상세화합니다.

---

## 1. User Entity (사용자 계정 마스터)

* **정의**: 시스템의 모든 소유권 및 결제, 화이트리스트 메일 정보를 소유하는 마스터 계정
* **물리 테이블명**: `accounts_user`
* **세부 속성 명세**:

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | UUID (v7) | Primary Key | 시계열 자동 정렬되는 기본 고유 식별자 |
| `email` | VarChar(255) | Unique | 로그인용 고유 이메일 계정 주소 |
| `registered_forward_email_1` | VarChar(255) | Nullable | 1차 스팸 방어용 화이트리스트 메일 |
| `registered_forward_email_2` | VarChar(255) | Nullable | 2차 스팸 방어용 화이트리스트 메일 |
| `registered_forward_email_3` | VarChar(255) | Nullable | 3차 스팸 방어용 화이트리스트 메일 |

---

## 2. UserPushSubscription Entity (웹 푸시 단말 구독)

* **정의**: VAPID v2 Web Push 명세를 기반으로 사용자 단말의 알림 수신 정보를 저장
* **물리 테이블명**: `accounts_userpushsubscription`
* **복합 고유 제약조건 (UniqueConstraint)**:
  - **제약명**: `unique_user_push_subscription`
  - **대상 필드 조합**: `['user', 'endpoint']`
  - **목적**: 동일 사용자가 특정 알림 단말을 중복 등록하여 브라우저 알림이 다중 발송되는 현상을 데이터베이스 레이어에서 원천 차단

---

## 3. Ledger Entity (가계부 마스터 원장)

* **정의**: 영수증 한 장의 분석 결과를 대표하는 핵심 지출 거래 내역
* **물리 테이블명**: `ledgers_ledger`
* **세부 속성 명세**:

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | UUID (v7) | Primary Key | 시계열 인덱싱 정렬 PK |
| `user` | ForeignKey | ON DELETE CASCADE | 사용자 계정 외래키 매핑 |
| `vendor_registration_number` | VarChar(10) | Default='0000000000' | 10자리 가맹점 사업자등록번호. 결락(null) 시 '0000000000' 강제 보정. |
| `transaction_date` | Date | Not Null | 결제 거래 발생일자 |
| `total_amount` | Decimal(12, 2) | Not Null | 최종 영수증 총액 |

* **복합 고유 제약조건 (UniqueConstraint)**:
  - **제약명**: `unique_ledger_transaction`
  - **대상 필드 조합**: `['user', 'vendor_registration_number', 'transaction_date', 'total_amount']`
  - **목적**: 동일 가계부 거래가 중복 생성(Insert)되는 불상사를 DB 레이어에서 철저하게 원천 차단하여 통계 데이터 왜곡 방지

---

## 4. LedgerItem Entity (상세 품목 세부 레코드)

* **정의**: Ledger 마스터 원장에 귀속되는 1:N 형태의 구매 품목 정보
* **물리 테이블명**: `ledgers_ledgeritem`
* **세부 속성 명세**:

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | UUID (v7) | Primary Key | 기본 식별자 PK |
| `ledger` | ForeignKey | ON DELETE CASCADE | 부모 가계부 외래키. 부모 삭제 시 상세 품목 자동 연쇄 삭제. |
| `item_name` | VarChar(255) | Not Null | 구매 품목명 |
| `quantity` | Integer | Default=1 | 구매 수량 |
| `unit_price` | Decimal(12, 2) | Not Null | 개당 단가 |
| `total_price` | Decimal(12, 2) | Not Null | 수량 * 단가 합산 가격 |

---

## 5. FailedTask Entity (Dead Letter Queue 예외 로그)

* **정의**: 중복 적재 차단 또는 비동기 AI 파싱 등 비즈니스 로직 처리 중 발생한 물리 장해 정보를 격리 수집
* **물리 테이블명**: `tasks_failedtask`
* **세부 속성 명세**:

| 필드명 | 타입 | 제약조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | UUID (v7) | Primary Key | 시계열 PK |
| `task_id` | VarChar(255) | Unique | Celery 태스크 고유 식별자 |
| `error_message` | TextField | Not Null | 오류 원시 메시지 요약 |
| `stack_trace` | TextField | Nullable | 원시 예외 오류 콜스택 (Traceback) 정보 |

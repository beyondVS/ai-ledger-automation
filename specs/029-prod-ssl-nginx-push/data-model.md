# Data Model Specification: Production SSL & E2E Notification Release

**Feature**: `029-prod-ssl-nginx-push`

## 1. Relational Database Schema (PostgreSQL)

가계부 알림망 및 PWA 브라우저 단말과의 웹푸시 구독 상태를 데이터베이스 레이어에서 멱등성 있게 관리하기 위해 아래 두 엔티티를 정의합니다.

### 1.1 `PushSubscription` (웹 푸시 구독 정보)
사용자 브라우저 단말의 웹푸시 구독 권한 승인 정보를 저장하며, 단말의 만료나 무효화 시 비활성화 처리합니다.

| 필드명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT` | `PRIMARY KEY`, `AUTO_INCREMENT` | 고유 식별자 |
| `user_id` | `UUID` | `FOREIGN KEY` (User.id), `NOT NULL` | 구독 소유자 (가계부 사용자) |
| `endpoint` | `TEXT` | `NOT NULL` | FCM/APNs 푸시 서버의 구독 엔드포인트 URL |
| `p256dh` | `VARCHAR(255)` | `NOT NULL` | 푸시 페이로드 암호화를 위한 클라이언트 공개 키 |
| `auth` | `VARCHAR(255)` | `NOT NULL` | 푸시 서비스 메시지 인증용 비밀 토큰 |
| `is_active` | `BOOLEAN` | `DEFAULT True`, `NOT NULL` | 현재 활성 상태 여부 (404/410 수신 시 False) |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP`, `NOT NULL` | 최초 생성 일시 |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP`, `ON UPDATE CURRENT_TIMESTAMP`, `NOT NULL` | 마지막 수정 일시 |

- **복합 고유 제약조건 (Composite Unique Key)**:
  - `UNIQUE (user_id, endpoint)`: 한 사용자가 동일한 단말/브라우저로 여러 번 구독 등록을 시도하더라도 중복 레코드가 쌓이지 않고 기존 레코드가 업데이트(Upsert)되도록 멱등성을 인덱스 레이어에서 강력히 규제합니다.

### 1.2 `NotificationLog` (알림 발송 로그)
백엔드 Celery 작업에 의해 트리거된 알림의 전송 이력 및 상태를 영속화하여 모니터링 및 수신 확인(ACK) 처리에 활용합니다.

| 필드명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `UUID (v7)` | `PRIMARY KEY` | Native UUIDv7 기반의 정렬 가능한 고유 식별자 |
| `user_id` | `UUID` | `FOREIGN KEY` (User.id), `NOT NULL` | 알림 수신 사용자 |
| `type` | `VARCHAR(50)` | `NOT NULL` | 알림 유형 (`RECEIPT_SUCCESS`, `RECEIPT_FAIL`, `BUDGET_80`, `BUDGET_100`) |
| `status` | `VARCHAR(20)` | `DEFAULT 'PENDING'`, `NOT NULL` | 전송 상태 (`PENDING`, `DELIVERED`, `FAILED`) |
| `title` | `VARCHAR(255)` | `NOT NULL` | 알림 제목 |
| `message` | `TEXT` | `NOT NULL` | 알림 세부 본문 내용 |
| `response_code`| `INTEGER` | `NULL` | 푸시 서버(FCM/APNs) 반환 HTTP 상태 코드 |
| `retry_count` | `INTEGER` | `DEFAULT 0`, `NOT NULL` | 일시적 에러 발생 시 재시도 횟수 |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP`, `NOT NULL` | 알림 발생 일시 |
| `updated_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP`, `NOT NULL` | 상태 수정 일시 |

- **Idempotency Key (예산 알림 중복 발송 방지용)**:
  - 동일 월 내에 동일 임계치(80%, 100%)에 해당하는 예산 초과 알림이 여러 번 발생하는 현상을 차단하기 위해, `(user_id, budget_month, type)` 조합의 고유성 대조 로직을 적용합니다.

---

## 2. Client-Side Database Schema (IndexedDB)

네트워크 플래핑 및 오프라인 단말 복귀 시 알림의 유실 없는 영속 캐싱과 정렬을 위해 브라우저 IndexedDB의 로컬 스토리지를 정의합니다.

### 2.1 `CachedNotification` (로컬 캐시 알림 레코드)
단말의 백그라운드 서비스 워커가 웹 푸시를 수신하면 이를 즉시 IndexedDB에 영속화하고, 포그라운드로 진입 시 프론트엔드가 이를 읽어 화면에 렌더링합니다.

| 속성명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | `String (UUIDv7)` | `keyPath`, `unique` | 백엔드와 일치하는 UUIDv7 고유 알림 식별자 |
| `type` | `String` | `NOT NULL` | 알림 유형 (예: `RECEIPT_SUCCESS`) |
| `title` | `String` | `NOT NULL` | 알림 타이틀 |
| `message` | `String` | `NOT NULL` | 알림 내용 상세 |
| `is_read` | `Boolean` | `NOT NULL` | 사용자 읽음 상태 여부 (기본: `false`) |
| `received_at` | `Integer` | `Index 생성` | 수신 시간 타임스탬프 (밀리초) |

- **가비지 컬렉션 (GC) 한도**:
  - IndexedDB 내 데이터 누적에 따른 성능 결함을 막기 위해 **보존 기간 30일 초과 데이터 자동 삭제** 및 **최대 저장 개수 100개 상한**을 초과하는 오래된 알림을 자동 퍼지(Purge)합니다.
  - 가비지 컬렉션 태스크는 브라우저의 트랜잭션 자동 만료(`TransactionInactiveError`)를 예방하기 위해, 30일 초과 삭제와 100개 상한 초과분 삭제 단계를 각각 별도의 독립적인 `readwrite` 트랜잭션으로 격리 수립하여 안전하게 수행합니다.

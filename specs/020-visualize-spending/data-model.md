# Data Model Specification: 소비 시각화 차트 및 예산 게이지 (가계부 UI 고도화 1단계)

본 문서는 대시보드의 예산 게이지 시각화와 실시간 편집을 완벽히 영속화하기 위해 데이터베이스에 신설 및 변경되는 데이터 모델 사양을 정의합니다.

## 1. 신설 엔티티: `MonthlyBudget` (월별 예산)

사용자별로 특정 월에 설정한 지출 목표 금액(예산) 정보를 저장합니다.

### 속성 (Attributes)

| 필드명 | 논리 타입 | 물리 타입 | 제약 조건 | 설명 |
|:---|:---|:---|:---|:---|
| **`id`** | UUIDv7 | `UUID` | Primary Key | 헌법 I조에 의거, 순차 정렬이 가능한 Native UUIDv7 식별자 사용 |
| **`user`** | ForeignKey | `auth.User` (또는 `settings.AUTH_USER_MODEL`) | ON DELETE CASCADE, Nullable=False | 예산의 소유주인 가계부 사용자 |
| **`budget_month`** | Date | `DATE` | Nullable=False | 예산 설정 연월. 매월 1일로 정규화하여 저장 (예: `2026-06-01`은 2026년 6월 전체 예산 의미) |
| **`amount`** | Decimal | `NUMERIC(12, 0)` | Nullable=False, Default=1000000 | 원화(KRW) 기준의 예산 총액 (0원 이상) |
| **`created_at`** | DateTime | `TIMESTAMPTZ` | Auto_now_add=True, Nullable=False | 예산 최초 생성 일시 |
| **`updated_at`** | DateTime | `TIMESTAMPTZ` | Auto_now=True, Nullable=False | 예산 마지막 수정 일시 |

### 유효성 검사 규칙 (Validation Rules)
* **`amount` 검증**: 예산 금액은 반드시 `0` 이상이어야 합니다. 음수 금액이 인입될 경우 HTTP 400 Bad Request를 반환합니다.
* **`budget_month` 검증**: 월의 연월 데이터가 유효한 날짜 규격을 충족해야 합니다.
* **복합 고유 제약조건 (Unique Constraint)**:
  * 물리 레이아웃: `UNIQUE (user_id, budget_month)`
  * 목적: 특정 사용자가 동일한 월에 중복으로 다중 예산 레코드를 생성하는 것을 DB 인덱스 레벨에서 완벽하게 차단합니다.

---

## 2. 기존 엔티티 검토 및 관계

### `LedgerItem` (결제 내역)
* **관계**: `MonthlyBudget`과 직접적인 DB Foreign Key 관계는 맺지 않습니다.
* **집계**: 특정 월의 `LedgerItem` 지출 합계를 집계하여 `MonthlyBudget`의 `amount`와 대조하여 소진 비율을 실시간 계산합니다.
* **집계 시 필터링 규칙**:
  * 결제일시(`transaction_date`) 기준 당월 1일 00:00:00부터 말일 23:59:59 사이의 결제 건을 추출합니다.
  * 카테고리 정보가 유실되었거나 유효하지 않은 값인 경우, 헌법 3조에 의거하여 데이터베이스 상에서 `'미분류'` 카테고리로 안전하게 대치 집계합니다.

# Interface Contracts: Transactional Ledger Service

**Feature**: Database Migration and Unique Constraints
**Branch**: `003-apply-db-unique-constraints`
**Date**: 2026-05-29

본 문서는 백엔드 서비스 레이어 상에서 `Ledger`와 `LedgerItem`을 1:N 원자적으로 생성하는 핵심 트랜잭션 서비스 인터페이스 규격을 계약으로 명세합니다.

---

## 1. create_ledger_transactional Service Contract

* **위치**: `backend/src/apps/ledgers/services.py`
* **역할**: 마스터 가계부 레코드 생성 후 연동 품목 상세 리스트를 단 하나의 데이터베이스 트랜잭션 블록(`transaction.atomic()`) 내에서 영구 적재 및 중복 발생 시 예외 수용.

### 파라미터 시그니처 (Parameters Signature)

```python
def create_ledger_transactional(
    user_id: str,
    transaction_date: str,
    total_amount: float,
    vendor_registration_number: str = "0000000000",
    items: list[dict] = None
) -> dict:
```

* **파라미터 상세 제약**:
  - `user_id`: UUIDv7 규격 문자열 (100% 필수)
  - `transaction_date`: `'YYYY-MM-DD'` 포맷 날짜 문자열 (100% 필수)
  - `total_amount`: 양의 부동 소수점 총 결제 가격 (100% 필수)
  - `vendor_registration_number`: 10자리 사업자등록번호. 누락 시 기본값 `'0000000000'` 자동 주입.
  - `items`: 상세 품목 정보 사전(dict) 배열
    * 각 item 명세: `{"item_name": str, "quantity": int, "unit_price": float, "total_price": float}`

---

## 2. 반환 규격 및 성공/실패 시나리오 계약

### 🟢 성공 시 (Success Return Value)
정합성 테스트 검증 통과 및 정상 적재 완료 시 반환 결과:

```json
{
  "status": "SUCCESS",
  "ledger_id": "01940a02-b230-7411-a8cf-81c82823a31c",
  "items_count": 3,
  "error": null
}
```

### 🔴 실패 시 (Fail Return Value - 중복 적재 발생)
복합 UNIQUE 인덱스에 의해 차단 및 DLQ 격리 완료 시 반환 결과:

```json
{
  "status": "FAILED_DUPLICATE",
  "ledger_id": null,
  "items_count": 0,
  "error": "IntegrityError: duplicate key value violates unique constraint 'unique_ledger_transaction'"
}
```
*(주의: 이 경우 데이터베이스는 `transaction.atomic()`에 의해 전격 롤백되며, 해당 예외 페이로드는 Celery 큐 스로틀링이나 무한 지연 없이 FailedTask 테이블에 즉시 적재 보존됩니다.)*

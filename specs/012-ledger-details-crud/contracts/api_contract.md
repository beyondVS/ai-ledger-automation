# API Contract: Ledger Detail Edit & Delete Modal (CRUD)

## Endpoints Summary

| Method | URL | Description |
| :--- | :--- | :--- |
| **PATCH** | `/api/v1/receipts/<uuid:id>/` | 수동 정정 (가맹점명, 날짜, 금액, 카테고리 수정) |
| **DELETE** | `/api/v1/receipts/<uuid:id>/` | 수동 삭제 (마스터 레코드 및 관련 상세 품목 CASCADE 제거) |

---

## 1. Edit Transaction (PATCH)

Updates fields for a specific ledger transaction owned by the authenticated user.

* **URL**: `/api/v1/receipts/<uuid:id>/`
* **Headers**:
  ```http
  Authorization: Bearer <JWT_ACCESS_TOKEN>
  Content-Type: application/json
  ```
* **Request Payload**:
  ```json
  {
    "vendor_name": "수정된 스타벅스",
    "transaction_date": "2026-06-07",
    "total_amount": "15000.00",
    "category": "식비"
  }
  ```
  *(Note: All fields are optional but must pass validation if present.)*
* **Response (200 OK)**:
  ```json
  {
    "id": "01944e8d-88f5-7c1c-9226-eb52c6f1a8e1",
    "vendor_name": "수정된 스타벅스",
    "vendor_registration_number": "1208112345",
    "transaction_date": "2026-06-07",
    "total_amount": "15000.00",
    "supply_value": "13636.36",
    "vat_amount": "1363.64",
    "category": "식비",
    "created_at": "2026-06-07T16:30:00Z",
    "updated_at": "2026-06-07T17:01:00Z"
  }
  ```
* **Error Responses**:
  * **400 Bad Request**: Validation failed (e.g. empty `vendor_name` or invalid date format).
  * **401 Unauthorized**: JWT Token missing or expired.
  * **403 Forbidden / 404 Not Found**: Attempting to edit a ledger entry belonging to another user.

---

## 2. Delete Transaction (DELETE)

Permanently deletes a specific ledger entry owned by the authenticated user.

* **URL**: `/api/v1/receipts/<uuid:id>/`
* **Headers**:
  ```http
  Authorization: Bearer <JWT_ACCESS_TOKEN>
  ```
* **Response (204 No Content)**:
  *(Empty Body)*
* **Error Responses**:
  * **401 Unauthorized**: JWT Token missing or expired.
  * **403 Forbidden / 404 Not Found**: Attempting to delete a ledger entry belonging to another user.

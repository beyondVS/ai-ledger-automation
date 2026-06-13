# API Contract: Admin Template Management

본 문서는 관리자가 가맹점 템플릿의 자동 승인, 강등, 블랙리스트 및 자가 치유 히스토리를 모니터링하고 관리하기 위한 백엔드 API 계약(Contract)을 정의합니다.

## API Endpoints

### 1. 가맹점 템플릿 목록 조회
관리자 화면에서 자가 치유 상태 및 검증 상태별로 템플릿을 검색하고 필터링합니다.

* **URL:** `/api/admin/templates/`
* **Method:** `GET`
* **Headers:** `Authorization: Bearer <AdminJWTToken>`
* **Query Parameters:**
  * `is_verified` (boolean, optional) - 검증 상태 필터
  * `is_blacklisted` (boolean, optional) - 블랙리스트 차단 상태 필터
  * `vendor_registration_number` (string, optional) - 10자리 사업자등록번호 검색
* **Response (200 OK):**
  ```json
  {
    "count": 12,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "0190562f-4882-7e81-b51e-e265c71a39d2",
        "vendor_registration_number": "1208147526",
        "is_verified": true,
        "is_blacklisted": false,
        "consistency_count": 0,
        "self_healing_attempts": 1,
        "last_healing_at": "2026-06-13T06:00:00Z"
      }
    ]
  }
  ```

---

### 2. 특정 템플릿 실행 및 자가 치유 이력 조회
특정 가맹점 템플릿의 파싱 모드(LLM vs Bypass), 사용자 수동 정정(Diff) 내역, 파싱 오류 내역을 조회합니다.

* **URL:** `/api/admin/templates/{id}/history/`
* **Method:** `GET`
* **Headers:** `Authorization: Bearer <AdminJWTToken>`
* **Response (200 OK):**
  ```json
  {
    "template_id": "0190562f-4882-7e81-b51e-e265c71a39d2",
    "history": [
      {
        "id": "01905634-1c2b-7abc-a912-f01e23a4b5c6",
        "ledger_id": "01905634-1c2b-7abc-a912-f01e23a4b5f9",
        "execution_time": "2026-06-13T06:05:00Z",
        "parsing_mode": "BYPASS",
        "is_success": true,
        "user_corrected": true,
        "corrected_diff": [
          {
            "field": "total_amount",
            "before": 12000,
            "after": 120000
          }
        ],
        "error_message": null
      }
    ]
  }
  ```

---

### 3. 블랙리스트 템플릿 수동 승격 및 검증
관리자가 해당 가맹점의 정규식을 수동으로 확인한 후, 블랙리스트를 강제로 해제하고 검증된 상태로 강제 승격합니다.

* **URL:** `/api/admin/templates/{id}/verify/`
* **Method:** `POST`
* **Headers:** `Authorization: Bearer <AdminJWTToken>`
* **Request Body:**
  ```json
  {
    "regex_pattern": {
      "vendor_name": ".*가맹점명.*",
      "transaction_date": "\\d{4}-\\d{2}-\\d{2}",
      "total_amount": "\\d+"
    }
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Template has been manually verified and promoted.",
    "template": {
      "id": "0190562f-4882-7e81-b51e-e265c71a39d2",
      "is_verified": true,
      "is_blacklisted": false,
      "self_healing_attempts": 0
    }
  }
  ```

---

### 4. 자가 치유 카운터 초기화
연속 자가 치유 실패로 인해 블랙리스트에 오른 템플릿의 치유 카운터와 차단 플래그를 재설정하여 자율 루프에 다시 진입하도록 허용합니다.

* **URL:** `/api/admin/templates/{id}/reset-healing/`
* **Method:** `POST`
* **Headers:** `Authorization: Bearer <AdminJWTToken>`
* **Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Self-healing counter has been reset. Template is ready for auto-promotion loop.",
    "template": {
      "id": "0190562f-4882-7e81-b51e-e265c71a39d2",
      "is_verified": false,
      "is_blacklisted": false,
      "self_healing_attempts": 0
    }
  }
  ```

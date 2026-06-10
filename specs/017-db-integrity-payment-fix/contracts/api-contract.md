# Interface Contracts: API & Component Data Binding

## 1. 결제 데이터 인입 API 계약 (Inbound Payment API Contract)

- **Endpoint**: `POST /api/v1/ledgers/ingest/`
- **Content-Type**: `application/json`

### 1.1 Request Payload
```json
{
  "vendor_registration_number": "1234567890",
  "transaction_date": "2026-06-11T05:40:00+09:00",
  "total_amount": 15500.00,
  "approval_number": "TX-998877",
  "items": [
    {
      "item_name": "맥도날드 1955 버거 세트",
      "unit_price": 8500.00,
      "quantity": 1,
      "category_id": "0190048e-28b9-7561-9c1a-289c89012abc"
    },
    {
      "item_name": "초코 쉐이크 L",
      "unit_price": 3500.00,
      "quantity": 2,
      "category_id": "0190048e-28b9-7561-9c1a-289c89012abc"
    }
  ]
}
```

### 1.2 Responses

#### Case A: 신규 적재 성공 (HTTP 201 Created)
- **상황**: 1분 중복 거래가 아니며 고유 제약조건을 충족하여 DB에 무결하게 신규 삽입 완료된 상태.
- **Response Body**:
```json
{
  "status": "COMPLETED",
  "message": "Payment record ingested successfully.",
  "ledger_id": "0190049f-11b2-7bc9-93e1-28562d9804e1"
}
```

#### Case B: 중복 결제 요청 우회 (HTTP 200 OK)
- **상황**: 승인번호가 동일하거나, 60초 이내에 동일 가맹점/동일 금액으로 재입력되어 중복 데이터로 탐지된 상태. DB 쓰기는 실행되지 않으며(Bypass), 기존 생성되어 있던 `ledger_id`를 반환합니다.
- **Response Body**:
```json
{
  "status": "COMPLETED",
  "message": "Duplicate payment detected; bypassed without creating redundant records.",
  "ledger_id": "0190049f-11b2-7bc9-93e1-28562d9804e1"
}
```

#### Case C: 품목 데이터 오류로 인한 전체 롤백 실패 (HTTP 400 Bad Request)
- **상황**: 마스터는 정상이었으나 품목 배열 내의 특정 속성이 올바르지 않아 트랜잭션이 전체 취소된 상태.
- **Response Body**:
```json
{
  "status": "FAILED",
  "error_code": "TRANSACTION_ROLLBACK",
  "message": "Failed to ingest payment items. Whole transaction has been rolled back.",
  "errors": {
    "items": [
      {
        "quantity": ["Ensure this value is greater than or equal to 1."]
      }
    ]
  }
}
```

---

## 2. FE-05-B 수정 내역 모달 카테고리 데이터 매핑 계약 (UI Component Binding)

프론트엔드 모달 컴포넌트(`LedgerEditModal.vue`)와 거래 내역 수정 API 간의 데이터 연동 구조입니다.

### 2.1 카테고리 목록 조회 API
- **Endpoint**: `GET /api/v1/categories/`
- **Response Body**:
```json
[
  {
    "id": "0190048e-28b9-7561-9c1a-289c89012abc",
    "name": "식비",
    "is_active": true
  },
  {
    "id": "0190048e-28c0-798b-821f-9c882190befd",
    "name": "교통비",
    "is_active": true
  },
  {
    "id": "0190048e-28d1-7c91-a1b2-8c90be9087ea",
    "name": "미분류",
    "is_active": true
  }
]
```

### 2.2 UI 컴포넌트 데이터 바인딩 규칙 (Vue 3)
수정 모달이 로드될 때 API 데이터 매핑 상태 및 예외 방어 모델 구성입니다.

```javascript
// 모달 컴포넌트 내부 상태 정의 (v-model 바인딩 구조)
const formState = ref({
  ledger_id: "",
  total_amount: 0,
  // 카테고리 ID 바인딩 모델
  category_id: "" 
});

// 기존 거래 데이터 로드 및 초기 바인딩 로직
function initializeModal(ledgerData, categoriesList) {
  formState.value.ledger_id = ledgerData.id;
  formState.value.total_amount = ledgerData.total_amount;
  
  // 카테고리 ID 바인딩 누수 방지 방어 코드
  const currentCategoryId = ledgerData.category_id;
  const isCategoryValid = categoriesList.some(cat => cat.id === currentCategoryId);
  
  if (currentCategoryId && isCategoryValid) {
    // 1. 기존 지정 카테고리가 존재하고 활성화 상태이면 해당 ID를 그대로 바인딩
    formState.value.category_id = currentCategoryId;
  } else {
    // 2. 카테고리가 누락(Null)되었거나 이미 삭제/비활성화된 무효 ID인 경우
    //    '미분류' 카테고리 객체를 찾아 바인딩하여 드롭다운 UI에 '미분류'로 자동 노출되도록 제어
    const unclassifiedCategory = categoriesList.find(cat => cat.name === '미분류');
    formState.value.category_id = unclassifiedCategory ? unclassifiedCategory.id : "";
  }
}

// 수정 내역 저장 요청 데이터 페이로드 검증 (PUT /api/v1/ledgers/:id/)
function getSubmitPayload() {
  // 전송 시 category_id 필드가 Null 또는 누락되지 않도록 강제 유효성 방어
  if (!formState.value.category_id) {
    throw new Error("Category must be specified. Fallback to unclassified.");
  }
  return {
    total_amount: formState.value.total_amount,
    category_id: formState.value.category_id
  };
}
```

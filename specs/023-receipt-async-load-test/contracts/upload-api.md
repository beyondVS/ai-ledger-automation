# API Contract: Receipt Bulk Upload API

본 문서는 벌크 영수증 일괄 유입을 처리하는 비동기 업로드 API 엔드포인트의 스키마와 입출력 규격을 정의합니다.

---

## 1. 엔드포인트 개요

* **URL**: `/api/ledgers/receipts/bulk-upload/`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Authentication**: JWT Bearer Token (`Authorization: Bearer <Access_Token>`)
* **역할**: 클라이언트가 최대 50개의 영수증 이미지/PDF 파일을 한 번에 업로드하면, 서버는 유효성 검사 후 즉시 비동기 작업(ReceiptTask)을 큐에 적재하고 접수 정보 및 작업 ID 리스트를 반환합니다.

---

## 2. 요청 명세 (Request)

### 2.1 Request Header
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW
```

### 2.2 Request Body
* `files`: Binary File Array (Multi-part file parameter)
  * 최대 파일 개수 한도: **50개**
  * 개별 파일 최대 용량: **10 MB**
  * 허용되는 미디어 타입: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`

---

## 3. 응답 명세 (Response)

### 3.1 성공 응답 (HTTP 202 Accepted)
API 인입 서버가 50개의 영수증 접수를 완료하고 비동기 Celery 태스크로의 분산 적재를 완료했음을 의미합니다.

* **Response Body (JSON)**:
```json
{
  "message": "50 receipts accepted and successfully queued for asynchronous processing.",
  "tasks": [
    {
      "task_id": "01902047-3fbd-78d1-ba9f-4318357f6a7d",
      "file_name": "receipt_01.jpg",
      "status": "PENDING",
      "created_at": "2026-06-17T00:03:00.000Z"
    },
    {
      "task_id": "01902047-3fbe-7ce2-901d-85fa1b7fcf29",
      "file_name": "receipt_02.png",
      "status": "PENDING",
      "created_at": "2026-06-17T00:03:00.120Z"
    }
  ]
}
```

---

## 4. 에러 응답 (Error Responses)

### 4.1 파라미터 결함 (HTTP 400 Bad Request)
전송된 파일 목록이 없거나, 허용 용량/개수를 초과한 경우입니다.

* **요청 파일이 없는 경우**:
```json
{
  "error": "No files uploaded. Please include 'files' field in form-data."
}
```
* **동시 업로드 제한 개수(50개)를 초과한 경우**:
```json
{
  "error": "Exceeded maximum upload limit of 50 files per request. Uploaded: 52 files."
}
```

### 4.2 인증 인증 실패 (HTTP 401 Unauthorized)
인증 헤더가 유효하지 않거나 만료된 토큰인 경우입니다.

```json
{
  "detail": "Authentication credentials were not provided or token has expired."
}
```

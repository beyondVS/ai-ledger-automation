# API Contract: Asynchronous Receipt Upload & Job Polling

본 문서에서는 클라이언트(프론트엔드)와 메인 웹 API 서버 간에 영수증 파일을 비동기로 안전하게 업로드하고, 백그라운드 작업 처리 상태를 폴링(Polling)하기 위한 인터페이스 규약을 기술합니다.

---

## 1. 영수증 비동기 업로드 접수 API

영수증 파일을 멀티파트 형식으로 서버에 전송하여 백그라운드 큐에 작업을 적재합니다.

* **Endpoint**: `/api/ledgers/upload/`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`

### Request Payload
* **Parameters**:
  - `file`: File (Binary receipt image or PDF) - *Mandatory*

### Response Specification

#### [Success] 202 Accepted
작업이 정상적으로 메시지 큐에 접수되었을 때 즉시 반환되는 응답입니다.
```json
{
  "job_id": "018f3a38-c64a-7182-bcf8-94ef93cf0001",
  "status": "PENDING",
  "created_at": "2026-06-08T17:55:00.123456Z"
}
```

#### [Error] 400 Bad Request
파일이 없거나 지원하지 않는 파일 포맷(이미지/PDF 외의 파일)인 경우.
```json
{
  "error": "INVALID_FILE",
  "message": "제출된 파일이 비어있거나 지원되지 않는 문서 형식입니다."
}
```

---

## 2. 비동기 작업 상태 폴링 API

업로드 완료 시 획득한 `job_id`를 기반으로 백그라운드 태스크의 현재 진행 상태를 조회합니다.

* **Endpoint**: `/api/ledgers/jobs/<uuid:job_id>/`
* **Method**: `GET`
* **Content-Type**: `application/json`

### Response Specification

#### [Success] 200 OK (대기 중 / 처리 중)
작업이 아직 완료되지 않았을 때의 상태 응답입니다.
```json
{
  "job_id": "018f3a38-c64a-7182-bcf8-94ef93cf0001",
  "status": "PROCESSING",
  "created_at": "2026-06-08T17:55:00.123456Z",
  "updated_at": "2026-06-08T17:55:02.987654Z"
}
```

#### [Success] 200 OK (분석 완료 및 가계부 레코드 연계 완료)
분석이 최종 성공하여 매핑된 가계부 내역(`ledger_id`)을 반환합니다. 클라이언트는 이 ID를 이용해 상세 화면으로 리다이렉트 처리합니다.
```json
{
  "job_id": "018f3a38-c64a-7182-bcf8-94ef93cf0001",
  "status": "SUCCESS",
  "ledger_id": 1042,
  "created_at": "2026-06-08T17:55:00.123456Z",
  "updated_at": "2026-06-08T17:55:08.456123Z"
}
```

#### [Success] 200 OK (분석 실패)
작업 수행 도중 에러가 발생하여 실패한 경우이며, 클라이언트는 화면에 오류 원인을 설명해 줍니다.
```json
{
  "job_id": "018f3a38-c64a-7182-bcf8-94ef93cf0001",
  "status": "FAILED",
  "failure_reason": "외부 OCR 모듈 타임아웃 발생 (Connection Timeout)",
  "created_at": "2026-06-08T17:55:00.123456Z",
  "updated_at": "2026-06-08T17:55:05.111222Z"
}
```

#### [Error] 404 Not Found
존재하지 않는 `job_id`를 전달한 경우.
```json
{
  "error": "JOB_NOT_FOUND",
  "message": "요청하신 작업 식별자를 찾을 수 없습니다."
}
```

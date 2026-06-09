# API Contracts: 비동기 작업 API 명세

본 가이드는 API 서버와 프론트엔드 간의 비동기 영수증 파일 분석 및 상태 조회를 위한 인터페이스 계약을 규정합니다.

## 1. 영수증 업로드 및 비동기 접수 API

영수증 이미지 또는 PDF 파일을 서버에 전송하고 작업 접수를 받는 동등 분기입니다.

* **URL**: `/api/ledgers/upload/`
* **Method**: `POST`
* **Headers**:
  * `Authorization`: `Bearer <Access_Token>`
  * `Content-Type`: `multipart/form-data`
* **Request Body**:
  * `file`: File (영수증 PDF 또는 이미지 버퍼)
* **Response**:
  * **Code**: `202 Accepted`
  * **Payload**:
    ```json
    {
      "status": "PENDING",
      "job_id": "01904a60-7212-70b9-8bc3-3b4a2eb83df8"
    }
    ```
  * **Error Codes**:
    * `401 Unauthorized`: 인증 토큰 유효성 검증 실패 시
    * `400 Bad Request`: 허용되지 않은 파일 포맷(MIME 타입) 또는 빈 파일 전송 시

---

## 2. 비동기 작업 상태 조회 (Polling) API

프론트엔드 클라이언트가 비동기 작업의 완료 상태를 파악하기 위해 2초 주기로 숏 폴링하는 API입니다.

* **URL**: `/api/tasks/<job_id>/`
* **Method**: `GET`
* **Headers**:
  * `Authorization`: `Bearer <Access_Token>`
* **Response**:
  * **Code**: `200 OK`
  * **Payload**:
    * *작업 진행 중 또는 대기 중인 경우*:
      ```json
      {
        "job_id": "01904a60-7212-70b9-8bc3-3b4a2eb83df8",
        "status": "PROCESSING",
        "error_message": null,
        "result": null
      }
      ```
    * *작업이 정상적으로 완료된 경우*:
      ```json
      {
        "job_id": "01904a60-7212-70b9-8bc3-3b4a2eb83df8",
        "status": "COMPLETED",
        "error_message": null,
        "result": {
          "ledger_id": 142
        }
      }
      ```
    * *작업에 최종 실패한 경우*:
      ```json
      {
        "job_id": "01904a60-7212-70b9-8bc3-3b4a2eb83df8",
        "status": "FAILED",
        "error_message": "LLM API 호출 시간 초과 (3회 재시도 실패)",
        "result": null
      }
      ```
  * **Error Codes**:
    * `404 Not Found`: 존재하지 않는 `job_id`를 조회 시
    * `401 Unauthorized`: 인증 토큰 유효성 검증 실패 시

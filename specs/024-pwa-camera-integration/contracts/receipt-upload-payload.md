# API Contract: Receipt Image Upload Payload

**Feature Branch**: `024-pwa-camera-integration`

## 1. 영수증 이미지 업로드 엔드포인트

- **HTTP Method**: `POST`
- **Endpoint**: `/api/ledgers/upload/`
- **Content-Type**: `multipart/form-data`
- **Authentication**: `Bearer <sessionToken>` (Header: `Authorization`)

### 1.1 HTTP Request Payload (FormData)

카메라 촬영 및 Canvas 압축 처리가 완료된 `compressedBlob` 파일 데이터를 FormData 규격에 바인딩하여 전송합니다.

```text
POST /api/ledgers/upload/ HTTP/1.1
Host: api-server
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="file"; filename="receipt_1718559021.jpg"
Content-Type: image/jpeg

[compressed binary image data]
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

| 파라미터명 | 타입 | 필수 여부 | 설명 |
| :--- | :--- | :--- | :--- |
| `file` | `Binary (Blob)` | 필수 (Required) | Canvas 압축 가공이 완료된 JPEG 포맷 영수증 이미지 |

---

## 2. API Response

### 2.1 성공 응답 (202 Accepted)
비동기 3-Tier 하이브리드 파이프라인 분석이 정상적으로 접수되었을 때 반환되는 표준 응답 계약 구조입니다.

```json
{
  "job_id": "job_uuid_v7_value_here",
  "status": "PENDING",
  "message": "영수증 이미지 업로드가 성공적이며 분석 태스크가 적재되었습니다."
}
```

### 2.2 실패 응답 (400 Bad Request)
전송된 파일의 형식이 누락되었거나 파라미터 명세가 맞지 않을 때 반환되는 에러 구조입니다.

```json
{
  "error": "BAD_REQUEST",
  "message": "전송된 영수증 파일('file')이 없거나 올바르지 않은 바이너리 형식입니다."
}
```

### 2.3 실패 응답 (401 Unauthorized)
세션 토큰이 누락되었거나 만료되었을 때 반환되는 보안 차단 에러 구조입니다.

```json
{
  "error": "UNAUTHORIZED",
  "message": "인증 세션 정보가 누락되었거나 유효하지 않습니다."
}
```

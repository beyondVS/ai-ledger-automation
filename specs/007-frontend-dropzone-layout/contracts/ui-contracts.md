# UI & Component Contracts: frontend-dropzone-layout

**Created**: 2026-06-02

## 1. 드롭존 컴포넌트 인터페이스 계약 (Dropzone.vue Interface)

`Dropzone.vue`는 영수증 파일을 접수하고 유효성을 1차 검증한 후 부모 컴포넌트에 이벤트를 발송하는 격리된 재사용 컴포넌트입니다.

### Props (속성 입력 계약)
*해당 피처는 단독 페이지 구성으로 Props 입력은 공백을 유지하되, 확장성을 위해 기본 구조만 예약합니다.*

| 속성명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :---: | :--- |
| **maxSizeMB** | Number | `10` | 허용 가능한 최대 파일 크기 (메가바이트 단위) |
| **allowedFormats** | Array | `['image/png', 'image/jpeg', 'image/jpg', 'application/pdf']` | 허용 가능한 파일 MIME 타입 배열 |

### Emitted Events (이벤트 발생 계약)

| 이벤트명 | 페이로드 타입 | 설명 |
| :--- | :--- | :--- |
| **`file-detected`** | `File` (Native File) | 파일 드래그앤드롭 또는 선택 성공 및 유효성 검사 통과 시 발생 |
| **`file-removed`** | `null` | 사용자가 업로드된 파일의 삭제 버튼을 클릭하여 선택을 취소했을 때 발생 |
| **`validation-error`** | `String` (에러 메시지) | 용량 초과 또는 지원하지 않는 포맷 파일 감입으로 검사 실패 시 발생 |

---

## 2. 메인 페이지 상태 정의 계약 (AppState Contract)

메인 페이지(`App.vue` 또는 홈 뷰)에서 영수증 드롭존 및 목록 레이아웃을 관리하기 위한 반응형 상태(Reactive State) 규격입니다.

```javascript
// AppState 상태 정의 인터페이스 객체
const state = {
  // 현재 등록된 영수증 파일 정보 (없을 경우 null)
  currentFile: {
    id: String,          // UUIDv7 형식
    name: String,        // 파일 이름
    size: Number,        // 바이트 용량
    type: String,        // MIME 유형
    previewUrl: String,  // URL.createObjectURL로 생성한 미리보기 blob 주소
    rawFile: File        // 원본 File 객체
  } | null,
  
  // 현재 에러 발생 상태 메시지 (에러가 없을 경우 null)
  errorMessage: String | null
}
```

---

## 3. PWA Manifest & 네이티브 카메라 연동 규격 계약

헌법 제V조(Vision-First PWA)에서 강력히 강제하는 모바일 카메라 직접 호출 표준 바인딩 규격입니다.

### 파일 선택 엘리먼트 바인딩 속성 계약
```html
<!-- PWA 환경에서 사진첩 브라우징 대신 네이티브 모바일 카메라 셔터를 최우선으로 즉시 트리거하는 HTML5 속성 규격 -->
<input 
  type="file" 
  id="receipt-file-input" 
  accept="image/png, image/jpeg, application/pdf" 
  capture="environment"
/>
```
* **`accept`**: 이미지(PNG, JPEG) 및 문서(PDF) 수용 범위를 엄격히 고정.
* **`capture="environment"`**: 모바일 뷰포트에서 클릭 시 사진 파일 선택 브라우저 대신 스마트폰 후면(후방 환경) 카메라를 즉시 가동하여 직촬영하도록 브라우저 표준 지시어 바인딩.

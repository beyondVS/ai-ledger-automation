# Research: Upload API Integration & Async Schema Design

## Decisions & Technical Approaches

### 1. Client-side Image Compression (HTML5 Canvas)
- **Decision**: 사용자가 이미지를 업로드 창에 입력하면, 즉시 HTML5 Canvas API를 구동하여 원본 이미지의 가로 크기를 최대 1000px로 조정하고 JPEG 포맷(압축률 0.85)으로 리사이징하여 서버로 전송합니다.
- **Rationale**: 헌법 제V조(Vision-First PWA)에 명시된 "업로드 직전 클라이언트 단 HTML5 Canvas API를 가동하여 이미지를 가로 최대 1000px 수준으로 1차 압축 처리하여 전송" 규칙을 엄격히 준수합니다. 이를 통해 모바일 환경에서 네트워크 대역폭을 절약하고 백엔드 서버의 리사이징 연산 부하를 최소화합니다.
- **Alternatives Considered**: 서버 측 단독 리사이징(부적합 - 모바일 업로드 대기시간 증가 및 백엔드 CPU 스파이크 유발).

### 2. API Response Schema for Backward Compatibility
- **Decision**: 동기식 Django API 응답 구조를 아래의 스키마로 설계하여 반환합니다.
  ```json
  {
    "job_id": "018f3d6c-6a9b-7c1d-8f2e-3c4d5e6f7a8b", 
    "status": "COMPLETED",
    "data": {
      "merchant_name": "가맹점명",
      "transaction_date": "2026-06-03",
      "amount": 15000,
      "items": [
        { "name": "물품A", "quantity": 1, "price": 10000 },
        { "name": "물품B", "quantity": 1, "price": 5000 }
      ]
    }
  }
  ```
- **Rationale**: 헌법 Phase 1 품질 게이트와 3주차 비동기 전환(Celery 태스크) 대응을 위해 하위 호환 응답 구조를 미리 통제합니다. 동기식 동작 시에는 `status`를 항상 `"COMPLETED"`로 리턴하며, `job_id`에는 UUIDv7 규격에 부합하는 가상 UUID를 반환합니다.
- **Alternatives Considered**: 동기식 처리에서 `job_id`와 `status`를 제외하고 순수 데이터만 리턴하는 방식(부적합 - 3주차 비동기 전환 시 프론트엔드 파싱 및 처리 코드에 파괴적 변경을 유발함).

### 3. Client-side Virtual Polling Module
- **Decision**: 프론트엔드 업로드 서비스 내부에 추상화된 `VirtualPollingManager`를 구현합니다. API 응답의 `status`가 `"COMPLETED"`이면 즉시 UI 결과를 업데이트하고 로딩 인디케이터를 해제하며, 만약 임의의 시뮬레이션을 통해 `"PENDING"` 또는 `"PROCESSING"` 상태가 주입되면 1초 주기로 가상 대기 루프를 돌려 상태 변화를 시뮬레이션한 후 최종 데이터를 바인딩합니다.
- **Rationale**: 3주차 백엔드 비동기 전환 시 백엔드 엔드포인트 수정 없이 프론트엔드가 하위 호환 상태 대기 화면을 매끄럽게 유지할 수 있도록 미리 가상 폴링 모듈을 설계하여 연동합니다.

### 4. Database Connection Pool Controls
- **Decision**: 1주차 구축된 Django API 컨테이너 설정 상의 데이터베이스 커넥션 풀 한도를 최대 5개 이하로 계속 유지 및 모니터링합니다. (Supabase 등 무료 등급 DBMS의 커넥션 고갈 예방)
- **Rationale**: 헌법 제II조의 "api_server 컨테이너 최대 5개, Celery worker 최대 3개, 전체 합산 8개 이하" 자원 점유 최적화 조항을 준수합니다.

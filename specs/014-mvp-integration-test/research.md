# Research & Decision Record: MVP Integration Test

본 문서는 MVP Integration Test 피처 개발을 위해 검토된 핵심 기술적 선택 사항들과 그에 대한 연구 결과를 기록합니다.

## Decisions

### 1. HTML5 Canvas 1차 이미지 압축
* **결정사항 (Decision)**: Vue 3 클라이언트 단에서 영수증 이미지 감지 즉시 HTML5 Canvas API를 이용하여 최대 가로 폭 1000px로 리사이징하고, JPEG Quality 0.8 수준으로 압축 인코딩하여 서버에 송신합니다.
* **타당성 (Rationale)**: 
  - 최근 모바일 기기로 촬영한 영수증 이미지는 파일당 10MB~20MB를 초과하는 경우가 많아, 원본 그대로 전송 시 모바일 대역폭에 따른 지연이 크게 발생합니다.
  - 클라이언트 단에서 1차 리사이징 및 압축을 수행하면 네트워크 전송 용량을 100KB~300KB 수준으로 줄여 E2E 10초 이내 갱신 목표(SC-001)를 안정적으로 달성할 수 있습니다.
  - 또한, 서버 측 메모리가 대용량 파일 업로드 시 폭주하는 것을 원천 방어합니다.
* **고려된 대안 (Alternatives considered)**: 원본 이미지를 그대로 업로드하고 서버 측에서만 리사이징 처리.
  - **기각 사유**: 네트워크 업로드 지연으로 인해 E2E 10초 목표를 준수할 수 없으며 모바일 사용자 환경에서 응답이 매우 답답하게 느껴지므로 기각했습니다.

### 2. Pillow 모듈 활용 WebP 2차 이미지 변환
* **결정사항 (Decision)**: Django 백엔드 서버에서 Multipart-form으로 수신한 이미지 바이트 버퍼를 Pillow 모듈로 로드한 뒤, WebP 포맷(Quality 80)으로 2차 변환하여 Gemini API로 송신합니다.
* **타당성 (Rationale)**:
  - WebP 포맷은 JPEG 대비 30% 이상 용량이 더 작으면서도 OCR(텍스트 추출)을 위한 화질 손실이 매우 적어 Gemini API 호출 시 전송 지연을 극소화합니다.
  - 추후 Storage에 보존할 때 디스크 비용을 최적화할 수 있어 헌법 제V조의 대역폭 및 용량 절감에 부합합니다.
* **고려된 대안 (Alternatives considered)**: 클라이언트에서 받은 JPEG 파일 버퍼를 그대로 Gemini API로 전달.
  - **기각 사유**: WebP로의 추가 용량 최적화 혜택을 포기하기에는 API 전송 지연 및 추후 스토리지 누적 비용 부담이 크므로 변환 파이프라인을 도입합니다.

### 3. Gemini-2.5-Flash Structured Outputs 적용
* **결정사항 (Decision)**: 백엔드는 Gemini-2.5-Flash API를 활용하되, `response_mime_type="application/json"` 옵션과 함께 `response_schema`에 JSON Schema를 명시적으로 전달하여 정형 가계부 데이터 구조를 강제 수신합니다.
* **타당성 (Rationale)**:
  - LLM의 텍스트 응답을 정규식이나 JSON 파싱 함수로 재처리하는 방식은 필드 누락이나 불규칙한 데이터 반환 시 롤백 및 파싱 실패율이 매우 높습니다.
  - Pydantic 등으로 정의된 명확한 스키마를 API 레벨에서 강제함으로써 데이터 정합성을 보장하고, `ledgers` 및 `ledger_items` 테이블에 안정적으로 데이터를 매핑할 수 있습니다.
* **고려된 대안 (Alternatives considered)**: 일반 텍스트 응답 프롬프팅 및 정규식 파싱 폴백.
  - **기각 사유**: 구조화되지 않은 일반 텍스트는 필드 유실율이 높아 트랜잭션 원자성을 지켜야 하는 금융 성격의 가계부 데이터 적재에 부적합하므로 기각했습니다.

### 4. Django 트랜잭션 원자성 (`transaction.atomic()`) 수호
* **결정사항 (Decision)**: 단일 영수증에서 생성되는 `ledgers` 마스터 레코드와 `ledger_items` 세부 품목 데이터의 DB 삽입 로직을 `transaction.atomic()` 컨텍스트 블록으로 일괄 바인딩합니다.
* **타당성 (Rationale)**:
  - 세부 품목 삽입이나 복합 유니크 제약조건 위반 예외가 발생할 경우, 마스터 테이블(ledgers)에만 데이터가 남는 데이터 오염 상태(Dirty State)를 확실히 방지합니다.
  - RDBMS의 ACID 정합성을 활용해 100% 원자성을 보장함으로써 헌법 제I조를 영구 준수합니다.
* **고려된 대안 (Alternatives considered)**: 개별 `save()` 처리 후 예외 발생 시 코드 단에서 수동 DELETE 수행.
  - **기각 사유**: 예기치 않은 시스템 장해(파워 오프, 커넥션 단절 등) 시 수동 클린업 코드가 동작하지 않아 데이터 부정합이 발생할 위험이 크므로 기각했습니다.

### 5. 사업자번호 기반 bypass 캐싱 파이프라인
* **결정사항 (Decision)**: OCR 텍스트 분석 결과 가맹점의 10자리 사업자등록번호가 식별되면 `merchant_templates` 캐시 테이블을 최우선 인덱스 조회하고, 수동 승인 마크(`is_verified: true`)가 지정된 정적 정규식 규칙이 존재할 경우 LLM 호출을 즉시 우회(Bypass)하여 로컬 파서로 처리합니다.
* **타당성 (Rationale)**:
  - 유료 LLM API 연동 예산 비용을 실질적으로 0원에 수렴하도록 절감할 수 있으며, 캐시된 로컬 정규식 파싱은 100ms 이내에 완료되어 성능 면에서도 훌륭한 혜택을 줍니다.
  - 캐시 정보가 없거나 미검증 상태(`is_verified: false`)일 때만 LLM을 가동하는 하이브리드 비용 최적화 파이프라인(헌법 제III조)을 준수합니다.
* **고려된 대안 (Alternatives considered)**: 모든 요청에 Gemini API 무조건 호출.
  - **기각 사유**: 상용 서비스 확대 시 API 비용이 비선형적으로 증가하여 비용 통제가 불가능하므로 우회 캐싱을 의무화합니다.

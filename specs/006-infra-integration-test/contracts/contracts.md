# Interface Contracts: 1주차 인프라 중간 점검 및 로컬 통합 테스트 수행 (Infra Integration Test)

본 문서는 PDF 영수증 데이터의 파싱 및 Django ORM 적재 흐름에서 사용되는 컴포넌트 간 인터페이스 계약, 시퀀스 데이터 흐름 및 입출력 스키마 규격을 명세합니다.

---

## 1. 가계부 트랜잭션 적재 인터페이스 규격 (DRF Service Level)

영수증 데이터를 단일 원자적 트랜잭션 내에서 영속화하는 파이썬 서비스 함수인 `create_ledger_transactional`의 입출력 계약 명세입니다.

### 1.1 입력 매개변수 스키마 (Input Schema)

```json
{
  "user_id": "UUID String",
  "ledger_data": {
    "vendor_registration_number": "1208147528",
    "vendor_name": "홍콩반점",
    "transaction_date": "2026-05-29",
    "total_amount": 24000.00,
    "supply_value": 21818.18,
    "vat_amount": 2181.82
  },
  "items_data": [
    {
      "item_name": "짜장면 곱빼기",
      "quantity": 2,
      "unit_price": 7000.00,
      "total_price": 14000.00
    },
    {
      "item_name": "탕수육 소",
      "quantity": 1,
      "unit_price": 10000.00,
      "total_price": 10000.00
    }
  ]
}
```

### 1.2 출력 응답 스키마 (Output Response)

*   **성공 시 (SUCCESS)**:
    ```json
    {
      "status": "SUCCESS",
      "ledger_id": "UUIDv7 String",
      "message": "Ledger transactions successfully committed."
    }
    ```
*   **실패 시 (FAILURE - 복합 고유 키 위배 등)**:
    *   **동작**: 상위 호출 계층으로 `django.db.IntegrityError` 예외를 전격 Throw하여 원본 트랜잭션 롤백을 즉각 보장합니다.

---

## 2. 통합 검증 컴포넌트 간 시퀀스 흐름 계약 (Sequence Diagram)

통합 테스트 스위트(`TestPDFIntegrationSuite`)가 작동할 때 각 컴포넌트와 데이터베이스가 맺는 원자적 시퀀스 상호작용 계약입니다.

```mermaid
sequenceDiagram
    autonumber
    actor CLI as run-pdf-tests Script
    participant Suite as TestPDFIntegrationSuite
    participant Extractor as PDFTextExtractor
    participant DRF as create_ledger_transactional
    participant DB as PostgreSQL v18 Test DB
    participant DLQ as FailedTask (DLQ)

    CLI->>DB: [1] 격리된 Docker 18-alpine 컨테이너 기동
    CLI->>DB: [2] Django ORM 마이그레이션 일제 가동 (스키마 멱등 구축)
    CLI->>Suite: [3] Pytest 통합 검증 스위트 기동
    
    %% 해피패스
    Suite->>Extractor: [4] receipt_sample.pdf 파일 바이트 인계
    Extractor->>Extractor: [5] PyMuPDF+pdfplumber 하이브리드 파싱 & NFC 한글 복원
    Extractor-->>Suite: [6] 파싱 텍스트 DTO 반환
    Suite->>DRF: [7] user_id 및 파싱 JSON 페이로드 주입
    DRF->>DB: [8] transaction.atomic() 세션 가동 및 INSERT 시도
    DB-->>DRF: [9] 성공 응답 (Commit Complete)
    DRF-->>Suite: [10] STATUS: SUCCESS 반환
    
    %% 중복 유입 및 DLQ 분기
    Suite->>DRF: [11] 동일 페이로드로 2차 인서트 시도 (중복 영수증)
    DRF->>DB: [12] transaction.atomic() 세션 하에서 INSERT
    DB-->>DRF: [13] UNIQUE 고유 제약조건 위배 에러 (IntegrityError)
    DRF->>DB: [14] 1차 롤백 수행 (Rollback Active Transaction)
    DRF->>DLQ: [15] [격리 적재] 신규 독립 세션 가동 FailedTask 생성 및 커밋
    DLQ-->>DRF: [16] 격리 완료
    DRF-->>Suite: [17] IntegrityError 예외 및 롤백 입증 완료
    
    Suite-->>CLI: [18] 전체 14개 테스트 PASS 결과 출력
    CLI->>DB: [19] [Clean Isolation] Docker Container & Volumn 즉시 회수 (Cleanup)
```

---

## 3. 크로스 플랫폼 CLI 자동화 도구 계약 (run-pdf-tests Script)

Windows PowerShell 및 UNIX/macOS Bash 양대 쉘 도구의 인터페이스 CLI 표준 파라미터 및 동작 계약 명세입니다.

*   **기본 옵션**:
    *   **Windows**: `.\scripts\run-pdf-tests.ps1`
    *   **UNIX**: `./scripts/run-pdf-tests.sh`
*   **리턴 코드 계약 (Exit Code)**:
    *   `0`: 모든 검증 성공 (DB 기동 -> 마이그레이션 -> 테스트 패스 -> 리소스 정리 성공)
    *   `1` 이상: 검증 실패 (DB 에러, 테스트 실패, 자원 Cleanup 실패 등 발생)

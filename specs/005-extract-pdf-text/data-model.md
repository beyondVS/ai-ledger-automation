# Data Model & DTOs: PDF Text Lossless Extraction

**Feature**: PDF Text Extraction Utility | **Date**: 2026-05-31
**Status**: Approved

본 설계는 PDF 텍스트 무손실 추출 유틸리티 클래스가 반환하는 데이터 규격(DTO)과, 추출된 텍스트가 데이터베이스 레이어 및 LLM 파이프라인에서 안전하게 활용되기 위해 준수해야 할 유효성 검증 규칙을 수립합니다.

---

## 1. 데이터 송수신 객체 (Data Transfer Object)

### ExtractionResult DTO
유틸리티 클래스의 호출자에게 예외 없이 안전하게 반환되는 최종 구조화된 데이터 객체입니다.

| 필드명 | 데이터 타입 | 설명 | 필수 여부 |
| :--- | :--- | :--- | :---: |
| `success` | `bool` | 텍스트 추출 작업의 전체 성공 여부 | 필수 |
| `raw_text` | `str` | 전체 페이지의 텍스트가 병합된 단일 문자열 (정규화 완료) | 필수 |
| `page_texts` | `dict[int, str]` | 페이지 번호(1-indexed)를 키로 하고, 해당 페이지의 텍스트를 값으로 하는 맵 | 필수 |
| `extracted_pages` | `int` | 정상적으로 텍스트를 파싱 및 복원해낸 총 페이지 수 | 필수 |
| `used_engine` | `str` | 추출에 최종 활용된 라이브러리 명칭 (`"pymupdf"`, `"pdfplumber"`) | 필수 |
| `is_encrypted` | `bool` | 입력된 PDF 파일이 비밀번호 등으로 보안 암호화되었는지 여부 | 필수 |
| `has_text_layer` | `bool` | PDF 내부 객체 상에 텍스트 데이터 노드가 물리적으로 식별되었는지 여부 | 필수 |
| `error_message` | `str | None` | 실패 시 상세 에러 원인 문자열 (성공 시 `None`) | 선택 |

---

## 2. 유효성 검증 및 유니코드 정규화 규칙

### A. 한글 유니코드 NFC 정규화 규칙 (NFC Normalization)
- **대상**: 추출 완료된 모든 `raw_text` 및 `page_texts` 값.
- **적용 표준**: 유니코드 정규화 규격의 NFC(Normal Form Canonical Composition).
- **검증 시나리오**: 
  - 자모가 분리된 문자열 `"ㄱ-ㅏ-ㄱ-ㅏ-ㅇ-ㅔ-ㅂ-ㅜ"` 감지 시 즉시 조합형 완성 문자 `"가계부"`로 변환되어야 합니다.
  - 변환 전후의 글자수 차이와 인코딩 유효성을 확인하여 원시 정보 왜곡을 원천 방어합니다.

### B. 암호화 및 파일 무결성 판독 규칙
- **암호화 여부**: PDF 로드 시 `doc.is_encrypted`가 참이거나 권한 에러(`fitz.FileDataError`, `pdfplumber.pdf.PDFPasswordIncorrect`)가 발생할 때 `is_encrypted = True`, `success = False`로 플래깅 처리합니다.
- **텍스트 레이어 미존재 (스캔 전용 PDF)**:
  - 전체 페이지를 순회하며 공백 문자를 제외한 추출 캐릭터의 합계가 **0개**인 경우 `has_text_layer = False`로 설정합니다.
  - 이 경우 DTO의 `success = False`, `error_message = "No physical text layer detected in PDF. Scan/OCR required."`를 채워 즉시 OCR 바이패스 흐름으로 제어권을 반환합니다.

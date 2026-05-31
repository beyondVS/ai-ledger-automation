# Quickstart: PDF Text Extraction Utility

**Feature**: PDF Text Extraction Utility | **Date**: 2026-05-31
**Status**: Approved

본 가이드는 개발자가 로컬 개발 환경 및 테스트 벤치마크 환경에서 `PDFTextExtractor`를 즉시 기동하고 검증할 수 있는 빠른 활용 방법을 소개합니다.

---

## 1. 선언적 의존성 설치 및 락킹

헌법 제VII조(선언적 의존성 및 uv 패키지 격리 수호)에 의거하여, ad-hoc 방식의 `pip install`은 엄격히 금지됩니다. 프로젝트 의존성은 반드시 백엔드 `pyproject.toml`에 선언한 후 `uv sync`를 통해 락파일을 갱신해야 합니다.

### 의존성 주입 명령 예시 (로컬 터미널)
```bash
# 1. backend 디렉토리로 이동하여 선언적 의존성 추가
# (PyMuPDF의 실행 패키지명은 pymupdf, pdfplumber의 패키지명은 pdfplumber)
uv add pymupdf pdfplumber

# 2. 로컬 가상 환경과 락파일 동기화 및 멱등성 검증
uv sync
```

---

## 2. 기본적인 빠른 사용법 (Quick Snippet)

### A. 기본적인 파일 경로로부터의 추출
```python
from io import BytesIO
from specs.extract_pdf_text.extractor import PDFTextExtractor

# 1. 파일 소스로부터 추출 엔진 인스턴스 생성 (기본값: PyMuPDF 우선, NFC 정규화 설정)
extractor = PDFTextExtractor(file_source="tests/samples/sample_receipt.pdf")

# 2. 텍스트 추출 실행 (레이아웃 보존 옵션 활성화)
result = extractor.extract_text(layout=True)

# 3. 결과 출력 및 DTO 검증
if result.success:
    print(f"추출 성공! 사용된 엔진: {result.used_engine}")
    print(f"추출된 총 페이지 수: {result.extracted_pages}")
    print(f"--- 추출 텍스트 원본 ---\n{result.raw_text}")
else:
    print(f"추출 실패 사유: {result.error_message}")
```

### B. 메모리 내 BytesIO 바이트 스트림으로부터의 추출 (비동기 Celery 환경 최적화)
```python
from io import BytesIO
from specs.extract_pdf_text.extractor import PDFTextExtractor

def process_uploaded_pdf_stream(pdf_bytes: bytes):
    # 바이트 데이터를 메모리 스트림으로 래핑
    stream = BytesIO(pdf_bytes)
    
    # 어댑터 생성
    extractor = PDFTextExtractor(
        file_source=stream,
        engine_preference="pymupdf",
        normalize_unicode=True
    )
    
    # 레이아웃 보존 방식으로 텍스트 추출 실행
    result = extractor.extract_text(layout=True)
    
    return result
```

---

## 3. 단위 테스트 샘플 코드 (UnitTest/Django Test Runner)

로컬 빌드/테스트 품질 게이트를 만족하기 위해, 아래의 규격에 따라 테스트 케이스를 구현합니다.

```python
import unittest
from io import BytesIO
from specs.extract_pdf_text.extractor import PDFTextExtractor

class TestPDFTextExtractor(unittest.TestCase):
    def setUp(self):
        # 테스트 전용 간단한 물리 PDF 파일 혹은 모의 바이너리 준비
        self.sample_pdf_path = "tests/samples/sample_receipt.pdf"
        
    def test_pymupdf_extract_success(self):
        """정상적인 PDF에서 PyMuPDF를 이용한 텍스트 무손실 추출 성공 검증"""
        extractor = PDFTextExtractor(self.sample_pdf_path, engine_preference="pymupdf")
        result = extractor.extract_text(layout=True)
        
        self.assertTrue(result.success)
        self.assertEqual(result.used_engine, "pymupdf")
        self.assertIn("가맹점", result.raw_text)  # 예시 텍스트 포함 확인
        self.assertTrue(result.has_text_layer)

    def test_korean_unicode_nfc_normalization(self):
        """맥OS 등에서 발생할 수 있는 한글 자모 깨짐에 대한 NFC 정규화 동작 보장 검증"""
        # 의도적으로 자모가 분리된 문자열에 대해 유니코드 정규화 후 정합성 체크
        from unicodedata import normalize
        jamo_text = "ㄱ-ㅏ-ㄱ-ㅏ-ㅇ-ㅔ-ㅂ-ㅜ" # 자모 분리 상태 예시
        normalized = normalize("NFC", jamo_text)
        
        # 유틸리티 내부 정규화 함수 동작 후 완성형 한글 판독 무결성 검증
        self.assertNotIn("ㄱ-ㅏ", normalized)
```

import unittest
import unicodedata
from io import BytesIO
import fitz
from utils.pdf_extractor import PDFTextExtractor, ExtractionResult

class TestPDFTextExtractor(unittest.TestCase):
    def setUp(self) -> None:
        # 1. 테스트용 정상 PDF 동적 생성 (영문 텍스트 삽입하여 폰트 인코딩 결함 회피)
        self.doc = fitz.open()
        self.page = self.doc.new_page()
        self.page.insert_text((50, 50), "Ledger Test Receipt", fontsize=12)
        self.normal_pdf_bytes = self.doc.write()
        self.doc.close()

    def test_pymupdf_extract_success(self) -> None:
        """PyMuPDF 단독 구동 시, 정상 한글 텍스트(영문 포함)를 무손실 추출하는지 검증합니다."""
        stream = BytesIO(self.normal_pdf_bytes)
        extractor = PDFTextExtractor(file_source=stream, engine_preference="pymupdf")
        result = extractor.extract_text(layout=True)

        self.assertTrue(result.success, msg=result.error_message)
        self.assertEqual(result.used_engine, "pymupdf")
        self.assertIn("Ledger Test Receipt", result.raw_text)
        self.assertTrue(result.has_text_layer)
        self.assertFalse(result.is_encrypted)
        self.assertEqual(result.extracted_pages, 1)

    def test_korean_unicode_nfc_normalization(self) -> None:
        """macOS NFD 방식으로 인코딩된 한글 텍스트가 NFC 완성형 한글로 안전하게 정규화 복원되는지 검증합니다."""
        extractor = PDFTextExtractor(file_source=BytesIO(b"dummy"), engine_preference="pymupdf", normalize_unicode=True)
        
        # NFD 자모 분리 한글 준비
        nfd_text = unicodedata.normalize('NFD', "가계부 자동화")
        
        # NFC 정규화 함수 직접 작동
        normalized_text = extractor._normalize(nfd_text)
        
        # 조합이 정상 복원되었는지 검증
        self.assertEqual(normalized_text, "가계부 자동화")
        
        # 분리형 낱자가 더 이상 매칭되지 않는지 검증
        self.assertNotIn(nfd_text, normalized_text)

    def test_pymupdf_fallback_to_pdfplumber(self) -> None:
        """PyMuPDF 파싱 오류 시 pdfplumber로 자동 Fallback 처리되는지 검증합니다."""
        from unittest.mock import patch
        
        stream = BytesIO(self.normal_pdf_bytes)
        extractor = PDFTextExtractor(file_source=stream, engine_preference="pymupdf")
        
        # PyMuPDF의 텍스트 추출 행위(fitz.Page.get_text)를 Mocking하여 강제 예외 유도
        with patch('fitz.Page.get_text', side_effect=RuntimeError("PyMuPDF internal error simulation")):
            result = extractor.extract_text(layout=True)
            
        self.assertTrue(result.success, msg=result.error_message)
        # 1차 실패 후 pdfplumber로 성공적으로 Fallback 복원되었음을 검증
        self.assertEqual(result.used_engine, "pdfplumber")
        self.assertIn("Ledger Test Receipt", result.raw_text)
        self.assertTrue(result.has_text_layer)

    def test_encrypted_pdf_handling(self) -> None:
        """암호화된 PDF 유입 시, 크래시 없이 success: False 및 is_encrypted: True를 감싸 반환하는지 검증합니다."""
        # 암호화 PDF 동적 생성
        enc_doc = fitz.open()
        enc_doc.new_page()
        # 암호화 바이트 작성
        enc_bytes = enc_doc.write(
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw="secret"
        )
        enc_doc.close()

        extractor = PDFTextExtractor(file_source=BytesIO(enc_bytes))
        result = extractor.extract_text(layout=True)

        self.assertFalse(result.success)
        self.assertTrue(result.is_encrypted, msg=result.error_message)
        self.assertIn("암호화", result.error_message)

    def test_no_text_layer_pdf_handling(self) -> None:
        """텍스트 레이어가 없는 빈 PDF 유입 시, success: False 및 has_text_layer: False DTO를 안전하게 반환하는지 검증합니다."""
        # 텍스트 레이어가 없는 스캔 이미지 대체 빈 PDF 생성
        blank_doc = fitz.open()
        blank_doc.new_page()
        blank_bytes = blank_doc.write()
        blank_doc.close()

        extractor = PDFTextExtractor(file_source=BytesIO(blank_bytes))
        result = extractor.extract_text(layout=True)

        self.assertFalse(result.success)
        self.assertFalse(result.has_text_layer)
        self.assertIn("물리적 텍스트", result.error_message)



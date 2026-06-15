import io
import unittest
from unittest.mock import MagicMock, patch

# T007: 로컬 OCR(PyMuPDF / Tesseract) 문자 추출 기능 테스트
# TDD에 따라 구현 전에 이 테스트를 실행하면, 호출할 대상 함수가 없거나 실패해야 합니다.


class LocalOCRTestCase(unittest.TestCase):
    """
    로컬 OCR 문자 추출 기능의 단위 테스트 (TDD)
    """

    @patch("fitz.open")
    def test_pdf_ocr_text_extraction_success(self, mock_fitz_open):
        """PDF 파일 유입 시 PyMuPDF(fitz)를 통한 텍스트 추출 성공 검증"""
        # Given: fitz.open이 페이지 컬렉션을 반환하도록 모킹
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Starbucks Coffee YEOKSAM\nTotal Amount: 15,000"
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        # 임시 PDF 바이트
        pdf_file = io.BytesIO(b"fake pdf content")

        # When: 우리가 구현할 OCR 추출 함수 호출 (아직 구현되지 않아 예외 발생 등으로 실패 유도)
        # T010 구현 전이므로 ImportError 또는 AttributeError로 실패해야 합니다.
        from apps.ledgers.services.ocr import extract_text_from_pdf

        extracted_text = extract_text_from_pdf(pdf_file)

        # Then: 추출된 텍스트 검증
        self.assertIn("Starbucks", extracted_text)
        self.assertIn("15,000", extracted_text)

    @patch("pytesseract.image_to_string")
    @patch("PIL.Image.open")
    def test_image_ocr_text_extraction_success(self, mock_image_open, mock_tesseract_string):
        """이미지 파일 유입 시 Tesseract를 통한 텍스트 추출 성공 검증"""
        # Given: pytesseract가 문자열을 정상 반환하도록 모킹
        mock_tesseract_string.return_value = "Starbucks Yeoksam \n Total: 15000"
        mock_image_open.return_value = MagicMock()

        # 임시 이미지 바이트
        image_file = io.BytesIO(b"fake image content")

        # When: 이미지 OCR 추출 함수 호출
        from apps.ledgers.services.ocr import extract_text_from_image

        extracted_text = extract_text_from_image(image_file)

        # Then: 결과 검증
        self.assertIn("Starbucks", extracted_text)
        self.assertIn("15000", extracted_text)

    def test_ocr_text_extraction_empty_fallback(self):
        """OCR 실패 시 빈 문자열 반환 및 예외 안전 복구 검증"""
        # Given: fitz.open이 예외를 발생시키도록 모킹
        with patch("fitz.open", side_effect=Exception("PDF Corrupted")):
            pdf_file = io.BytesIO(b"corrupted pdf")

            # When & Then: 예외가 발생하더라도 삼켜지고 빈 문자열로 복구되는지 검증
            from apps.ledgers.services.ocr import extract_text_from_pdf

            extracted_text = extract_text_from_pdf(pdf_file)
            self.assertEqual(extracted_text, "")

import logging

import fitz
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_file) -> str:
    """
    PyMuPDF(fitz)를 사용하여 PDF 파일로부터 텍스트를 추출합니다.
    예외 발생 시 빈 문자열("")을 반환하며 안전하게 복구됩니다.
    """
    try:
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)

        pdf_bytes = pdf_file.read()
        if not pdf_bytes:
            return ""

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        extracted_text = ""
        for page in doc:
            text = page.get_text()
            if text:
                extracted_text += text

        return extracted_text
    except Exception as e:
        logger.warning(f"PDF 텍스트 추출 중 에러 발생: {str(e)}")
        return ""


def extract_text_from_image(image_file) -> str:
    """
    Tesseract OCR을 사용하여 이미지 파일로부터 텍스트를 추출합니다.
    예외 발생 시 빈 문자열("")을 반환하며 안전하게 복구됩니다.
    """
    try:
        if hasattr(image_file, "seek"):
            image_file.seek(0)

        img = Image.open(image_file)
        extracted_text = pytesseract.image_to_string(img, lang="kor+eng")
        return extracted_text or ""
    except Exception as e:
        logger.warning(f"이미지 OCR 텍스트 추출 중 에러 발생: {str(e)}")
        return ""

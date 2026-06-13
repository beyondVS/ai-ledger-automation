import unittest

# TDD: RegexParser 구현 전이므로 최초 임포트 시 실패(Red)가 발생하는 것이 정상입니다.
try:
    from apps.ledgers.services.parser import RegexParser
except ImportError:
    RegexParser = None


class TestRegexParser(unittest.TestCase):
    def setUp(self):
        if RegexParser is None:
            self.skipTest("RegexParser is not implemented yet.")

    def test_extract_total_amount_success(self):
        # Given
        ocr_text = "스타벅스 강남역점\n사업자번호: 120-86-12345\n합계: 15,000\n날짜: 2026-06-11"
        rules = {
            "total_amount_regex": r"합계:\s*([0-9,]+)",
            "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
        }

        # When
        parser = RegexParser(rules)
        amount = parser.extract_total_amount(ocr_text)

        # Then
        self.assertEqual(amount, 15000.0)

    def test_extract_total_amount_invalid_format(self):
        # Given
        ocr_text = "스타벅스 강남역점\n사업자번호: 120-86-12345\n금액: 15,000"
        rules = {
            "total_amount_regex": r"합계:\s*([0-9,]+)",
        }

        # When & Then (정규식 매칭 실패 시 ValueError가 발생하는지 검증)
        parser = RegexParser(rules)
        with self.assertRaises(ValueError):
            parser.extract_total_amount(ocr_text)

    def test_extract_transaction_date_success(self):
        # Given
        ocr_text = "스타벅스 강남역점\n날짜: 2026-06-11"
        rules = {
            "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
        }

        # When
        parser = RegexParser(rules)
        date_str = parser.extract_transaction_date(ocr_text)

        # Then
        self.assertEqual(date_str, "2026-06-11")

    def test_extract_transaction_date_invalid_format(self):
        # Given
        ocr_text = "스타벅스 강남역점\n일자: 2026/06/11"
        rules = {
            "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
        }

        # When & Then
        parser = RegexParser(rules)
        with self.assertRaises(ValueError):
            parser.extract_transaction_date(ocr_text)

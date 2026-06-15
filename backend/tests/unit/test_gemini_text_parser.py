import unittest
from unittest.mock import MagicMock, patch

from utils.llm_client import ReceiptLLMClient, ReceiptSchema

# T013: Gemini-2.5-Flash Text-only API 호출을 통한 텍스트 기반 구조화 기능 단위 테스트 (TDD)


class GeminiTextParserTestCase(unittest.TestCase):
    """
    Gemini-2.5-Flash Text-only 파서 및 금액 검증에 대한 단위 테스트
    """

    @patch("litellm.Router.completion")
    def test_gemini_text_parsing_with_valid_checksum_success(self, mock_completion):
        """Gemini 반환 JSON이 완벽하고 금액 정합성(합계가 일치)을 충족할 때 성공적으로 ReceiptSchema 반환 검증"""
        # Given: LiteLLM Router가 상세 품목의 합(10000 + 5000 = 15000)이 총 결제금액(15000)과 정확히 일치하는 JSON을 반환하도록 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "이마트", "vendor_registration_number": "2208112345", "transaction_date": "2026-06-11T16:00:00", "total_amount": 15000.0, "category": "생활용품", "items": [{"item_name": "건전지", "unit_price": 5000.0, "quantity": 2, "total_price": 10000.0}, {"item_name": "치약", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}]}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When: 우리가 구현할 Gemini Text-only 파서 메서드 호출
        client = ReceiptLLMClient()
        # T015 구현 전이므로 AttributeError 등으로 실패해야 합니다.
        result = client.parse_receipt_cloud_text("fake ocr text")

        # Then: 성공적으로 ReceiptSchema가 반환되는지 확인
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ReceiptSchema)
        self.assertEqual(result.total_amount, 15000.0)
        self.assertEqual(result.vendor_name, "이마트")

    @patch("litellm.Router.completion")
    def test_gemini_text_parsing_with_invalid_checksum_fails(self, mock_completion):
        """Gemini 반환 JSON은 맞으나 금액 정합성(품목 합계가 총액과 다름) 불일치 시 None 반환 검증"""
        # Given: 품목 합(5000*1 + 5000 = 10000)이 총 결제금액(15000)과 다른 불일치 JSON 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "이마트", "vendor_registration_number": "2208112345", "transaction_date": "2026-06-11T16:00:00", "total_amount": 15000.0, "category": "생활용품", "items": [{"item_name": "건전지", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}, {"item_name": "치약", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}]}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When: Gemini Text-only 파서 실행
        client = ReceiptLLMClient()
        result = client.parse_receipt_cloud_text("fake ocr text")

        # Then: 금액 정합성 오류로 인해 None을 반환해야 함
        self.assertIsNone(result)

    @patch("litellm.Router.completion")
    def test_gemini_text_parsing_with_broken_json_fails(self, mock_completion):
        """Gemini 반환값이 올바른 JSON 포맷이 아닐 때 (스키마 붕괴) None 반환 검증"""
        # Given: 깨진 JSON 텍스트 반환 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "이마트", "vendor_registration_number": "2208112345", broken_json_here...'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When
        client = ReceiptLLMClient()
        result = client.parse_receipt_cloud_text("fake ocr text")

        # Then
        self.assertIsNone(result)

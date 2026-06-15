import unittest
from unittest.mock import MagicMock, patch

from utils.llm_client import ReceiptLLMClient, ReceiptSchema

# T008: 로컬 Ollama 파서 및 금액 정합성(Checksum) 검증 단위 테스트
# TDD이므로 구현 전에 실행하면 테스트가 실패하거나 에러가 나야 합니다.


class OllamaParserTestCase(unittest.TestCase):
    """
    로컬 Ollama 파서 및 금액 검증에 대한 단위 테스트
    """

    @patch("litellm.Router.completion")
    def test_ollama_parsing_with_valid_checksum_success(self, mock_completion):
        """Ollama 반환 JSON이 완벽하고 금액 정합성(합계가 일치)을 충족할 때 성공적으로 ReceiptSchema 반환 검증"""
        # Given: LiteLLM Router가 상세 품목의 합(5000*2 + 5000 = 15000)이 총 결제금액(15000)과 정확히 일치하는 JSON을 반환하도록 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "스타벅스", "vendor_registration_number": "1208612345", "transaction_date": "2026-06-11T15:00:00", "total_amount": 15000.0, "category": "식비", "items": [{"item_name": "아메리카노", "unit_price": 5000.0, "quantity": 2, "total_price": 10000.0}, {"item_name": "스콘", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}]}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When: 우리가 구현할 로컬 Ollama 파서 메서드 호출
        client = ReceiptLLMClient()
        # T011 구현 전이므로 AttributeError 등으로 실패해야 합니다.
        result = client.parse_receipt_local("fake ocr text")

        # Then: 성공적으로 ReceiptSchema가 반환되는지 확인
        self.assertIsNotNone(result)
        self.assertIsInstance(result, ReceiptSchema)
        self.assertEqual(result.total_amount, 15000.0)
        self.assertEqual(result.vendor_name, "스타벅스")

    @patch("litellm.Router.completion")
    def test_ollama_parsing_with_invalid_checksum_fails(self, mock_completion):
        """Ollama 반환 JSON은 맞으나 금액 정합성(품목 합계가 총액과 다름) 불일치 시 None 반환 검증"""
        # Given: 품목 합(5000*1 + 5000 = 10000)이 총 결제금액(15000)과 다른 불일치 JSON 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "스타벅스", "vendor_registration_number": "1208612345", "transaction_date": "2026-06-11T15:00:00", "total_amount": 15000.0, "category": "식비", "items": [{"item_name": "아메리카노", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}, {"item_name": "스콘", "unit_price": 5000.0, "quantity": 1, "total_price": 5000.0}]}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When: 로컬 Ollama 파서 실행
        client = ReceiptLLMClient()
        result = client.parse_receipt_local("fake ocr text")

        # Then: 금액 정합성 오류로 인해 None을 반환해야 함
        self.assertIsNone(result)

    @patch("litellm.Router.completion")
    def test_ollama_parsing_with_broken_json_fails(self, mock_completion):
        """Ollama 반환값이 올바른 JSON 포맷이 아닐 때 (스키마 붕괴) None 반환 검증"""
        # Given: 깨진 JSON 텍스트 반환 모킹
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"vendor_name": "스타벅스", "vendor_registration_number": "1208612345", broken_json_here...'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # When
        client = ReceiptLLMClient()
        result = client.parse_receipt_local("fake ocr text")

        # Then
        self.assertIsNone(result)

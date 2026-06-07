from unittest.mock import patch

from apps.ledgers.models import Ledger
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class ReceiptUploadViewTest(TestCase):
    """
    [T008] [US1] ReceiptUploadView API E2E 통합 테스트
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="viewuser", email="viewuser@example.com", password="viewuser123")
        cls.upload_url = reverse("receipt-upload")

    def setUp(self):
        # 인증용 토큰 헤더 생성
        token = AccessToken.for_user(self.user)
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        # 가상의 1픽셀 이미지 데이터 준비 (Pillow 2차 변환용)
        # 1x1 투명 GIF 바이트
        self.dummy_image_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        self.uploaded_file = SimpleUploadedFile(
            name="test_receipt.gif", content=self.dummy_image_bytes, content_type="image/gif"
        )

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt")
    def test_receipt_upload_success(self, mock_parse_receipt):
        """영수증 이미지 업로드 성공 시, 동기적으로 가계부에 적재되고 COMPLETED 응답을 반환하는지 검증"""
        # Gemini API Mock 응답 데이터 설정
        mock_parse_receipt.return_value = {
            "vendor_name": "스타벅스 역삼대로점",
            "vendor_registration_number": "1208612345",
            "transaction_date": "2026-06-07T12:34:56Z",
            "total_amount": 15000.00,
            "items": [
                {"item_name": "카페아메리카노 Tall", "unit_price": 4500.00, "quantity": 2, "total_price": 9000.00},
                {"item_name": "부드러운 생크림 카스텔라", "unit_price": 6000.00, "quantity": 1, "total_price": 6000.00},
            ],
        }

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 10초 이내 동기 갱신 응답 검증 (HTTP 200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "COMPLETED")
        self.assertIsNone(response.data["job_id"])

        # 적재된 가계부 마스터 및 세부 품목 DB 검증
        self.assertTrue(Ledger.objects.filter(user=self.user, vendor_registration_number="1208612345").exists())
        ledger = Ledger.objects.get(user=self.user, vendor_registration_number="1208612345")
        self.assertEqual(ledger.items.count(), 2)
        self.assertEqual(ledger.total_amount, 15000.00)

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt")
    def test_receipt_upload_duplicate_error(self, mock_parse_receipt):
        """동일한 가계부 내역이 중복 적재 시도될 때 409 Conflict로 차단되는지 검증"""
        # 먼저 하나의 가계부를 직접 적재
        Ledger.objects.create(
            user=self.user,
            vendor_name="스타벅스 역삼대로점",
            vendor_registration_number="1208612345",
            transaction_date="2026-06-07",
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64,
        )

        # Gemini Mock 응답 데이터 설정 (동일 내역)
        mock_parse_receipt.return_value = {
            "vendor_name": "스타벅스 역삼대로점",
            "vendor_registration_number": "1208612345",
            "transaction_date": "2026-06-07T12:34:56Z",
            "total_amount": 15000.00,
            "items": [],
        }

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 409 Conflict 에러 및 차단 응답 검증
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error_code"], "DUPLICATE_RECEIPT")

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt")
    def test_receipt_upload_parsing_fail(self, mock_parse_receipt):
        """Gemini 파싱 실패(필수값 누락 등) 시 422 Unprocessable Entity를 반환하고 롤백되는지 검증"""
        # Gemini가 None 또는 파싱 오류를 반환하도록 모킹
        mock_parse_receipt.return_value = None

        ledger_count_before = Ledger.objects.count()

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 422 Unprocessable Entity 에러 검증 및 데이터 롤백 확인
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["error_code"], "PARSING_FAILED")
        self.assertEqual(Ledger.objects.count(), ledger_count_before)

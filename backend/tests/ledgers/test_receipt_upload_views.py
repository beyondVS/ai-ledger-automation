import datetime
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

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_vision")
    def test_receipt_upload_success(self, mock_parse_receipt):
        """영수증 이미지 업로드 성공 시, 비동기 접수(202) 후 Eager 모드로 가계부에 COMPLETED 적재되는지 검증"""
        from utils.llm_client import ReceiptItemSchema, ReceiptSchema

        # Gemini API Mock 응답 데이터 설정
        mock_parse_receipt.return_value = ReceiptSchema(
            vendor_name="스타벅스 역삼대로점",
            vendor_registration_number="1208612345",
            transaction_date="2026-06-07T12:34:56Z",
            total_amount=15000.00,
            category="식비",
            items=[
                ReceiptItemSchema(item_name="카페아메리카노 Tall", unit_price=4500.00, quantity=2, total_price=9000.00),
                ReceiptItemSchema(
                    item_name="부드러운 생크림 카스텔라", unit_price=6000.00, quantity=1, total_price=6000.00
                ),
            ],
        )

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 202 Accepted 접수 확인
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertIsNotNone(response.data["job_id"])

        # Eager 모드 실행 완료 후 Job 상태가 COMPLETED인지 확인
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.get(id=response.data["job_id"])
        self.assertEqual(job.status, "COMPLETED")

        # 적재된 가계부 마스터 및 세부 품목 DB 검증
        self.assertTrue(Ledger.objects.filter(user=self.user, vendor_registration_number="1208612345").exists())
        ledger = Ledger.objects.get(user=self.user, vendor_registration_number="1208612345")
        self.assertEqual(ledger.items.count(), 2)
        self.assertEqual(ledger.total_amount, 15000.00)

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_vision")
    def test_receipt_upload_duplicate_error(self, mock_parse_receipt):
        """동일한 가계부 내역이 중복 적재 시도될 때 비동기 처리에서 FAILED로 격리 차단되는지 검증"""
        # 먼저 하나의 가계부를 직접 적재
        Ledger.objects.create(
            user=self.user,
            vendor_name="스타벅스 역삼대로점",
            vendor_registration_number="1208612345",
            transaction_date=datetime.datetime.fromisoformat("2026-06-07T12:34:56Z".replace("Z", "+00:00")),
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64,
        )

        from utils.llm_client import ReceiptSchema

        # Gemini Mock 응답 데이터 설정 (동일 내역)
        mock_parse_receipt.return_value = ReceiptSchema(
            vendor_name="스타벅스 역삼대로점",
            vendor_registration_number="1208612345",
            transaction_date="2026-06-07T12:34:56Z",
            total_amount=15000.00,
            category="식비",
            items=[],
        )

        ledger_count_before = Ledger.objects.count()

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 202 Accepted 접수 확인
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Eager 모드 실행 후 중복 제약에 걸려 FAILED 상태가 되었는지 확인
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.get(id=response.data["job_id"])
        self.assertEqual(job.status, "FAILED")

        # 중복 차단되어 가계부 총 개수가 늘어나지 않았는지 확인
        self.assertEqual(Ledger.objects.count(), ledger_count_before)

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_vision")
    def test_receipt_upload_parsing_fail(self, mock_parse_receipt):
        """Gemini 파싱 실패(필수값 누락 등) 시 비동기 작업이 FAILED가 되고 정상 롤백되는지 검증"""
        # Gemini가 None 또는 파싱 오류를 반환하도록 모킹
        mock_parse_receipt.return_value = None

        ledger_count_before = Ledger.objects.count()

        # API 호출
        response = self.client.post(self.upload_url, {"image": self.uploaded_file}, format="multipart", **self.headers)

        # 202 Accepted 접수 확인
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # Eager 모드 실행 후 파싱 에러로 FAILED 상태가 되었는지 확인
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.get(id=response.data["job_id"])
        self.assertEqual(job.status, "FAILED")

        # 가계부 및 상세 데이터 롤백 확인
        self.assertEqual(Ledger.objects.count(), ledger_count_before)

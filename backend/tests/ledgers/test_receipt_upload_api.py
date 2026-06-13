import datetime
import uuid
from unittest.mock import MagicMock, patch

from apps.accounts.models import User
from apps.ledgers.models import Ledger, MerchantTemplate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient


class ReceiptUploadAPITestCase(TestCase):
    """
    [T008] ReceiptUploadView API 통합 테스트 케이스
    - DRF APIClient의 force_authenticate를 활용하여 last_login 필드가 없는 커스텀 유저 로그인을 지원합니다.
    """

    @classmethod
    def setUpTestData(cls):
        # 헌법 제VIII조 준수: setUpTestData(cls)를 통한 공통 테스트 유저 생성
        cls.user = User.objects.create(username="testuser", email="testuser@example.com")
        cls.upload_url = reverse("receipt-upload")

        # [T008] 캐시 바이패스 검증을 위한 승인된 템플릿 세팅
        MerchantTemplate.objects.create(
            vendor_registration_number="1208612345",
            vendor_name="스타벅스 역삼역점",
            parsing_rules={
                "merchant_name_regex": "스타벅스\\s+\\S+",
                "total_amount_regex": "합계\\s+(\\d+)",
                "date_pattern": r"날짜:\s*([\d\-]+)",
                "default_items": [
                    {"name": "아이스 아메리카노", "quantity": 2, "price": 5000.00},
                    {"name": "초콜릿 칩 스콘", "quantity": 1, "price": 5000.00},
                ],
            },
            is_verified=True,
        )

    def setUp(self):
        # DRF APIClient 및 force_authenticate 적용으로 last_login 세이브 에러 회피
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("fitz.open")
    def test_receipt_upload_success_and_db_persistence(self, mock_fitz_open):
        # Given: fitz.open().page.get_text() 모킹
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "스타벅스 역삼역점\n사업자번호: 120-86-12345\n합계 15000\n날짜: 2026-06-11"
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        # 1. 가상 영수증 PDF 데이터 생성
        dummy_image_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        receipt_image = SimpleUploadedFile(
            name="starbucks.pdf", content=dummy_image_bytes, content_type="application/pdf"
        )

        # 2. 비동기 업로드 API 요청
        response = self.client.post(self.upload_url, {"file": receipt_image}, format="multipart")

        # 3. 응답 데이터 스펙 검증
        self.assertEqual(response.status_code, 202)
        response_json = response.json()

        # 3주차 비동기 대응 하위 호환성 필드 검증 (job_id, status)
        self.assertIn("job_id", response_json)
        self.assertEqual(response_json["status"], "PENDING")

        # 4. Eager 모드 실행 완료 후 데이터베이스 원자적 트랜잭션 적재 결과 검증 (헌법 I조 수호)
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.select_related("ledger").get(id=response_json["job_id"])
        self.assertEqual(job.status, "COMPLETED")
        self.assertIsNotNone(job.ledger)

        ledger = job.ledger
        self.assertEqual(ledger.vendor_registration_number, "1208612345")
        self.assertEqual(ledger.total_amount, 15000.00)
        self.assertEqual(ledger.items.count(), 2)

    def test_receipt_upload_unauthenticated(self):
        # 비인증 상태 요청 시 401 Unauthorized 검증
        self.client.force_authenticate(user=None)
        receipt_image = SimpleUploadedFile(name="test.jpg", content=b"dummy_data", content_type="image/jpeg")
        response = self.client.post(self.upload_url, {"file": receipt_image})
        self.assertEqual(response.status_code, 401)

    def test_receipt_status_not_found(self):
        # [T017] 존재하지 않는 UUID 조회 시 404 반환 검증
        random_job_id = uuid.uuid4()
        status_url = reverse("receipt-status", kwargs={"job_id": random_job_id})
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 404)

    def test_receipt_status_success(self):
        # [T017] ReceiptUploadJob 수동 생성하여 단계적 상태 조회 검증
        from apps.ledgers.models import ReceiptUploadJob

        # 1. PENDING 상태 조회 검증
        job = ReceiptUploadJob.objects.create(user=self.user, status="PENDING", raw_file_name="pending_receipt.jpg")
        status_url = reverse("receipt-status", kwargs={"job_id": job.id})
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")
        self.assertEqual(response.json()["job_id"], str(job.id))

        # 2. PROCESSING 상태 조회 검증
        job.status = "PROCESSING"
        job.save()
        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PROCESSING")

        # 3. COMPLETED 상태 및 가계부 레코드 바인딩 데이터 조회 검증
        ledger = Ledger.objects.create(
            user=self.user,
            vendor_registration_number="1208612345",
            vendor_name="스타벅스",
            transaction_date=timezone.make_aware(datetime.datetime(2026, 6, 3)),
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64,
        )
        job.status = "COMPLETED"
        job.ledger = ledger
        job.save()

        response = self.client.get(status_url)
        self.assertEqual(response.status_code, 200)
        resp_json = response.json()
        self.assertEqual(resp_json["status"], "COMPLETED")
        self.assertIn("data", resp_json)
        self.assertEqual(resp_json["data"]["ledger_id"], str(ledger.id))
        self.assertEqual(resp_json["data"]["merchant_name"], "스타벅스")
        self.assertEqual(float(resp_json["data"]["total_amount"]), 15000.00)

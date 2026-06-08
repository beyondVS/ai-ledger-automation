from unittest.mock import patch

from apps.accounts.models import User
from apps.ledgers.models import ReceiptUploadJob
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class ReceiptAsyncJobsTests(APITestCase):
    """
    [T008] ReceiptAsyncJobsTests
    - 영수증 비동기 업로드 및 작업 상태 조회 API 연동을 검증하는 통합 테스트입니다.
    - 실제 구현에 앞서 테스트가 실패(Red)함을 입증하기 위해 선제 도입되었습니다.
    """

    @classmethod
    def setUpTestData(cls):
        # 헌법 제VIII조 수호: setUpTestData를 통해 초기 공통 셋업 데이터 오버헤드 최소화
        cls.user = User.objects.create_user(
            email="test_user@example.com",
            password="test_secure_password123!",
            username="testuser",
        )
        cls.upload_url = reverse("receipt-upload")

    def setUp(self):
        # JWT 인증 주입
        self.client.force_authenticate(user=self.user)

    @patch("apps.tasks.tasks.extract_receipt_text_task.delay")
    def test_receipt_upload_async_accepts_and_returns_job_id(self, mock_delay):
        """
        영수증 업로드 요청 시 202 Accepted 응답과 함께 임시 작업 UUID를 받는지 확인합니다.
        """
        # 유효한 1x1 GIF 이미지 바이트 (Pillow 이미지 판독 통과)
        valid_gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        test_file = SimpleUploadedFile("receipt.jpg", valid_gif_bytes, content_type="image/jpeg")

        response = self.client.post(self.upload_url, {"file": test_file}, format="multipart")

        # 202 Accepted 검증
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("job_id", response.data)
        self.assertEqual(response.data["status"], "PENDING")

        # Celery 태스크가 정상적으로 트리거되었는지 검증
        mock_delay.assert_called_once()

    def test_receipt_job_status_polling(self):
        """
        생성된 job_id로 비동기 작업 진행 상태를 폴링하여 조회할 수 있는지 검증합니다.
        """
        job = ReceiptUploadJob.objects.create(
            user=self.user,
            status="PENDING",
            raw_file_name="receipt.jpg",
        )

        status_url = reverse("receipt-job-status", kwargs={"job_id": job.id})
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["job_id"], str(job.id))
        self.assertEqual(response.data["status"], "PENDING")

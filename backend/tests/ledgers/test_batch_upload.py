import os
from unittest.mock import patch

from apps.accounts.models import User
from apps.ledgers.models import Ledger, ReceiptUploadJob
from apps.tasks.tasks import extract_receipt_text_task
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class ReceiptBatchUploadAPITests(APITestCase):
    """
    [T015] ReceiptBatchUploadAPITests
    - 10개 이상의 영수증을 동시 업로드할 때 웹 서버가 타임아웃 없이 비동기 큐로 작업을 안전하게 넘기고
      202 Accepted와 작업 ID 리스트를 정상적으로 반환하는지 검증합니다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="batch_user@example.com",
            password="test_secure_password123!",
            username="batchuser",
        )
        cls.upload_url = reverse("receipt-upload")

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    @patch("apps.tasks.tasks.extract_receipt_text_task.delay")
    def test_batch_upload_accepts_multiple_files_and_returns_list_of_jobs(self, mock_delay):
        """
        10개의 영수증 이미지 파일을 한 번에 업로드할 때,
        각각의 비동기 Job ID와 PENDING 상태가 담긴 리스트 응답을 받는지 확인합니다.
        """
        valid_gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

        # 10개의 가상 파일 생성
        files = []
        for i in range(10):
            files.append(SimpleUploadedFile(f"receipt_{i}.jpg", valid_gif_bytes, content_type="image/jpeg"))

        # DRF multipart 포맷으로 다중 파일을 동일 키('file')에 리스트 형태로 전송
        response = self.client.post(self.upload_url, {"file": files}, format="multipart")

        # 202 Accepted 검증
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        # 리스트 형식 응답 및 개수 검증
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 10)

        for job_data in response.data:
            self.assertIn("job_id", job_data)
            self.assertEqual(job_data["status"], "PENDING")

        # Celery 태스크가 각각의 파일 경로와 Job ID에 맞춰 10회 정상 트리거 되었는지 검증
        self.assertEqual(mock_delay.call_count, 10)


class CeleryTaskRetryAndFailureTests(TransactionTestCase):
    """
    [T015] CeleryTaskRetryAndFailureTests
    - 비동기 Celery 태스크 처리 중 예외 발생 시, 최대 3회의 지수 백오프 재시도가 작동하는지 검증합니다.
    - 최종 실패 시 LedgerJob에 에러 내역이 정상 반영되고 트랜잭션 롤백 무결성이 유지되는지 검증합니다.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="retry_user@example.com",
            password="test_secure_password123!",
            username="retryuser",
        )

    def test_celery_task_retries_on_transient_failure_and_finally_fails(self):
        """
        외부 API 호출 등 일시적 예외 발생 시 태스크가 재시도(retry)되며,
        재시도 횟수 초과 시 최종 실패(FAILED)로 기록되고 DB 무결성이 유지되는지 검증합니다.
        """
        # 임시 이미지 생성
        valid_gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        fake_file_dir = "uploads/receipts"
        os.makedirs(fake_file_dir, exist_ok=True)
        fake_file_path = os.path.join(fake_file_dir, "retry_receipt.jpg")
        with open(fake_file_path, "wb") as f:
            f.write(valid_gif_bytes)

        # Job 생성
        job = ReceiptUploadJob.objects.create(
            user=self.user,
            status="PENDING",
            raw_file_name="retry_receipt.jpg",
        )

        # LLM 클라이언트가 예외를 강제 발생시키도록 모킹
        with patch(
            "utils.llm_client.ReceiptLLMClient.parse_receipt", side_effect=ValueError("Gemini API Connection Refused")
        ):
            # extract_receipt_text_task.retry가 실제 Celery 런타임이 아닌 테스트 환경에서
            # 무한 대기나 예외로 끊기도록 retry 자체를 모킹하여 재시도 흐름만 포착합니다.
            # 또한 retry 호출 시 Celery의 Retry 예외가 발생하므로 이를 시뮬레이션합니다.
            from celery.exceptions import Retry

            mock_retry_exception = Retry("Simulated Retry", None)

            with patch(
                "apps.tasks.tasks.extract_receipt_text_task.retry", side_effect=mock_retry_exception
            ) as mock_retry:
                with self.assertRaises(Retry):
                    extract_receipt_text_task(str(job.id), fake_file_path)

                # retry가 한 번 호출되었는지 확인
                mock_retry.assert_called_once()
                # retry 시 인자로 countdown 및 max_retries가 잘 기입되었는지 확인
                called_kwargs = mock_retry.call_args[1]
                self.assertEqual(called_kwargs.get("max_retries"), 3)
                self.assertIn("countdown", called_kwargs)

        # 최종 3회 재시도 실패 상황 시뮬레이션 (MaxRetriesExceededError 등 예외 상황)
        # 태스크 내에서 재시도 횟수 한도를 넘었을 때 FAILED 상태 기록과 롤백 무결성 확인
        # self.request.retries를 3으로 모킹하여 재시도 조건(retries < max_retries)을 우회하고 최종 실패 분기로 보냅니다.
        from unittest.mock import PropertyMock

        with patch("utils.llm_client.ReceiptLLMClient.parse_receipt", side_effect=ValueError("Gemini API Down")):
            with patch("celery.app.task.Context.retries", new_callable=PropertyMock, return_value=3):
                try:
                    extract_receipt_text_task(str(job.id), fake_file_path)
                except Exception:
                    pass

        # 최종 작업 상태 확인
        job.refresh_from_db()
        self.assertEqual(job.status, "FAILED")
        self.assertIsNotNone(job.failure_reason)
        self.assertIn("영수증 이미지 분석 또는 데이터 파싱에 실패했습니다.", job.failure_reason)

        # 트랜잭션 롤백 무결성 확인: 실패한 Job과 엮인 Ledger 데이터가 없어야 함
        self.assertIsNone(job.ledger)
        self.assertEqual(Ledger.objects.filter(upload_job=job).count(), 0)

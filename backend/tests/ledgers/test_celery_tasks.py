from unittest.mock import patch

from apps.accounts.models import User
from apps.ledgers.models import ReceiptUploadJob
from apps.tasks.tasks import extract_receipt_text_task
from django.test import TestCase, override_settings


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CeleryTasksTests(TestCase):
    """
    [T009] CeleryTasksTests
    - extract_receipt_text_task 비동기 태스크의 생명주기 및 데이터 트랜잭션 성공을 검증하는 테스트입니다.
    - 실제 구현에 앞서 테스트가 실패(Red)함을 입증하기 위해 선제 도입되었습니다.
    """

    @classmethod
    def setUpTestData(cls):
        # 헌법 제VIII조 수호: setUpTestData를 통해 초기 공통 셋업 데이터 오버헤드 최소화
        cls.user = User.objects.create_user(
            email="test_worker_user@example.com",
            password="test_secure_password123!",
            username="workeruser",
        )

    def test_extract_receipt_text_task_success_transitions_job_and_creates_ledger(self):
        """
        비동기 태스크가 정상 실행되면 ReceiptUploadJob의 상태가 SUCCESS가 되고,
        데이터베이스에 Ledger 및 LedgerItem이 원자적으로 생성되어야 합니다.
        """
        import os

        fake_file_dir = "uploads/receipts"
        os.makedirs(fake_file_dir, exist_ok=True)
        fake_file_path = os.path.join(fake_file_dir, "test_receipt.jpg")
        valid_gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        with open(fake_file_path, "wb") as f:
            f.write(valid_gif_bytes)

        # 임시 업로드 작업 생성
        job = ReceiptUploadJob.objects.create(
            user=self.user,
            status="PENDING",
            raw_file_name="receipt.jpg",
        )

        # OCR 및 LLM 파서 모듈을 모킹하여 성공적인 분석 결과 데이터가 반환되도록 설정
        mock_parsed_data = {
            "vendor_name": "테스트 편의점",
            "vendor_registration_number": "1234567890",
            "transaction_date": "2026-06-08",
            "total_amount": 5000.00,
            "supply_value": 4545.45,
            "vat_amount": 454.55,
            "category": "식비",
            "items": [
                {
                    "item_name": "삼각김밥",
                    "quantity": 2,
                    "unit_price": 1500.00,
                    "total_price": 3000.00,
                },
                {
                    "item_name": "생수",
                    "quantity": 1,
                    "unit_price": 2000.00,
                    "total_price": 2000.00,
                },
            ],
        }

        # 실제 tasks.py 내의 LLM 클라이언트 모듈(예: ReceiptLLMClient 또는 litellm 연동 부)을 모킹하여
        # 고정된 mock_parsed_data를 던지게끔 패치합니다.
        with patch("utils.llm_client.ReceiptLLMClient.parse_receipt", return_value=mock_parsed_data):
            # 태스크 직접 호출 (eager 모드이므로 동기 실행됨)
            extract_receipt_text_task(str(job.id), fake_file_path)

        # 결과 검증
        job.refresh_from_db()
        self.assertEqual(job.status, "COMPLETED")
        self.assertIsNotNone(job.ledger)

        # 트랜잭션 원자성 생성 및 헌법 I조 수호 검증
        ledger = job.ledger
        self.assertEqual(ledger.vendor_name, "테스트 편의점")
        self.assertEqual(ledger.total_amount, 5000.00)
        self.assertEqual(ledger.user, self.user)

        # 1:N 품목 데이터 관계 검증
        items = ledger.items.all()
        self.assertEqual(items.count(), 2)
        self.assertEqual(items[0].item_name, "삼각김밥")
        self.assertEqual(items[1].item_name, "생수")

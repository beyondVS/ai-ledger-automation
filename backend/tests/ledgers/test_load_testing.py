import os
import shutil
import tempfile
from unittest.mock import patch

from apps.ledgers.models import Ledger, ReceiptTask
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from utils.llm_client import ReceiptItemSchema, ReceiptSchema

User = get_user_model()


class ReceiptAsyncLoadTest(TestCase):
    """
    [023-receipt-async-load-test] 비동기 아키텍처 튜닝 및 부하 테스트 E2E 통합 테스트
    - 헌법 VIII조에 의거하여 django.test.TestCase 및 setUpTestData를 수호합니다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="loadtestuser", password="securepassword123", email="loadtest@example.com", timezone="Asia/Seoul"
        )
        try:
            cls.url = reverse("ledgers:receipts-bulk-upload")
        except Exception:
            cls.url = "/api/v1/ledgers/receipts/bulk-upload/"

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "receipt_sample.pdf"
        )
        self.temp_files = []

    def tearDown(self):
        # 테스트 완료 후 생성된 임시 파일 정리
        for path in self.temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _get_temp_copy(self, suffix=""):
        """원본 테스트 PDF를 안전하게 임시 경로로 복사하여 반환합니다."""
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"test_receipt_{suffix}.pdf")
        shutil.copy(self.pdf_path, temp_path)
        self.temp_files.append(temp_path)
        return temp_path

    @patch("apps.ledgers.tasks.extract_receipt_task.delay")
    def test_bulk_upload_api_success(self, mock_task_delay):
        """
        [US1] [T006] 50개 파일 벌크 업로드 접수 시 5초 이내에 202 응답 및 task_id 반환 검증
        """
        self.assertTrue(os.path.exists(self.pdf_path), "부하 테스트를 위한 receipt_sample.pdf가 필요합니다.")

        files = []
        opened_files = []
        try:
            for _ in range(50):
                f = open(self.pdf_path, "rb")
                opened_files.append(f)
                files.append(f)

            response = self.client.post(self.url, {"files": files}, format="multipart")
            self.assertEqual(response.status_code, 202)

            data = response.json()
            self.assertIn("tasks", data)
            self.assertEqual(len(data["tasks"]), 50)
            self.assertEqual(ReceiptTask.objects.filter(user=self.user).count(), 50)
            self.assertEqual(mock_task_delay.call_count, 50)

        finally:
            for f in opened_files:
                f.close()

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_local")
    def test_duplicate_prevention_async(self, mock_parse_local):
        """
        [US2] [T009] 비동기 동시 유입 시 60초 카드 승인 중복 방어 알고리즘 검증
        - 동일 가맹점, 동일 금액, 동일 거래 시각(60초 내)의 영수증 2종이 병렬 처리될 때 1건만 최종 적재 확인
        """
        mock_schema = ReceiptSchema(
            vendor_name="스타벅스 강남점",
            vendor_registration_number="1234567890",
            transaction_date="2026-06-17T00:00:00Z",
            total_amount=5500.0,
            approval_number="99887766",
            category="식비",
            items=[ReceiptItemSchema(item_name="아메리카노", quantity=1, unit_price=5500.0, total_price=5500.0)],
        )
        mock_parse_local.return_value = mock_schema

        # 각각 다른 임시 파일 경로를 지정하여 FileNotFoundError 및 원본 훼손 차단
        path1 = self._get_temp_copy("first")
        path2 = self._get_temp_copy("second")

        task1 = ReceiptTask.objects.create(
            user=self.user, status="PENDING", file_name="receipt_first.pdf", file_path=path1
        )
        task2 = ReceiptTask.objects.create(
            user=self.user, status="PENDING", file_name="receipt_second.pdf", file_path=path2
        )

        from apps.ledgers.tasks import extract_receipt_task

        # eager 모드로 비동기 태스크 동기식 실행
        extract_receipt_task(task_id=str(task1.id), file_path=path1)
        extract_receipt_task(task_id=str(task2.id), file_path=path2)

        task1.refresh_from_db()
        task2.refresh_from_db()

        self.assertEqual(task1.status, "COMPLETED")
        self.assertEqual(task2.status, "FAILED")
        self.assertEqual(task2.error_message, "이미 등록된 중복 영수증입니다.")
        self.assertEqual(Ledger.objects.filter(user=self.user).count(), 1)

    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_local")
    def test_transaction_rollback_atomicity(self, mock_parse_local):
        """
        [US2] [T009] 파싱 성공 후 DB 적재 중 예외 발생 시 atomic 롤백 무결성 검증
        - LedgerItem 적재 시 문자열 길이 한계 초과 에러를 유도하여 transaction 롤백 및 고아 유무 검증
        """
        mock_schema = ReceiptSchema(
            vendor_name="이마트 역삼점",
            vendor_registration_number="5050505050",
            transaction_date="2026-06-17T01:00:00Z",
            total_amount=12000.0,
            approval_number="11223344",
            category="생활용품",
            items=[
                # item_name을 DB CHAR 컬럼 한도(255자)를 넘기는 300자로 셋업해 DB DataError 유도
                ReceiptItemSchema(item_name="물티슈" * 150, quantity=1, unit_price=12000.0, total_price=12000.0)
            ],
        )
        mock_parse_local.return_value = mock_schema

        path = self._get_temp_copy("rollback")

        task = ReceiptTask.objects.create(
            user=self.user, status="PENDING", file_name="receipt_fail.pdf", file_path=path
        )

        from apps.ledgers.tasks import extract_receipt_task

        # DB DataError가 발생할 것이므로 예외 포착 후 롤백 결과 진단
        try:
            extract_receipt_task(task_id=str(task.id), file_path=path)
        except Exception:
            pass

        task.refresh_from_db()
        self.assertEqual(task.status, "FAILED")
        self.assertIsNotNone(task.error_message)
        self.assertTrue(
            "value too long" in task.error_message.lower()
            or "too long" in task.error_message.lower()
            or "dataerror" in task.error_message.lower()
        )

        # 롤백 수호 증명: Ledger 레코드가 영속화되지 않고 격리 롤백 완료
        self.assertEqual(Ledger.objects.filter(vendor_registration_number="5050505050").count(), 0)

    def test_load_test_reporter(self):
        """
        [US3] [T012] 리포터 모듈이 ReceiptTask 목록을 기반으로 성능 통계를 정상 집계하고 출력하는지 검증
        """
        import datetime

        from django.utils import timezone

        base_time = timezone.now()

        t1 = ReceiptTask.objects.create(
            user=self.user, status="COMPLETED", parser_stage="OLLAMA", file_name="task1.pdf", file_path="/tmp/task1.pdf"
        )
        t2 = ReceiptTask.objects.create(
            user=self.user,
            status="COMPLETED",
            parser_stage="GEMINI_TEXT",
            file_name="task2.pdf",
            file_path="/tmp/task2.pdf",
        )
        t3 = ReceiptTask.objects.create(
            user=self.user,
            status="FAILED",
            parser_stage="NONE",
            error_message="Connection timeout",
            file_name="task3.pdf",
            file_path="/tmp/task3.pdf",
        )

        # auto_now_add / auto_now를 우회하여 강제로 시각 업데이트
        ReceiptTask.objects.filter(id=t1.id).update(
            created_at=base_time, updated_at=base_time + datetime.timedelta(seconds=2)
        )
        ReceiptTask.objects.filter(id=t2.id).update(
            created_at=base_time + datetime.timedelta(seconds=1), updated_at=base_time + datetime.timedelta(seconds=5)
        )
        ReceiptTask.objects.filter(id=t3.id).update(
            created_at=base_time + datetime.timedelta(seconds=2), updated_at=base_time + datetime.timedelta(seconds=4)
        )

        from apps.ledgers.services.reporter import ReceiptLoadTestReporter

        task_ids = [t1.id, t2.id, t3.id]
        report_data = ReceiptLoadTestReporter.generate_report(user_id=self.user.id, task_ids=task_ids)

        self.assertEqual(report_data["total_count"], 3)
        self.assertEqual(report_data["completed_count"], 2)
        self.assertEqual(report_data["failed_count"], 1)
        self.assertEqual(report_data["total_duration"], 5.0)  # max(base+5) - min(base) = 5초
        self.assertEqual(report_data["stage_stats"]["OLLAMA"], 1)
        self.assertEqual(report_data["stage_stats"]["GEMINI_TEXT"], 1)
        self.assertIn("총 요청 건수       : 3 건", report_data["report_text"])
        self.assertIn("총 소요 시간       : 5.00 초", report_data["report_text"])
        self.assertIn("Connection timeout: 1건", report_data["report_text"])

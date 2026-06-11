import json
import os

from apps.accounts.models import User
from apps.ledgers.exceptions import DuplicatePaymentError
from apps.ledgers.models import Ledger, LedgerItem
from apps.ledgers.services import create_ledger_transactional
from apps.tasks.models import FailedTask
from django.test import TestCase
from utils.pdf_extractor import PDFTextExtractor


class TestPDFIntegrationSuite(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        [T006] [US1] 클래스 기동 시 최초 1회 가짜 유저 데이터를 격리 적재하여 DB 부하를 차단합니다.
        """
        cls.user = User.objects.create(email="integration_test@example.com")
        cls.user_id_str = str(cls.user.id)

        # [T001]에서 생성해둔 표준 영수증 PDF 파일의 디스크 절대 경로 확보
        # conftest.py 등을 타지 않고 테스트 파일 기준으로 경로를 안전하게 획득
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cls.pdf_path = os.path.join(base_dir, "tests", "resources", "receipt_sample.pdf")

    def test_normal_pdf_ingestion(self):
        """
        [T007, T008] [US1]
        - 실제 로컬 PDF를 바이트로 로드해 PDFTextExtractor로 파싱을 성공시키고,
        - create_ledger_transactional 서비스를 호출해 정상 커밋 적재됨을 검증합니다.
        """
        # 1. 로컬 PDF 바이트 스트림 로드
        self.assertTrue(os.path.exists(self.pdf_path), msg=f"PDF Sample file does not exist at {self.pdf_path}")
        with open(self.pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # 2. PDFTextExtractor 가동 및 텍스트 추출 검증
        from io import BytesIO

        stream = BytesIO(pdf_bytes)
        extractor = PDFTextExtractor(file_source=stream)
        result = extractor.extract_text(layout=True)

        self.assertTrue(result.success, msg=result.error_message)
        self.assertIn("HongKongBanJum", result.raw_text)
        self.assertIn("1208147528", result.raw_text)
        self.assertIn("24000.00", result.raw_text)

        # 3. 추출된 데이터를 가공한 서비스 입력 페이로드 구성
        ledger_data = {
            "vendor_registration_number": "1208147528",
            "vendor_name": "홍콩반점",
            "transaction_date": "2026-05-29",
            "total_amount": 24000.00,
            "supply_value": 21818.18,
            "vat_amount": 2181.82,
            "raw_llm_response": result.raw_text,
        }

        items_data = [
            {"item_name": "짜장면 곱빼기", "quantity": 2, "unit_price": 7000.00, "total_price": 14000.00},
            {"item_name": "탕수육 소", "quantity": 1, "unit_price": 10000.00, "total_price": 10000.00},
        ]

        # 4. 트랜잭션 적재 기동 및 상태 검증
        res = create_ledger_transactional(self.user_id_str, ledger_data, items_data)
        self.assertEqual(res["status"], "SUCCESS")

        # DB 영속화 적재 수량 단언 검증
        self.assertEqual(Ledger.objects.filter(user=self.user, vendor_registration_number="1208147528").count(), 1)
        ledger_record = Ledger.objects.filter(user=self.user, vendor_registration_number="1208147528").first()
        self.assertEqual(LedgerItem.objects.filter(ledger=ledger_record).count(), 2)

    def test_duplicate_pdf_isolation(self):
        """
        [T009, T010, T011] [US2]
        - 동일한 PDF 데이터를 지닌 영수증을 2회 연속 중복 적재 요청 시,
        - 고유 제약조건 예외가 정확하게 발생하고 롤백 및 FailedTask 격리가 완료되는지 검증합니다.
        """
        ledger_data = {
            "vendor_registration_number": "1208147528",
            "vendor_name": "홍콩반점",
            "transaction_date": "2026-05-29",
            "total_amount": 24000.00,
            "supply_value": 21818.18,
            "vat_amount": 2181.82,
        }

        items_data = [
            {"item_name": "짜장면 곱빼기", "quantity": 2, "unit_price": 7000.00, "total_price": 14000.00},
            {"item_name": "탕수육 소", "quantity": 1, "unit_price": 10000.00, "total_price": 10000.00},
        ]

        # 1. 1차 인서트 시도: 정상 성공해야 함
        res1 = create_ledger_transactional(self.user_id_str, ledger_data, items_data)
        self.assertEqual(res1["status"], "SUCCESS")

        # 2. 2차 인서트 시도: UNIQUE 복합 고유 키 충돌로 DuplicatePaymentError 발생 보장
        with self.assertRaises(DuplicatePaymentError):
            create_ledger_transactional(self.user_id_str, ledger_data, items_data)

        # 3. 2차 중복은 롤백되어 DB에 2번째 마스터 행이 증식되지 않았음을 입증 (여전히 1개)
        self.assertEqual(Ledger.objects.filter(user=self.user, vendor_registration_number="1208147528").count(), 1)

        # 4. FailedTask DLQ 테이블에 격리 완료되었는지 확인 및 복원력 검증
        self.assertTrue(FailedTask.objects.filter(user=self.user, task_type="API_LEDGER_INGEST_DUPLICATE").exists())
        failed_log = FailedTask.objects.filter(user=self.user, task_type="API_LEDGER_INGEST_DUPLICATE").first()
        self.assertIsNotNone(failed_log.error_message)

        payload = json.loads(failed_log.raw_payload)
        self.assertEqual(payload["ledger_data"]["vendor_name"], "홍콩반점")
        self.assertEqual(float(payload["ledger_data"]["total_amount"]), 24000.00)

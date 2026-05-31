import json
from django.test import TestCase
from django.db import IntegrityError
from apps.accounts.models import User
from apps.ledgers.models import Ledger
from apps.tasks.models import FailedTask
from apps.ledgers.services import create_ledger_transactional

class TestLedgerDuplicateIngestion(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        클래스 최초 실행 시 테스트용 사용자를 단 1회만 생성하여 DB 인서트 오버헤드를 극대화로 예방합니다.
        """
        cls.user = User.objects.create(email="merchant_dup@example.com")
        cls.user_id_str = str(cls.user.id)

    def test_duplicate_ledger_block_and_failed_task_routing(self):
        """
        동일한 사용자가 같은 날짜, 가맹점 사업자등록번호, 거래 총액을 가진 영수증을
        2회 연속 적재를 시도했을 때, 복합 고유 키 인덱스 충돌로 인해
        2번째 인서트가 차단되며 해당 정보가 FailedTask에 무손실 격리 기록되는지 검증합니다.
        """
        ledger_data = {
            "vendor_registration_number": "1208147528",  # 동일 사업자번호
            "vendor_name": "홍콩반점",
            "transaction_date": "2026-05-29",           # 동일 날짜
            "total_amount": 24000.00,                   # 동일 총액
            "supply_value": 21818.18,
            "vat_amount": 2181.82,
        }
        
        items_data = [
            {"item_name": "짜장면 곱빼기", "quantity": 2, "unit_price": 7000.00, "total_price": 14000.00},
            {"item_name": "탕수육 소", "quantity": 1, "unit_price": 10000.00, "total_price": 10000.00}
        ]
        
        # 1. 1차 인서트 시도: 성공해야 함
        result1 = create_ledger_transactional(self.user_id_str, ledger_data, items_data)
        self.assertEqual(result1["status"], "SUCCESS")
        self.assertEqual(Ledger.objects.filter(vendor_registration_number="1208147528").count(), 1)
        
        # 2. 2차 인서트 시도: 동일 페이로드 적재 시 DB 고유 키 위배 발생
        with self.assertRaises(IntegrityError):
            create_ledger_transactional(self.user_id_str, ledger_data, items_data)
            
        # 3. [UNIQUE 차단 수호]: 데이터베이스에 2번째 영수증 행이 적재되지 않았음을 증명 (개수 여전히 1개)
        self.assertEqual(Ledger.objects.filter(user=self.user, vendor_registration_number="1208147528").count(), 1)
        
        # 4. [FailedTask DLQ 격리 수집 검증]: 2번째 인서트 실패 페이로드가 FailedTask에 영구 격리 적재되었는지 확인
        self.assertTrue(FailedTask.objects.filter(user=self.user, task_type="API_LEDGER_INGEST_DUPLICATE").exists())
        
        failed_log = FailedTask.objects.filter(user=self.user, task_type="API_LEDGER_INGEST_DUPLICATE").first()
        self.assertIsNotNone(failed_log.error_message)
        
        # 페이로드 역직렬화 및 복원력 검증
        payload = json.loads(failed_log.raw_payload)
        self.assertEqual(payload["ledger_data"]["vendor_name"], "홍콩반점")
        self.assertEqual(float(payload["ledger_data"]["total_amount"]), 24000.00)


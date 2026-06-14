from datetime import datetime
from zoneinfo import ZoneInfo

from apps.ledgers.models import Ledger
from apps.ledgers.services import create_ledger_transactional
from django.contrib.auth import get_user_model
from django.test import TestCase
from utils.llm_client import ReceiptSchema

User = get_user_model()


class TimezonePipelineTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="ny_user",
            email="ny_user@example.com",
            password="testpassword123",
            timezone="America/New_York",  # 뉴욕 시간대 (UTC-4)
        )

    def test_receipt_ingestion_timezone_normalization(self):
        """영수증 결제일 적재 시 사용자 타임존 기준 UTC 자동 정규화 테스트"""

        # 실제 ReceiptSchema DTO로 가계부 적재 인풋 구성
        receipt_dto = ReceiptSchema(
            vendor_registration_number="1234567890",
            vendor_name="스타벅스 뉴욕점",
            transaction_date="2026-06-14 15:30:00",  # 로컬 Naive 시간 문자열
            total_amount=12500.00,
            items=[],
            category="식비",
        )

        # 가계부 적재 서비스 함수 호출
        res = create_ledger_transactional(
            user_id=str(self.user.id), receipt_data=receipt_dto, user_timezone=self.user.timezone
        )

        # 저장된 결제일시 검증
        db_ledger = Ledger.objects.get(id=res["ledger_id"])

        # 뉴욕 15:30 은 UTC 기준 19:30 이어야 함
        expected_utc = datetime(2026, 6, 14, 19, 30, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(db_ledger.transaction_date, expected_utc)

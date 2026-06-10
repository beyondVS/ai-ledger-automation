import datetime

from apps.accounts.models import User
from apps.ledgers.exceptions import DuplicatePaymentError
from apps.ledgers.services import ingest_payment_data
from django.test import TestCase
from django.utils import timezone


class DuplicatePaymentCheckUnitTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 헌법 VIII조 수호: setUpTestData로 유저 준비
        cls.user = User.objects.create_user(
            username="testuser_dup", email="testuser_dup@example.com", password="securepassword123"
        )

    def test_different_approval_numbers_are_both_allowed(self):
        """
        US2: 승인번호가 다른 경우 60초 이내라도 개별 정상 거래로 허용
        """
        base_time = timezone.now()

        payload1 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            "transaction_date": base_time.isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "APPROVAL-111",
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        payload2 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            # 10초 차이
            "transaction_date": (base_time + datetime.timedelta(seconds=10)).isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "APPROVAL-222",  # 다른 승인번호
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        # 1차 적재
        ledger1 = ingest_payment_data(self.user, payload1)
        self.assertIsNotNone(ledger1)

        # 2차 적재 (승인번호가 다르므로 성공해야 함)
        ledger2 = ingest_payment_data(self.user, payload2)
        self.assertIsNotNone(ledger2)
        self.assertNotEqual(ledger1.id, ledger2.id)

    def test_same_approval_number_within_60_seconds_is_duplicate(self):
        """
        US2: 승인번호가 동일하고 60초 이내인 경우 DuplicatePaymentError 발생
        """
        base_time = timezone.now()

        payload1 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            "transaction_date": base_time.isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "SAME-APPROVAL",
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        payload2 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            # 30초 차이
            "transaction_date": (base_time + datetime.timedelta(seconds=30)).isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "SAME-APPROVAL",  # 동일한 승인번호
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        # 1차 적재
        ingest_payment_data(self.user, payload1)

        # 2차 적재 시도 시 중복 결제 예외 발생해야 함
        with self.assertRaises(DuplicatePaymentError):
            ingest_payment_data(self.user, payload2)

    def test_same_approval_number_after_60_seconds_is_allowed(self):
        """
        US2: 승인번호가 동일하거나 없더라도 60초를 초과한 경우 개별 정상 거래로 처리
        """
        base_time = timezone.now()

        payload1 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            "transaction_date": base_time.isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "SAME-APPROVAL",
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        payload2 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            # 61초 차이 (60초 초과)
            "transaction_date": (base_time + datetime.timedelta(seconds=61)).isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": "SAME-APPROVAL",
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        # 1차 적재
        ledger1 = ingest_payment_data(self.user, payload1)
        self.assertIsNotNone(ledger1)

        # 2차 적재 (60초 초과했으므로 정상 개별 거래 처리되어야 함)
        ledger2 = ingest_payment_data(self.user, payload2)
        self.assertIsNotNone(ledger2)
        self.assertNotEqual(ledger1.id, ledger2.id)

    def test_missing_approval_number_within_60_seconds_is_duplicate(self):
        """
        US2: 승인번호가 양쪽 다 유효하지(None) 않고 60초 이내인 경우 DuplicatePaymentError 발생
        """
        base_time = timezone.now()

        payload1 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            "transaction_date": base_time.isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": None,
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        payload2 = {
            "vendor_registration_number": "1234512345",
            "vendor_name": "맥도날드",
            # 45초 차이
            "transaction_date": (base_time + datetime.timedelta(seconds=45)).isoformat(),
            "total_amount": 10000.00,
            "supply_value": 9090.91,
            "vat_amount": 909.09,
            "approval_number": None,
            "items": [
                {"item_name": "상하이 버거 세트", "unit_price": 10000.00, "quantity": 1, "total_price": 10000.00}
            ],
        }

        ingest_payment_data(self.user, payload1)

        with self.assertRaises(DuplicatePaymentError):
            ingest_payment_data(self.user, payload2)

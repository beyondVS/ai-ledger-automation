import datetime

from apps.ledgers.models import Ledger, LedgerItem
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class LedgerModelTest(TestCase):
    """
    [T007] [US1] Ledger 및 LedgerItem 트랜잭션 정합성 및 제약조건 테스트
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword123"
        )

    def test_ledger_unique_constraint(self):
        """동일 유저, 동일 사업자번호, 동일 결제일시, 동일 금액의 중복 가계부 적재 시 UNIQUE 제약조건으로 차단되는지 검증"""
        # 첫 번째 가계부 생성
        Ledger.objects.create(
            user=self.user,
            vendor_name="스타벅스",
            vendor_registration_number="1208612345",
            transaction_date=datetime.date(2026, 6, 7),
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64,
        )

        # 동일 데이터로 두 번째 가계부 생성 시 IntegrityError 발생 검증
        with self.assertRaises(IntegrityError):
            Ledger.objects.create(
                user=self.user,
                vendor_name="스타벅스 리저브",
                vendor_registration_number="1208612345",
                transaction_date=datetime.date(2026, 6, 7),
                total_amount=15000.00,
                supply_value=13636.36,
                vat_amount=1363.64,
            )

    def test_ledger_and_items_atomic_rollback(self):
        """가계부 마스터 및 세부 품목 생성 시, 품목 생성에 실패하면 전체 트랜잭션이 롤백되는지 검증"""
        # 1. 트랜잭션 원자성 테스트를 위해 실패할 세부 품목 생성 시나리오
        ledger_count_before = Ledger.objects.count()
        item_count_before = LedgerItem.objects.count()

        try:
            with transaction.atomic():
                # 마스터는 정상적으로 생성
                Ledger.objects.create(
                    user=self.user,
                    vendor_name="투썸플레이스",
                    vendor_registration_number="1208699999",
                    transaction_date=datetime.date(2026, 6, 7),
                    total_amount=10000.00,
                    supply_value=9090.91,
                    vat_amount=909.09,
                )

                # 상세 품목 저장 중 고의적 예외 유발 (예: 강제 ValueError)
                # 이 에러로 인해 transaction.atomic() 블록이 롤백되어야 함
                raise ValueError("세부 품목 적재 강제 예외")
        except ValueError:
            pass

        # 2. 예외 처리 후 DB에 아무것도 남지 않았는지(롤백) 검증
        self.assertEqual(Ledger.objects.count(), ledger_count_before)
        self.assertEqual(LedgerItem.objects.count(), item_count_before)

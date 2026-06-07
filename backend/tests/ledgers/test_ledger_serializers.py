import datetime

from apps.ledgers.models import Ledger, LedgerItem
from apps.ledgers.serializers import LedgerListSerializer
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class LedgerListSerializerTest(TestCase):
    """
    [T013] LedgerListSerializer가 LedgerItem을 items 필드로 잘 직렬화하는지 검증하는 TDD 테스트
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        cls.ledger = Ledger.objects.create(
            user=cls.user,
            vendor_name="스타벅스 역삼역점",
            vendor_registration_number="1208112345",
            transaction_date=datetime.date(2026, 6, 7),
            total_amount=13500.00,
            supply_value=12272.73,
            vat_amount=1227.27,
        )
        cls.item1 = LedgerItem.objects.create(
            ledger=cls.ledger,
            item_name="아이스 아메리카노",
            quantity=2,
            unit_price=4500.00,
            total_price=9000.00,
        )
        cls.item2 = LedgerItem.objects.create(
            ledger=cls.ledger,
            item_name="클래식 스콘",
            quantity=1,
            unit_price=4500.00,
            total_price=4500.00,
        )

    def test_ledger_list_serializer_includes_items(self):
        """LedgerListSerializer 직렬화 시 items 키 및 상세 필드가 정상 주입되는지 검증합니다."""
        serializer = LedgerListSerializer(instance=self.ledger)
        data = serializer.data

        # 1. items 키 검증
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 2)

        # 2. 첫 번째 아이템 필드 검증 (API 스펙에 맞는 name, quantity, price 인지 확인)
        first_item = data["items"][0]
        self.assertEqual(first_item["name"], "아이스 아메리카노")
        self.assertEqual(first_item["quantity"], 2)
        # DecimalField는 직렬화 결과 문자열로 반환될 수 있으므로 문자열 혹은 float으로 대조
        self.assertEqual(float(first_item["price"]), 4500.00)

        # 3. 두 번째 아이템 필드 검증
        second_item = data["items"][1]
        self.assertEqual(second_item["name"], "클래식 스콘")
        self.assertEqual(second_item["quantity"], 1)
        self.assertEqual(float(second_item["price"]), 4500.00)

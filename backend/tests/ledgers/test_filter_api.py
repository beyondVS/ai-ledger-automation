import datetime

from apps.ledgers.models import Ledger
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class LedgerFilterApiTest(TestCase):
    """
    [T019] 다차원 복합 검색 필터링 API 테스트 (TDD Red 유도)
    - 상호명 부분일치, 복수 카테고리(OR), 날짜 범위, 금액 범위를 처리하는 필터링 쿼리가 정상 작동하는지 대조 검증합니다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="user_filter", email="user_filter@example.com", password="password123"
        )

        # 1. 스타벅스 강남 (식비, 12,000원, 6월 1일)
        cls.ledger1 = Ledger.objects.create(
            user=cls.user,
            vendor_name="스타벅스 강남점",
            vendor_registration_number="1234567890",
            transaction_date=datetime.datetime(2026, 6, 1, 5, 0, 0, tzinfo=datetime.UTC),
            total_amount=12000.00,
            supply_value=10909.09,
            vat_amount=1090.91,
            category="식비",
        )

        # 2. 맥도날드 홍대 (식비, 8,500원, 6월 2일)
        cls.ledger2 = Ledger.objects.create(
            user=cls.user,
            vendor_name="맥도날드 홍대점",
            vendor_registration_number="0987654321",
            transaction_date=datetime.datetime(2026, 6, 2, 5, 0, 0, tzinfo=datetime.UTC),
            total_amount=8500.00,
            supply_value=7727.27,
            vat_amount=772.73,
            category="식비",
        )

        # 3. 유니클로 강남 (쇼핑, 49,000원, 6월 3일)
        cls.ledger3 = Ledger.objects.create(
            user=cls.user,
            vendor_name="유니클로 강남점",
            vendor_registration_number="1111111111",
            transaction_date=datetime.datetime(2026, 6, 3, 5, 0, 0, tzinfo=datetime.UTC),
            total_amount=49000.00,
            supply_value=44545.45,
            vat_amount=4454.55,
            category="쇼핑",
        )

        # 4. 이마트 역삼 (마트, 75,000원, 6월 4일)
        cls.ledger4 = Ledger.objects.create(
            user=cls.user,
            vendor_name="이마트 역삼점",
            vendor_registration_number="2222222222",
            transaction_date=datetime.datetime(2026, 6, 4, 5, 0, 0, tzinfo=datetime.UTC),
            total_amount=75000.00,
            supply_value=68181.82,
            vat_amount=6818.18,
            category="마트",
        )

        cls.list_url = reverse("ledger-list")

    def test_filter_by_vendor_name(self):
        """상호명 검색어(q) 부분 일치 필터링이 정상적으로 적용되는지 확인합니다."""
        token = AccessToken.for_user(self.user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.get(f"{self.list_url}?q=강남", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 스타벅스 강남, 유니클로 강남 2건만 조회되어야 함
        self.assertEqual(len(response.data), 2)
        vendors = [item["vendor_name"] for item in response.data]
        self.assertIn("스타벅스 강남점", vendors)
        self.assertIn("유니클로 강남점", vendors)

    def test_filter_by_multiple_categories(self):
        """복수 카테고리 쉼표 구분자(categories=식비,마트) 필터가 OR 조건으로 정상 동작하는지 확인합니다."""
        token = AccessToken.for_user(self.user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.get(f"{self.list_url}?categories=식비,마트", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 스타벅스, 맥도날드(식비) + 이마트(마트) 3건이 나와야 하고 유니클로(쇼핑)는 제외되어야 함
        self.assertEqual(len(response.data), 3)
        categories = [item["category"] for item in response.data]
        self.assertIn("식비", categories)
        self.assertIn("마트", categories)
        self.assertNotIn("쇼핑", categories)

    def test_filter_by_amount_range(self):
        """최소/최대 결제 금액 대역 필터가 정상 적용되는지 확인합니다."""
        token = AccessToken.for_user(self.user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        # 10,000원 이상 50,000원 이하 범위 (스타벅스 12000, 유니클로 49000 2건)
        response = self.client.get(f"{self.list_url}?min_amount=10000&max_amount=50000", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)
        amounts = [float(item["total_amount"]) for item in response.data]
        self.assertIn(12000.00, amounts)
        self.assertIn(49000.00, amounts)
        self.assertNotIn(8500.00, amounts)
        self.assertNotIn(75000.00, amounts)

    def test_filter_by_date_range(self):
        """시작일/종료일 기간 검색 필터가 정상 동작하는지 확인합니다."""
        token = AccessToken.for_user(self.user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        # 6월 2일부터 6월 3일까지 (맥도날드 8500, 유니클로 49000 2건)
        response = self.client.get(f"{self.list_url}?start_date=2026-06-02&end_date=2026-06-03", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)
        vendors = [item["vendor_name"] for item in response.data]
        self.assertIn("맥도날드 홍대점", vendors)
        self.assertIn("유니클로 강남점", vendors)

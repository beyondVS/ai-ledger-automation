import datetime

from apps.ledgers.models import Ledger
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class LedgerCalendarApiTest(TestCase):
    """
    [T014] 월별 캘린더 지출 요약 API 뷰 테스트 (TDD Red 유도)
    - 사용자 선호 타임존 기준 로컬 일자별 합산 금액 및 건수 집계가 정확히 반영되는지 검증합니다.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. 테스트용 유저 생성 (초기 타임존은 Asia/Seoul)
        cls.user_a = User.objects.create_user(
            username="usera_cal",
            email="usera_cal@example.com",
            password="password123",
            timezone="Asia/Seoul",
        )
        cls.user_b = User.objects.create_user(
            username="userb_cal",
            email="userb_cal@example.com",
            password="password123",
            timezone="Asia/Seoul",
        )

        # 2. 거래 내역 생성 (UTC 시간 기준으로 적재됨)
        # 거래 1: 2026-06-01 14:00:00 UTC -> 서울 시간: 2026-06-01 23:00:00 (로컬 일자: 6월 1일)
        cls.ledger1 = Ledger.objects.create(
            user=cls.user_a,
            vendor_name="가게 A",
            vendor_registration_number="1234567890",
            transaction_date=datetime.datetime(2026, 6, 1, 14, 0, 0, tzinfo=datetime.UTC),
            total_amount=10000.00,
            supply_value=9090.91,
            vat_amount=909.09,
            category="식비",
        )

        # 거래 2: 2026-06-01 16:00:00 UTC -> 서울 시간: 2026-06-02 01:00:00 (로컬 일자: 6월 2일)
        cls.ledger2 = Ledger.objects.create(
            user=cls.user_a,
            vendor_name="가게 B",
            vendor_registration_number="0987654321",
            transaction_date=datetime.datetime(2026, 6, 1, 16, 0, 0, tzinfo=datetime.UTC),
            total_amount=20000.00,
            supply_value=18181.82,
            vat_amount=1818.18,
            category="쇼핑",
        )

        # 거래 3: 2026-06-02 14:00:00 UTC -> 서울 시간: 2026-06-02 23:00:00 (로컬 일자: 6월 2일)
        cls.ledger3 = Ledger.objects.create(
            user=cls.user_a,
            vendor_name="가게 C",
            vendor_registration_number="1111111111",
            transaction_date=datetime.datetime(2026, 6, 2, 14, 0, 0, tzinfo=datetime.UTC),
            total_amount=30000.00,
            supply_value=27272.73,
            vat_amount=2727.27,
            category="식비",
        )

        # 타 유저(B)의 가계부 데이터 생성 (집계에 섞이지 않아야 함)
        cls.ledger_b = Ledger.objects.create(
            user=cls.user_b,
            vendor_name="타 유저 가게",
            vendor_registration_number="2222222222",
            transaction_date=datetime.datetime(2026, 6, 1, 14, 0, 0, tzinfo=datetime.UTC),
            total_amount=50000.00,
            supply_value=45454.55,
            vat_amount=4545.45,
            category="식비",
        )

        cls.calendar_url = reverse("ledger-calendar")

    def test_calendar_summary_seoul_timezone(self):
        """Asia/Seoul 시간대 기준 로컬 일자별 합산 금액 및 건수가 정확히 집계되는지 확인합니다."""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.get(f"{self.calendar_url}?year=2026&month=6", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data["status"], "success")

        result = data["data"]
        self.assertEqual(result["year"], 2026)
        self.assertEqual(result["month"], 6)

        daily_summaries = result["daily_summaries"]

        # 6월 1일: 가게 A 건만 들어가므로 total_amount = 10000, count = 1
        self.assertIn("2026-06-01", daily_summaries)
        self.assertAlmostEqual(float(daily_summaries["2026-06-01"]["total_amount"]), 10000.00)
        self.assertEqual(daily_summaries["2026-06-01"]["count"], 1)

        # 6월 2일: 가게 B, 가게 C가 들어가므로 total_amount = 50000, count = 2
        self.assertIn("2026-06-02", daily_summaries)
        self.assertAlmostEqual(float(daily_summaries["2026-06-02"]["total_amount"]), 50000.00)
        self.assertEqual(daily_summaries["2026-06-02"]["count"], 2)

        # 월별 전체 합계액 검증 (10000 + 50000 = 60000)
        self.assertAlmostEqual(float(result["monthly_total"]), 60000.00)

    def test_calendar_summary_new_york_timezone(self):
        """America/New_York 시간대 기준 로컬 일자별 합산 금액 및 건수가 소급 집계되는지 확인합니다."""
        # user_a의 시간대를 America/New_York로 변경
        self.user_a.timezone = "America/New_York"
        self.user_a.save()

        # 뉴욕 시간대 오프셋 환산 (2026-06-01 은 서머타임이 적용되어 UTC-4 임)
        # 거래 1: 2026-06-01 14:00:00 UTC -> 뉴욕 2026-06-01 10:00:00 (로컬 일자: 6월 1일)
        # 거래 2: 2026-06-01 16:00:00 UTC -> 뉴욕 2026-06-01 12:00:00 (로컬 일자: 6월 1일)
        # 거래 3: 2026-06-02 14:00:00 UTC -> 뉴욕 2026-06-02 10:00:00 (로컬 일자: 6월 2일)
        # 따라서 뉴욕 기준: 6월 1일 = 30,000원(2건), 6월 2일 = 30,000원(1건)

        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.get(f"{self.calendar_url}?year=2026&month=6", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        daily_summaries = response.data["data"]["daily_summaries"]

        # 6월 1일: 가게 A + 가게 B (total_amount = 30000, count = 2)
        self.assertIn("2026-06-01", daily_summaries)
        self.assertAlmostEqual(float(daily_summaries["2026-06-01"]["total_amount"]), 30000.00)
        self.assertEqual(daily_summaries["2026-06-01"]["count"], 2)

        # 6월 2일: 가게 C (total_amount = 30000, count = 1)
        self.assertIn("2026-06-02", daily_summaries)
        self.assertAlmostEqual(float(daily_summaries["2026-06-02"]["total_amount"]), 30000.00)
        self.assertEqual(daily_summaries["2026-06-02"]["count"], 1)

    def test_calendar_summary_filtering(self):
        """카테고리 및 금액 필터 파라미터 적용 시 캘린더 요약 결과가 해당 내역으로만 필터링되는지 확인합니다."""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        # 카테고리가 '쇼핑'인 건만 필터링
        response = self.client.get(f"{self.calendar_url}?year=2026&month=6&categories=쇼핑", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        daily_summaries = response.data["data"]["daily_summaries"]
        # 쇼핑은 6월 2일(가게 B, 20000원)만 있으므로 6월 1일(가게 A, 식비)은 없어야 함
        self.assertNotIn("2026-06-01", daily_summaries)
        self.assertIn("2026-06-02", daily_summaries)
        self.assertAlmostEqual(float(daily_summaries["2026-06-02"]["total_amount"]), 20000.00)
        self.assertEqual(daily_summaries["2026-06-02"]["count"], 1)

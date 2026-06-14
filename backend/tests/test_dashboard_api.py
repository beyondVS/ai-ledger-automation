from datetime import date

from apps.accounts.models import User
from apps.ledgers.models import Ledger, MonthlyBudget
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient


class TestDashboardAndBudgetAPI(TestCase):
    """
    [T007, T015, T021] 대시보드 통계 API 및 예산 관리 API 연동 테스트
    - 헌법 VIII조 수호: django.test.TestCase 상속 및 setUpTestData 활용하여 DB 속도 최적화
    """

    @classmethod
    def setUpTestData(cls):
        # 1. 테스트용 사용자 생성
        cls.user = User.objects.create_user(
            username="dashboard_user",
            email="dashboard@example.com",
            password="testpassword123",
        )
        cls.other_user = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password="testpassword123",
        )

        # 2. 이번 달 가계부 데이터 적재
        # 카테고리별 분산: 식비 30만원, 교통비 10만원, 미분류 5만원
        # 가맹점: 스타벅스 강남점(15만원), 쿠팡(10만원), 카카오택시(5만원), 식비 가맹점A(15만원)
        now = timezone.now()

        # 식비 지출 1 (스타벅스 - 150,000원)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="1234567890",
            vendor_name="스타벅스 강남점",
            transaction_date=now,
            total_amount=150000,
            supply_value=136364,
            vat_amount=13636,
            category="식비",
        )
        # 식비 지출 2 (식비 가맹점A - 150,000원)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="9876543210",
            vendor_name="식비 가맹점A",
            transaction_date=now,
            total_amount=150000,
            supply_value=136364,
            vat_amount=13636,
            category="식비",
        )
        # 쇼핑/미분류 지출 (쿠팡 - 100,000원)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="1111111111",
            vendor_name="쿠팡",
            transaction_date=now,
            total_amount=100000,
            supply_value=90909,
            vat_amount=9091,
            category="미분류",
        )
        # 교통비 지출 (카카오택시 - 50,000원)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="2222222222",
            vendor_name="카카오택시",
            transaction_date=now,
            total_amount=50000,
            supply_value=45455,
            vat_amount=4545,
            category="교통비",
        )

        # 과거 월 지출 적재 (최근 3개월 흐름 테스트용)
        # 1개월 전 지출
        one_month_ago = now - timezone.timedelta(days=30)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="3333333333",
            vendor_name="과거 가맹점1",
            transaction_date=one_month_ago,
            total_amount=250000,
            supply_value=227273,
            vat_amount=22727,
            category="식비",
        )
        # 2개월 전 지출
        two_months_ago = now - timezone.timedelta(days=60)
        Ledger.objects.create(
            user=cls.user,
            vendor_registration_number="4444444444",
            vendor_name="과거 가맹점2",
            transaction_date=two_months_ago,
            total_amount=400000,
            supply_value=363636,
            vat_amount=36364,
            category="교통비",
        )

        # 3. 당월 예산 적재 (1,000,000원)
        budget_date = date(now.year, now.month, 1)
        cls.budget = MonthlyBudget.objects.create(
            user=cls.user,
            budget_month=budget_date,
            amount=1000000,
        )

        # URL 바인딩
        cls.dashboard_url = reverse("dashboard-statistics")
        cls.budget_url = reverse("monthly-budget-list")

    def setUp(self):
        self.client = APIClient()

    def test_dashboard_statistics_success(self):
        """
        [US1, US2, US3] 당월 가계부 및 예산 데이터를 포함한 통합 대시보드 API 반환 검증
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 1. 예산 게이지바 DTO 구조 검증 (spent_amount=45만원, spent_ratio=45%, status="safe")
        budget_data = response.data.get("budget")
        self.assertIsNotNone(budget_data)
        self.assertEqual(float(budget_data["amount"]), 1000000.0)
        self.assertEqual(float(budget_data["spent_amount"]), 450000.0)
        self.assertEqual(float(budget_data["remaining_amount"]), 550000.0)
        self.assertEqual(float(budget_data["spent_ratio"]), 45.0)
        self.assertEqual(budget_data["status"], "safe")

        # 2. 카테고리별 원형 차트 DTO 구조 검증 (식비 30만원(66.7%), 미분류 10만원(22.2%), 교통비 5만원(11.1%))
        category_data = response.data.get("category_spending")
        self.assertIsNotNone(category_data)
        self.assertEqual(len(category_data), 3)

        categories = {item["category_name"]: float(item["amount"]) for item in category_data}
        self.assertEqual(categories["식비"], 300000.0)
        self.assertEqual(categories["미분류"], 100000.0)
        self.assertEqual(categories["교통비"], 50000.0)

        # 3. TOP 3 가맹점 DTO 구조 검증 (금액 순 정렬: 스타벅스 강남점/식비 가맹점A 공동 1위(15만원) -> 쿠팡 3위(10만원))
        top_merchants = response.data.get("top_merchants")
        self.assertIsNotNone(top_merchants)
        self.assertEqual(len(top_merchants), 3)
        self.assertEqual(top_merchants[0]["merchant_name"], "스타벅스 강남점")
        self.assertEqual(float(top_merchants[0]["amount"]), 150000.0)
        self.assertEqual(top_merchants[2]["merchant_name"], "쿠팡")
        self.assertEqual(float(top_merchants[2]["amount"]), 100000.0)

    def test_dashboard_statistics_months_query(self):
        """
        [US1] 쿼리 파라미터(months) 변경 시 월별 지출 흐름 막대 차트 데이터 개수 검증
        """
        self.client.force_authenticate(user=self.user)

        # 1. 기본 3개월 조회
        response_3 = self.client.get(f"{self.dashboard_url}?months=3")
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)
        trends_3 = response_3.data.get("monthly_trends")
        self.assertEqual(len(trends_3), 3)

    def test_dashboard_statistics_no_data(self):
        """
        [US1] 지출 및 예산 데이터가 전혀 없는 사용자의 폴백 DTO 검증
        """
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 예산 폴백 검증 (Default: 1,000,000원, 지출 0원, 소진율 0%)
        budget_data = response.data.get("budget")
        self.assertEqual(float(budget_data["amount"]), 1000000.0)
        self.assertEqual(float(budget_data["spent_amount"]), 0.0)
        self.assertEqual(float(budget_data["spent_ratio"]), 0.0)
        self.assertEqual(budget_data["status"], "safe")

        # 차트 및 가맹점 폴백 (빈 리스트)
        self.assertEqual(len(response.data.get("category_spending")), 0)
        self.assertEqual(len(response.data.get("top_merchants")), 0)

    def test_budget_upsert_and_get(self):
        """
        [US2] 예산 설정 API(POST) 및 조회 API(GET) 검증
        """
        self.client.force_authenticate(user=self.user)

        # 1. 예산 수정 (기존 당월 예산 100만원 -> 150만원으로 Upsert)
        post_data = {"budget_month": "2026-06", "amount": 1500000}
        response_post = self.client.post(self.budget_url, post_data, format="json")
        self.assertEqual(response_post.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response_post.data["amount"]), 1500000.0)

        # 2. 예산 조회 검증
        response_get = self.client.get(f"{self.budget_url}?month=2026-06")
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response_get.data["amount"]), 1500000.0)

        # 3. 유효성 검사 에러 검증 (음수 금액 유입 시 400 Bad Request)
        bad_data = {"budget_month": "2026-06", "amount": -50000}
        response_bad = self.client.post(self.budget_url, bad_data, format="json")
        self.assertEqual(response_bad.status_code, status.HTTP_400_BAD_REQUEST)

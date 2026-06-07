import datetime

from apps.ledgers.models import Ledger, LedgerItem
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class ReceiptDetailViewTest(TestCase):
    """
    [T007, T015] ReceiptDetailView (PATCH, DELETE) 사용자 격리 및 유효성 검증 테스트
    """

    @classmethod
    def setUpTestData(cls):
        # 1. 테스트 유저 A, B 생성
        cls.user_a = User.objects.create_user(username="usera", email="usera@example.com", password="password123")
        cls.user_b = User.objects.create_user(username="userb", email="userb@example.com", password="password123")

        # 2. 유저 A의 가계부 데이터 및 하위 품목 생성
        cls.ledger_a = Ledger.objects.create(
            user=cls.user_a,
            vendor_name="원래 가맹점 A",
            vendor_registration_number="1234567890",
            transaction_date=datetime.date(2026, 6, 1),
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64,
            category="미분류",
        )
        cls.item_a1 = LedgerItem.objects.create(
            ledger=cls.ledger_a,
            item_name="커피",
            quantity=1,
            unit_price=5000.00,
            total_price=5000.00,
        )

        # 3. 유저 B의 가계부 데이터 생성
        cls.ledger_b = Ledger.objects.create(
            user=cls.user_b,
            vendor_name="가맹점 B",
            vendor_registration_number="0987654321",
            transaction_date=datetime.date(2026, 6, 2),
            total_amount=22000.00,
            supply_value=20000.00,
            vat_amount=2000.00,
            category="미분류",
        )

        # URL 매핑 (receipt-detail, kwargs={'pk': ...})
        cls.url_a = reverse("receipt-detail", kwargs={"pk": cls.ledger_a.id})
        cls.url_b = reverse("receipt-detail", kwargs={"pk": cls.ledger_b.id})

    # --- US1: PATCH API 테스트 ---
    def test_patch_ledger_success(self):
        """본인 소유 가계부를 유효한 값으로 정정 시 성공해야 합니다. (T007)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}
        payload = {
            "vendor_name": "수정된 가맹점",
            "transaction_date": "2026-06-05",
            "total_amount": 20000.00,
            "category": "식비",
        }

        # PATCH 요청
        response = self.client.patch(self.url_a, payload, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DB 갱신 확인
        self.ledger_a.refresh_from_db()
        self.assertEqual(self.ledger_a.vendor_name, "수정된 가맹점")
        self.assertEqual(str(self.ledger_a.transaction_date), "2026-06-05")
        self.assertEqual(self.ledger_a.total_amount, 20000.00)
        self.assertEqual(self.ledger_a.category, "식비")

        # 10% 자동 정합 보정값 검증 (T026 관련)
        # 20000.00의 10% 부가세 보정: supply_value 18181.82, vat_amount 1818.18
        self.assertAlmostEqual(float(self.ledger_a.supply_value), 18181.82, places=2)
        self.assertAlmostEqual(float(self.ledger_a.vat_amount), 1818.18, places=2)

    def test_patch_ledger_updates_merchant_template_category(self):
        """카테고리 정정 시 해당 가맹점의 MerchantTemplate default_category도 함께 자동 갱신되는지 검증 (T018 피드백 루프)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}
        payload = {"category": "문화/여가"}

        # 템플릿이 없는 상태에서 PATCH 요청
        from apps.ledgers.models import MerchantTemplate

        self.assertFalse(MerchantTemplate.objects.filter(vendor_registration_number="1234567890").exists())

        response = self.client.patch(self.url_a, payload, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 템플릿 자동 제안 등록 및 default_category 확인
        self.assertTrue(MerchantTemplate.objects.filter(vendor_registration_number="1234567890").exists())
        template = MerchantTemplate.objects.get(vendor_registration_number="1234567890")
        self.assertEqual(template.parsing_rules.get("default_category"), "문화/여가")
        self.assertFalse(template.is_verified)  # 헌법 III조에 의해 여전히 미승인(False) 상태여야 함

        # 템플릿이 이미 존재할 때 카테고리 재수정 시 덮어쓰기 검증
        payload2 = {"category": "식비"}
        response = self.client.patch(self.url_a, payload2, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        template.refresh_from_db()
        self.assertEqual(template.parsing_rules.get("default_category"), "식비")

    def test_patch_ledger_isolation(self):
        """타인의 가계부를 정정하려고 시도하면 404 Not Found 또는 403 Forbidden이 반환되어야 합니다. (T007)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}
        payload = {"vendor_name": "해킹된 가맹점"}

        response = self.client.patch(self.url_b, payload, content_type="application/json", **headers)
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # 유저 B 가계부 불변 확인
        self.ledger_b.refresh_from_db()
        self.assertEqual(self.ledger_b.vendor_name, "가맹점 B")

    def test_patch_ledger_validation_failed(self):
        """유효하지 않은 데이터(가맹점명 공백 등)로 수정 시 400 Bad Request가 반환되어야 합니다. (T007)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}
        payload = {"vendor_name": ""}  # 빈 가맹점명

        response = self.client.patch(self.url_a, payload, content_type="application/json", **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- US2: DELETE API 테스트 ---
    def test_delete_ledger_success(self):
        """본인 소유 가계부를 삭제하면 204 No Content와 함께 데이터베이스에서 CASCADE 제거되어야 합니다. (T015)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.delete(self.url_a, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Ledger 삭제 확인
        self.assertFalse(Ledger.objects.filter(id=self.ledger_a.id).exists())
        # LedgerItem CASCADE 연쇄 삭제 확인
        self.assertFalse(LedgerItem.objects.filter(id=self.item_a1.id).exists())

    def test_delete_ledger_isolation(self):
        """타인의 가계부를 삭제하려고 시도하면 404 Not Found 또는 403 Forbidden이 반환되어야 합니다. (T015)"""
        token = AccessToken.for_user(self.user_a)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(token)}"}

        response = self.client.delete(self.url_b, **headers)
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # 유저 B 가계부 보존 확인
        self.assertTrue(Ledger.objects.filter(id=self.ledger_b.id).exists())

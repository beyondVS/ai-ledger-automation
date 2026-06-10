from apps.accounts.models import User
from apps.ledgers.models import Ledger, LedgerItem
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class LedgerTransactionIntegrationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 헌법 VIII조 수호: setUpTestData 활용
        cls.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="securepassword123"
        )

    def setUp(self):
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)

    def test_ledger_item_save_failure_rolls_back_ledger(self):
        """
        T006: US1 - 품목 상세 저장 실패 시, 부모 Ledger까지 함께 롤백되는지 검증
        """
        url = reverse("ledger-ingest")
        payload = {
            "vendor_registration_number": "1234567890",
            "vendor_name": "맥도날드",
            "transaction_date": "2026-06-11",
            "total_amount": 15500.00,
            "supply_value": 14000.00,
            "vat_amount": 1500.00,
            "category": "식비",
            "items": [
                {"item_name": "정상 버거", "unit_price": 8500.00, "quantity": 1, "total_price": 8500.00},
                {
                    "item_name": "오류 품목",
                    "unit_price": 3500.00,
                    # 수량이 음수이거나 비정상 데이터인 오류 케이스
                    "quantity": -2,
                    "total_price": -7000.00,
                },
            ],
        }

        response = self.api_client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 롤백 검증: DB에 부모 Ledger 레코드와 자식 LedgerItem 레코드가 둘 다 없어야 함
        self.assertEqual(Ledger.objects.filter(user=self.user, vendor_registration_number="1234567890").count(), 0)
        self.assertEqual(LedgerItem.objects.count(), 0)

    def test_duplicate_payment_bypass_returns_200(self):
        """
        T006: US1 - 복합 고유 제약조건 충돌 시, 중복 생성을 우회하고 기존 id와 HTTP 200 반환 검증
        """
        url = reverse("ledger-ingest")
        payload = {
            "vendor_registration_number": "9876543210",
            "vendor_name": "스타벅스",
            "transaction_date": "2026-06-11",
            "total_amount": 5000.00,
            "supply_value": 4500.00,
            "vat_amount": 500.00,
            "category": "식비",
            "items": [{"item_name": "아메리카노", "unit_price": 5000.00, "quantity": 1, "total_price": 5000.00}],
        }

        # 1차 정상 적재
        response1 = self.api_client.post(url, payload, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        ledger_id = response1.data.get("ledger_id")
        self.assertIsNotNone(ledger_id)

        # 2차 중복 인입 시도
        response2 = self.api_client.post(url, payload, format="json")
        # 중복 시 200 OK 및 기존 ledger_id 반환
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data.get("ledger_id"), ledger_id)
        self.assertIn("duplicate", response2.data.get("message", "").lower())

        # 중복 레코드가 하나만 유일하게 존재하는지 검증
        self.assertEqual(Ledger.objects.filter(user=self.user, vendor_registration_number="9876543210").count(), 1)

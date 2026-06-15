from apps.ledgers.exceptions import DuplicatePaymentError
from apps.ledgers.models import Ledger
from apps.ledgers.services.payment import ingest_payment_data
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class LedgerDuplicateCheckTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="password123")
        cls.token = AccessToken.for_user(cls.user)
        cls.headers = {"HTTP_AUTHORIZATION": f"Bearer {str(cls.token)}"}

    def test_duplicate_check_by_raw_text_hash(self):
        # raw_text_hash가 100% 동일하면 중복 차단되는지 검증
        data1 = {
            "vendor_registration_number": "1234567890",
            "vendor_name": "스토어A",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 10000.00,
            "raw_text_hash": "hash12345",
            "items": [{"item_name": "상품1", "quantity": 1, "unit_price": 10000.00}],
        }
        ledger1 = ingest_payment_data(self.user, data1)
        self.assertIsNotNone(ledger1.id)
        self.assertEqual(ledger1.raw_text_hash, "hash12345")

        with self.assertRaises(DuplicatePaymentError):
            ingest_payment_data(self.user, data1)

    def test_duplicate_check_by_identifiers(self):
        # approval_number 혹은 order_id가 동일하면 중복 차단되는지 검증
        data1 = {
            "vendor_name": "스토어B",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 15000.00,
            "approval_number": "app_num_777",
            "order_id": "ord_id_999",
            "items": [{"item_name": "상품2", "quantity": 1, "unit_price": 15000.00}],
        }
        ledger1 = ingest_payment_data(self.user, data1)
        self.assertIsNotNone(ledger1.id)

        # 승인번호만 겹칠 때 차단
        data_dup_app = data1.copy()
        data_dup_app["order_id"] = "different_ord"
        with self.assertRaises(DuplicatePaymentError):
            ingest_payment_data(self.user, data_dup_app)

        # 주문 ID만 겹칠 때 차단
        data_dup_ord = data1.copy()
        data_dup_ord["approval_number"] = "different_app"
        with self.assertRaises(DuplicatePaymentError):
            ingest_payment_data(self.user, data_dup_ord)

    def test_allow_consecutive_payments(self):
        # 5분 내 동일 금액이라도 식별자/해시가 다르면 정상 연속 결제 처리
        data1 = {
            "vendor_name": "이니시스",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 11000.00,
            "approval_number": "app_1",
            "order_id": "ord_1",
            "items": [{"item_name": "아이템", "quantity": 1, "unit_price": 11000.00}],
        }
        data2 = {
            "vendor_name": "이니시스",
            "transaction_date": "2026-06-16T12:01:00Z",
            "total_amount": 11000.00,
            "approval_number": "app_2",
            "order_id": "ord_2",
            "items": [{"item_name": "아이템", "quantity": 1, "unit_price": 11000.00}],
        }
        ledger1 = ingest_payment_data(self.user, data1)
        ledger2 = ingest_payment_data(self.user, data2)
        self.assertNotEqual(ledger1.id, ledger2.id)
        self.assertEqual(Ledger.objects.filter(user=self.user, total_amount=11000.00).count(), 2)

    def test_duplicate_suspects_api(self):
        # 중복 의심 API (/api/ledgers/duplicate-suspects/) 가 5분 내 동일 금액 거래들을 쌍으로 묶어서 반환하는지 검증
        data1 = {
            "vendor_name": "배달의민족",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 15000.00,
            "approval_number": "app_3",
            "items": [{"item_name": "치킨", "quantity": 1, "unit_price": 15000.00}],
        }
        data2 = {
            "vendor_name": "에픽게임즈",
            "transaction_date": "2026-06-16T12:02:00Z",
            "total_amount": 15000.00,
            "order_id": "ord_4",
            "items": [{"item_name": "게임 재화", "quantity": 1, "unit_price": 15000.00}],
        }
        ingest_payment_data(self.user, data1)
        ingest_payment_data(self.user, data2)

        response = self.client.get(reverse("duplicate-suspects"), **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()["data"]
        self.assertEqual(len(res_data), 1)
        self.assertEqual(res_data[0]["ledger_1"]["vendor_name"], "배달의민족")
        self.assertEqual(res_data[0]["ledger_2"]["vendor_name"], "에픽게임즈")

    def test_ledger_merge_api(self):
        # 수동 병합 API (/api/ledgers/merge/) 기능 검증
        data1 = {
            "vendor_name": "이니시스(배달의민족)",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 15000.00,
            "approval_number": "app_5",
            "items": [{"item_name": "치킨", "quantity": 1, "unit_price": 15000.00}],
        }
        data2 = {
            "vendor_name": "배달의민족",
            "transaction_date": "2026-06-16T12:02:00Z",
            "total_amount": 15000.00,
            "order_id": "ord_6",
            "items": [{"item_name": "치킨", "quantity": 1, "unit_price": 15000.00}],
        }
        l1 = ingest_payment_data(self.user, data1)
        l2 = ingest_payment_data(self.user, data2)

        response = self.client.post(
            reverse("ledger-merge"),
            {"keep_ledger_id": str(l2.id), "delete_ledger_id": str(l1.id)},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(Ledger.objects.filter(id=l2.id).exists())
        self.assertFalse(Ledger.objects.filter(id=l1.id).exists())

        l2_refreshed = Ledger.objects.get(id=l2.id)
        self.assertEqual(l2_refreshed.approval_number, "app_5")
        self.assertEqual(l2_refreshed.order_id, "ord_6")

    def test_ledger_ignore_suspect_api(self):
        # 무시 API (/api/ledgers/ignore-suspect/) 기능 검증
        data1 = {
            "vendor_name": "스타벅스",
            "transaction_date": "2026-06-16T12:00:00Z",
            "total_amount": 5000.00,
            "items": [{"item_name": "커피", "quantity": 1, "unit_price": 5000.00}],
        }
        l1 = ingest_payment_data(self.user, data1)

        response = self.client.post(
            reverse("ledger-ignore-suspect"),
            {"ledger_ids": [str(l1.id)]},
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        l1_refreshed = Ledger.objects.get(id=l1.id)
        self.assertTrue(l1_refreshed.ignore_duplicate_check)

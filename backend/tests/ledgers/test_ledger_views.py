from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from apps.ledgers.models import Ledger
import datetime

User = get_user_model()

class LedgerListViewTest(TestCase):
    """
    [T021] 로그인된 유저의 데이터 격리 검증을 위한 가계부 리스트 뷰 테스트 (Django TestCase)
    """
    @classmethod
    def setUpTestData(cls):
        # 1. 테스트 유저 A, B 생성
        cls.user_a = User.objects.create_user(
            username='usera',
            email='usera@example.com',
            password='password123'
        )
        cls.user_b = User.objects.create_user(
            username='userb',
            email='userb@example.com',
            password='password123'
        )

        # 2. 유저 A의 가계부 데이터 생성
        cls.ledger_a = Ledger.objects.create(
            user=cls.user_a,
            vendor_name='유저 A의 상점',
            vendor_registration_number='1234567890',
            transaction_date=datetime.date(2026, 6, 1),
            total_amount=15000.00,
            supply_value=13636.36,
            vat_amount=1363.64
        )

        # 3. 유저 B의 가계부 데이터 생성
        cls.ledger_b = Ledger.objects.create(
            user=cls.user_b,
            vendor_name='유저 B의 상점',
            vendor_registration_number='0987654321',
            transaction_date=datetime.date(2026, 6, 2),
            total_amount=22000.00,
            supply_value=20000.00,
            vat_amount=2000.00
        )

        cls.list_url = reverse('ledger-list')

    def test_list_ledgers_isolation(self):
        """인증된 유저 A가 가계부를 조회할 때, 유저 B의 데이터는 격리 차단되고 본인(유저 A)의 데이터만 조회되는지 검증합니다."""
        # 유저 A에 대한 Access Token 발급
        token = AccessToken.for_user(self.user_a)
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {str(token)}'
        }

        response = self.client.get(self.list_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 반환 데이터 내에서 유저 A의 가계부만 확인
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['vendor_name'], '유저 A의 상점')
        # 유저 B의 데이터가 섞여있지 않은지 검증
        self.assertNotEqual(response.data[0]['vendor_name'], '유저 B의 상점')

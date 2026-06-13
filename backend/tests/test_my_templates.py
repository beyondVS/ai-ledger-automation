import pytest
from apps.accounts.models import User
from apps.ledgers.models import Ledger, MerchantTemplate
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestMyTemplateListView:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        # APIClient 직접 기동
        self.client = APIClient()

        # 1. 테스트용 사용자 생성
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="password123")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="password123")

        # 2. 테스트용 템플릿 생성
        self.template1 = MerchantTemplate.objects.create(
            vendor_registration_number="1111111111",
            vendor_name="Starbucks Shinchon",
            parsing_rules={"default_category": "카페/간식"},
            is_verified=True,
        )
        self.template2 = MerchantTemplate.objects.create(
            vendor_registration_number="2222222222",
            vendor_name="McDonalds",
            parsing_rules={"default_category": "식비"},
            is_verified=False,
        )
        self.template_dummy = MerchantTemplate.objects.create(
            vendor_registration_number="0000000000",
            vendor_name="간이영수증",
            parsing_rules={"default_category": "미분류"},
            is_verified=False,
        )

        # 3. User1의 가계부 내역 적재 (template1 가맹점 결제 발생, timezone-aware 적용)
        self.ledger1 = Ledger.objects.create(
            user=self.user1,
            vendor_registration_number="1111111111",
            vendor_name="Starbucks Shinchon",
            transaction_date=timezone.now(),
            total_amount=5000,
            supply_value=4545,
            vat_amount=455,
        )

        # 4. User1의 간이 영수증 결제 (0000000000, timezone-aware 적용)
        self.ledger_dummy = Ledger.objects.create(
            user=self.user1,
            vendor_registration_number="0000000000",
            vendor_name="간이영수증",
            transaction_date=timezone.now(),
            total_amount=1000,
            supply_value=909,
            vat_amount=91,
        )

        # URL 정의
        self.list_url = reverse("my-template-list")

    def test_my_template_list_success(self):
        """
        User1은 본인이 이용한 template1(1111111111)만 조회되고, dummy(0000000000) 및 template2는 제외되어야 합니다.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["vendor_registration_number"] == "1111111111"
        assert response.data[0]["vendor_name"] == "Starbucks Shinchon"

    def test_my_template_list_empty(self):
        """
        가계부 내역이 없는 User2는 조회 시 빈 목록을 반환해야 합니다.
        """
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_my_template_delete_success(self):
        """
        User1은 본인 가계부에 연동된 template1 가맹점 템플릿을 삭제할 수 있어야 합니다.
        """
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse("my-template-detail", kwargs={"template_id": self.template1.id})
        response = self.client.delete(detail_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not MerchantTemplate.objects.filter(id=self.template1.id).exists()

    def test_my_template_delete_forbidden(self):
        """
        User2는 본인 가계부에 연동되지 않은 template1을 삭제하려고 할 때 403 Forbidden 에러가 발생해야 합니다.
        """
        self.client.force_authenticate(user=self.user2)
        detail_url = reverse("my-template-detail", kwargs={"template_id": self.template1.id})
        response = self.client.delete(detail_url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert MerchantTemplate.objects.filter(id=self.template1.id).exists()

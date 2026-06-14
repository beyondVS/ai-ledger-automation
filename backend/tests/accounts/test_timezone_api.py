from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class UserTimezoneAPITestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 테스트 유저 생성
        cls.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword123", timezone="Asia/Seoul"
        )

    def setUp(self):
        self.client = APIClient()
        # JWT 인증 강제 바인딩
        self.client.force_authenticate(user=self.user)

    def test_patch_timezone_success(self):
        """유효한 타임존 변경 요청 시 200 OK 성공 응답 확인"""
        response = self.client.patch("/api/v1/accounts/timezone/", {"timezone": "America/New_York"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["data"]["timezone"], "America/New_York")

        # DB 갱신 검증
        self.user.refresh_from_db()
        self.assertEqual(self.user.timezone, "America/New_York")

    def test_patch_timezone_invalid(self):
        """무효한 타임존 명칭 요청 시 400 Bad Request 예외 응답 확인"""
        response = self.client.patch("/api/v1/accounts/timezone/", {"timezone": "Invalid/Timezone_Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["status"], "error")
        self.assertEqual(response.data["code"], "INVALID_TIMEZONE")

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

User = get_user_model()


class JWTTokenAuthenticationTest(TestCase):
    """
    [T020] 위조되거나 만료된 JWT 토큰으로 접근 시 401 Unauthorized 방어 테스트 (Django TestCase)
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="tokenauth", email="tokenauth@example.com", password="secure_password_999"
        )
        # 보안이 설정될 대상 가계부 URL 또는 임의의 보호 엔드포인트 지정
        cls.target_url = reverse("ledger-list")  # ledgers 앱의 목록 URL

    def test_request_without_token_unauthorized(self):
        """인증 헤더 없이 보안 API를 호출할 경우 401 Unauthorized로 거부되는지 검증합니다."""
        response = self.client.get(self.target_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_with_invalid_token_unauthorized(self):
        """위조되거나 변조된 토큰을 헤더에 동반하여 요청 시 401 Unauthorized로 차단되는지 검증합니다."""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid_token_xyz_12345"}
        response = self.client.get(self.target_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_with_expired_token_unauthorized(self):
        """만료된 토큰 규격으로 전달 시 401 Unauthorized로 차단되는지 검증합니다."""
        # 억지로 잘못 형식화된 만료 토큰 전달
        headers = {"HTTP_AUTHORIZATION": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjF9.invalid"}
        response = self.client.get(self.target_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

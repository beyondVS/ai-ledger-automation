from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

User = get_user_model()


class UserRegisterViewTest(TestCase):
    """
    [T008] 회원가입 API (/api/auth/register/) 검증 테스트 (Django TestCase 및 APIClient 활용)
    """

    @classmethod
    def setUpTestData(cls):
        # 중복 아이디 테스트용 유저 사전 등록
        cls.existing_username = "duplicateuser"
        cls.existing_user = User.objects.create_user(
            username=cls.existing_username, email="duplicate@example.com", password="old_secure_password_123"
        )
        cls.register_url = reverse("user-register")

    def test_register_success(self):
        """올바른 정보 입력 시 201 Created 응답과 함께 가입 유저의 메타데이터(username, email, provider 등)를 정상 반환하는지 검증합니다."""
        payload = {"username": "newregistrant", "email": "newregistrant@example.com", "password": "secure_password_999"}
        response = self.client.post(self.register_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["username"], payload["username"])
        self.assertEqual(response.data["email"], payload["email"])
        self.assertEqual(response.data["provider"], "local")
        self.assertIn("date_joined", response.data)

    def test_register_missing_fields(self):
        """필수 입력 필드(아이디 또는 비밀번호)가 유실된 불완전한 데이터 요청 유입 시 400 Bad Request를 반환하는지 검증합니다."""
        # 1. 패스워드 누락
        payload_no_pass = {"username": "nopass"}
        response = self.client.post(self.register_url, data=payload_no_pass, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. 아이디 누락
        payload_no_username = {"password": "somepassword123"}
        response = self.client.post(self.register_url, data=payload_no_username, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """이미 등록된 아이디로 가입을 제출했을 때 400 Bad Request 반환 및 중복 경고 메시지가 제공되는지 검증합니다."""
        payload = {"username": self.existing_username, "password": "fresh_password_abc"}
        response = self.client.post(self.register_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # DRF 기본 유효성 에러 구조 검증
        self.assertIn("username", response.data)


class UserLoginViewTest(TestCase):
    """
    [T014, T015] 로그인 및 로그아웃(토큰 블랙리스트) API 작동성 테스트 (Django TestCase)
    """

    @classmethod
    def setUpTestData(cls):
        cls.username = "loginuser"
        cls.email = "loginuser@example.com"
        cls.password = "secure_password_999"
        cls.user = User.objects.create_user(username=cls.username, email=cls.email, password=cls.password)
        cls.login_url = reverse("user-login")
        cls.logout_url = reverse("user-logout")

    def test_login_success(self):
        """올바른 계정 정보로 로그인 요청 시 200 OK와 함께 JWT 토큰(access, refresh)이 정상적으로 발급되는지 검증합니다."""
        payload = {"username": self.username, "password": self.password}
        response = self.client.post(self.login_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        """잘못된 비밀번호로 로그인 요청 시 401 Unauthorized를 반환하는지 검증합니다."""
        payload = {"username": self.username, "password": "wrong_password"}
        response = self.client.post(self.login_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklist_success(self):
        """로그아웃 요청 시, 수신된 리프레시 토큰이 블랙리스트 처리되어 만료 처리되는지 검증합니다."""
        # 1. 로그인하여 토큰 획득
        login_payload = {"username": self.username, "password": self.password}
        login_res = self.client.post(self.login_url, data=login_payload, content_type="application/json")
        refresh_token = login_res.data["refresh"]

        # 2. 리프레시 토큰을 실어 로그아웃 요청
        logout_payload = {"refresh": refresh_token}
        logout_res = self.client.post(self.logout_url, data=logout_payload, content_type="application/json")
        self.assertEqual(logout_res.status_code, status.HTTP_205_RESET_CONTENT)

    def test_token_refresh_success(self):
        """리프레시 토큰을 전송하여 새로운 Access Token을 정상적으로 갱신받는지 검증합니다."""
        # 1. 로그인하여 토큰 획득
        login_payload = {"username": self.username, "password": self.password}
        login_res = self.client.post(self.login_url, data=login_payload, content_type="application/json")
        refresh_token = login_res.data["refresh"]

        # 2. 리프레시 API 호출
        refresh_url = reverse("token-refresh")
        refresh_payload = {"refresh": refresh_token}
        refresh_res = self.client.post(refresh_url, data=refresh_payload, content_type="application/json")
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserModelTest(TestCase):
    """
    [T007] Custom User 모델의 비즈니스 규칙 및 스키마 검증 테스트 (Django TestCase 활용)
    """

    @classmethod
    def setUpTestData(cls):
        # 공통 테스트용 사용자 데이터 생성 (DB 오버헤드 최소화)
        cls.user_data = {
            "username": "existinguser",
            "email": "existinguser@example.com",
            "password": "secure_password_123",
        }
        cls.existing_user = User.objects.create_user(
            username=cls.user_data["username"], email=cls.user_data["email"], password=cls.user_data["password"]
        )

    def test_create_user_successful(self):
        """username과 패스워드로 정상적인 유저 생성이 성공하고, UUIDv7 및 기본 가입처가 매핑되는지 검증합니다."""
        user = User.objects.create_user(username="newuser", email="newuser@example.com", password="another_secure_pass")
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.provider, "local")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_username_uniqueness(self):
        """username 유일성(unique=True)에 따라 이미 가입된 username으로 재생성할 경우 IntegrityError가 나는지 검증합니다."""
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username=self.user_data["username"], email="different_email@example.com", password="different_password"
            )

    def test_password_is_hashed(self):
        """유저 가입 시 패스워드가 평문으로 저장되지 않고 해싱(PBKDF2 등)되어 안전하게 보존되는지 검증합니다."""
        user = User.objects.get(username=self.user_data["username"])
        self.assertNotEqual(user.password, self.user_data["password"])
        self.assertTrue(user.check_password(self.user_data["password"]))

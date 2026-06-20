from apps.accounts.models import UserPushSubscription
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class NotificationViewsTestCase(APITestCase):
    """
    [T013] 알림 관련 API 뷰 테스트 (DB 결합)
    - VAPID 공개키 조회 API
    - 구독 정보 등록, 목록 조회, 삭제(비활성화) API
    """

    @classmethod
    def setUpTestData(cls):
        # 테스트용 사용자 생성
        cls.user = User.objects.create_user(
            username="testuser_views", email="testuser_views@example.com", password="test_secure_password"
        )
        cls.other_user = User.objects.create_user(
            username="otheruser_views", email="otheruser_views@example.com", password="test_secure_password"
        )

    def setUp(self):
        # 기본 사용자 인증 처리
        self.client.force_authenticate(user=self.user)

    def test_get_vapid_public_key_unauthenticated(self):
        """VAPID 공개키 조회는 인증이 불필요해야 합니다."""
        self.client.force_authenticate(user=None)
        url = reverse("notifications:vapid-public-key")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("public_key", response.data)

    def test_create_push_subscription_success(self):
        """푸시 구독 정보를 성공적으로 등록할 수 있어야 합니다 (인증 필요)."""
        url = reverse("notifications:subscription-list")
        data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/mock_token_123",
            "keys": {"p256dh": "mock_p256dh_key_xyz", "auth": "mock_auth_secret_abc"},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["device_hint"], "FCM")
        self.assertTrue(response.data["is_active"])

        # DB 등록 확인
        self.assertTrue(UserPushSubscription.objects.filter(user=self.user, endpoint=data["endpoint"]).exists())

    def test_create_push_subscription_duplicate_updates_active(self):
        """동일한 엔드포인트로 중복 등록 시 기존 구독을 활성화(is_active=True)하고 200을 반환합니다."""
        # 기존에 비활성 구독 생성
        sub = UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/duplicate_token",
            p256dh="old_p256dh",
            auth="old_auth",
            is_active=False,
            device_hint="FCM",
        )

        url = reverse("notifications:subscription-list")
        data = {"endpoint": sub.endpoint, "keys": {"p256dh": "new_p256dh", "auth": "new_auth"}}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 상태 갱신 확인
        sub.refresh_from_db()
        self.assertTrue(sub.is_active)
        self.assertEqual(sub.p256dh, "new_p256dh")

    def test_list_push_subscriptions_excludes_secrets(self):
        """내 구독 목록 조회 시 p256dh, auth 등의 민감키는 제외되어야 합니다."""
        UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://web.push.apple.com/send/apple_token",
            p256dh="apple_p256dh",
            auth="apple_auth",
            device_hint="APPLE",
        )

        url = reverse("notifications:subscription-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn("p256dh", response.data[0])
        self.assertNotIn("auth", response.data[0])
        self.assertNotIn("endpoint", response.data[0])
        self.assertIn("device_hint", response.data[0])
        self.assertEqual(response.data[0]["device_hint"], "APPLE")

    def test_delete_push_subscription_success(self):
        """본인의 구독 정보를 성공적으로 삭제할 수 있어야 합니다."""
        sub = UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/delete_token",
            p256dh="del_p256dh",
            auth="del_auth",
        )

        url = reverse("notifications:subscription-detail", kwargs={"pk": sub.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Soft delete 또는 실제 delete 여부 확인 (DELETE 요건은 REST API 상 204 반환 후 삭제되거나 비활성화)
        # contracts에서는 "구독 비활성화"로 명시됨.
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_delete_push_subscription_forbidden_for_other_user(self):
        """타인의 구독 정보를 삭제하려 하면 403 또는 404를 반환해야 합니다."""
        sub = UserPushSubscription.objects.create(
            user=self.other_user,
            endpoint="https://fcm.googleapis.com/fcm/send/other_token",
            p256dh="other_p256dh",
            auth="other_auth",
        )

        url = reverse("notifications:subscription-detail", kwargs={"pk": sub.id})
        response = self.client.delete(url)
        # DRF IsOwnerPermission 등을 적용하면 403, get_object_or_404 처리 시 404
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

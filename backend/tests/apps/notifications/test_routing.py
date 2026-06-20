from unittest.mock import MagicMock, patch

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.sender import detect_push_channel
from apps.notifications.tasks import send_push_notification_task
from django.test import TestCase


class PushRoutingTestCase(TestCase):
    """
    [T026] 이중 채널 라우팅 및 채널 식별 기능 정밀 검증 테스트
    - 헌법 VIII조 준수: TestCase 상속 및 setUpTestData 활용
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="routing_user", email="routing_user@example.com", password="routing_secure_password"
        )

        # 1. FCM 구독
        cls.sub_fcm = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token_fcm",
            p256dh="p256dh_fcm_dummy_value_base64_enough_length_xyz_123",
            auth="auth_fcm_dummy_xyz",
            device_hint="Android Phone",
        )

        # 2. Apple VAPID 구독
        cls.sub_apple = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://web.push.apple.com/send/token_apple",
            p256dh="p256dh_apple_dummy_value_base64_enough_length_xyz_123",
            auth="auth_apple_dummy_xyz",
            device_hint="iOS iPhone",
        )

        # 3. Generic VAPID 구독
        cls.sub_generic = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://updates.push.services.mozilla.com/push/token_firefox",
            p256dh="p256dh_firefox_dummy_value_base64_enough_length_xyz_123",
            auth="auth_firefox_dummy_xyz",
            device_hint="Firefox PC",
        )

    def test_detect_push_channel_routing(self):
        """[T026] 엔드포인트 도메인 분석을 통해 채널(FCM, APPLE_VAPID, GENERIC_VAPID)이 정확히 검출되는지 검증"""
        self.assertEqual(detect_push_channel(self.sub_fcm.endpoint), "FCM")
        self.assertEqual(detect_push_channel(self.sub_apple.endpoint), "APPLE_VAPID")
        self.assertEqual(detect_push_channel(self.sub_generic.endpoint), "GENERIC_VAPID")

    @patch("apps.notifications.sender.webpush")
    def test_send_web_push_saves_correct_channel_in_log(self, mock_webpush):
        """[T027] 푸시 알림 전송 태스크 기동 시, 채널 구분을 정확히 분석하여 NotificationLog 레코드에 반영하는지 검증"""
        # pywebpush.webpush가 HTTP 201 Created 응답을 주는 것으로 모킹
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = "Created"
        mock_webpush.return_value = mock_response

        # 1. FCM 채널 로그 검증
        task_fcm = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub_fcm,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="TEST_ROUTING:FCM:1",
            title="FCM 제목",
            body="본문",
            status="PENDING",
        )
        send_push_notification_task(str(task_fcm.id))

        log_fcm = NotificationLog.objects.filter(task=task_fcm).first()
        self.assertIsNotNone(log_fcm)
        self.assertEqual(log_fcm.channel, "FCM")
        self.assertTrue(log_fcm.is_success)

        # 2. Apple VAPID 채널 로그 검증
        task_apple = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub_apple,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="TEST_ROUTING:APPLE:1",
            title="Apple 제목",
            body="본문",
            status="PENDING",
        )
        send_push_notification_task(str(task_apple.id))

        log_apple = NotificationLog.objects.filter(task=task_apple).first()
        self.assertIsNotNone(log_apple)
        self.assertEqual(log_apple.channel, "APPLE_VAPID")
        self.assertTrue(log_apple.is_success)

        # 3. Generic VAPID 채널 로그 검증
        task_generic = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub_generic,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="TEST_ROUTING:GENERIC:1",
            title="Generic 제목",
            body="본문",
            status="PENDING",
        )
        send_push_notification_task(str(task_generic.id))

        log_generic = NotificationLog.objects.filter(task=task_generic).first()
        self.assertIsNotNone(log_generic)
        self.assertEqual(log_generic.channel, "GENERIC_VAPID")
        self.assertTrue(log_generic.is_success)

from datetime import timedelta

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.tasks import cleanup_old_notification_logs
from django.test import TestCase
from django.utils import timezone


class NotificationCleanupTestCase(TestCase):
    """
    [T030] 30일이 경과한 NotificationLog 레코드 자동 정리 기능 검증 테스트
    - 헌법 VIII조 준수: TestCase 상속 및 setUpTestData 활용
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="cleanup_user", email="cleanup_user@example.com", password="cleanup_secure_password"
        )

        cls.sub = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token_cleanup",
            p256dh="p256dh_dummy",
            auth="auth_dummy",
        )

        cls.task = NotificationTask.objects.create(
            user=cls.user,
            subscription=cls.sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="CLEANUP_TEST:1",
            title="테스트",
            body="내용",
            status="SUCCESS",
        )

    def test_cleanup_old_notification_logs(self):
        """[T030] cleanup_old_notification_logs 태스크가 30일 이상 경과한 로그만 정확히 퍼지 처리하는지 검증"""
        now = timezone.now()

        # 1. 35일 전 로그 생성 (지워져야 함)
        old_log = NotificationLog.objects.create(
            task=self.task, user=self.user, channel="FCM", endpoint_hint=self.sub.endpoint[:255], is_success=True
        )
        NotificationLog.objects.filter(id=old_log.id).update(created_at=now - timedelta(days=35))

        # 2. 10일 전 로그 생성 (유지되어야 함)
        recent_log = NotificationLog.objects.create(
            task=self.task, user=self.user, channel="FCM", endpoint_hint=self.sub.endpoint[:255], is_success=True
        )
        NotificationLog.objects.filter(id=recent_log.id).update(created_at=now - timedelta(days=10))

        # 3. 정리 태스크 실행
        msg = cleanup_old_notification_logs()
        self.assertIn("Cleaned up 1 old notification logs", msg)

        # 4. 결과 검증
        self.assertFalse(NotificationLog.objects.filter(id=old_log.id).exists())
        self.assertTrue(NotificationLog.objects.filter(id=recent_log.id).exists())

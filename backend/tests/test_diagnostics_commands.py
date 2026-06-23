from io import StringIO
from unittest.mock import patch

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class TestDiagnosticsCommands(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 헌법 제VIII조 하이브리드 테스트 작성 규약 준수: setUpTestData를 통한 DB 오버헤드 최적화
        cls.user = User.objects.create_user(username="testadmin", password="password123")
        cls.sub = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/testToken",
            p256dh="p256dh_key",
            auth="auth_token",
            is_active=True,
        )

    @patch("apps.notifications.management.commands.trigger_test_push.send_web_push")
    def test_trigger_test_push_success(self, mock_send_push):
        """정상적으로 테스트 푸시를 즉시(동기) 전송하고 결과를 로그에 남기는 커맨드 성공 케이스 검증"""
        mock_send_push.return_value = {
            "is_success": True,
            "channel": "FCM",
            "http_status_code": 200,
            "response_body": "OK",
        }

        out = StringIO()
        call_command("trigger_test_push", username="testadmin", stdout=out)

        # command output 검증
        output = out.getvalue()
        self.assertIn("Successfully triggered test push", output)
        self.assertIn("testadmin", output)

        # 즉시 발송(동기)이므로 Celery를 통하지 않고 즉시 NotificationLog와 NotificationTask가 생성되어야 함
        task = NotificationTask.objects.filter(user=self.user, event_type="TEST_PUSH").first()
        self.assertIsNotNone(task)
        self.assertEqual(task.status, "SUCCESS")

        log = NotificationLog.objects.filter(task=task).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.is_success)
        self.assertEqual(log.status, "SENT")

    def test_trigger_test_push_no_user(self):
        """존재하지 않는 유저명 입력 시 CommandError가 발생하는지 검증"""
        with self.assertRaises(CommandError):
            call_command("trigger_test_push", username="nonexistentuser")

    def test_trigger_test_push_no_subscriptions(self):
        """구독이 없는 유저에 대해 커맨드 실행 시 적절히 처리되거나 예외가 발생하는지 검증"""
        User.objects.create_user(username="nosubuser", password="password123")
        out = StringIO()
        call_command("trigger_test_push", username="nosubuser", stdout=out)
        self.assertIn("No active subscriptions", out.getvalue())

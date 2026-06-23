from datetime import timedelta
from unittest.mock import patch

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.tasks import (
    cleanup_old_notification_logs,
    dispatch_user_notifications_task,
    send_push_notification_task,
)
from django.test import TestCase
from django.utils import timezone


class TestNotificationsTasks(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="taskuser", password="password123")
        cls.sub = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/taskToken",
            p256dh="p256dh_key",
            auth="auth_token",
            is_active=True,
        )

    @patch("apps.notifications.tasks.send_web_push")
    def test_send_push_notification_success(self, mock_send_push):
        """푸시 알림 전송 성공 시 상태 변경 및 로그 기록 테스트"""
        mock_send_push.return_value = {
            "is_success": True,
            "channel": "FCM",
            "http_status_code": 200,
            "response_body": "OK",
        }

        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="key_success",
            title="Success Title",
            body="Success Body",
        )

        result = send_push_notification_task(str(task.id))
        self.assertEqual(result["status"], "SUCCESS")

        task.refresh_from_db()
        self.assertEqual(task.status, "SUCCESS")

        # 감사 로그 기록 검증
        log = NotificationLog.objects.get(task=task)
        self.assertTrue(log.is_success)
        self.assertEqual(log.status, "SENT")
        self.assertEqual(log.http_status_code, 200)

    @patch("apps.notifications.tasks.send_web_push")
    def test_send_push_notification_gone_disables_subscription(self, mock_send_push):
        """410 Gone 수신 시 구독 비활성화 및 태스크 실패 처리 검증 (FR-006 수호)"""
        mock_send_push.return_value = {
            "is_success": False,
            "channel": "FCM",
            "http_status_code": 410,
            "response_body": "Gone",
        }

        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="key_gone",
            title="Gone Title",
            body="Gone Body",
        )

        result = send_push_notification_task(str(task.id))
        self.assertEqual(result["status"], "FAILED")

        # 구독 비활성화 확인
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.is_active)

        # 태스크 실패 확인
        task.refresh_from_db()
        self.assertEqual(task.status, "FAILED")

        # 로그 기록 검증
        log = NotificationLog.objects.get(task=task)
        self.assertFalse(log.is_success)
        self.assertEqual(log.status, "FAILED")
        self.assertEqual(log.http_status_code, 410)

    @patch("apps.notifications.tasks.send_push_notification_task.retry")
    @patch("apps.notifications.tasks.send_web_push")
    def test_send_push_notification_retry_on_temporary_failure(self, mock_send_push, mock_retry):
        """일시적인 네트워크 장애(500) 시 Celery 재시도 수행 검증"""
        mock_send_push.return_value = {
            "is_success": False,
            "channel": "FCM",
            "http_status_code": 500,
            "response_body": "Internal Server Error",
        }

        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="key_retry",
            title="Retry Title",
            body="Retry Body",
        )

        send_push_notification_task(str(task.id))
        # Celery retry가 호출되었는지 확인
        mock_retry.assert_called_once()

    @patch("apps.notifications.tasks.send_web_push")
    def test_dispatch_notifications_blocks_duplicate_within_60s(self, mock_send_push):
        """60초 시간 윈도우 기반 연속 결제/알림 중복 차단 검증 (DB 멱등성 수호)"""
        mock_send_push.return_value = {
            "is_success": True,
            "channel": "FCM",
            "http_status_code": 200,
            "response_body": "OK",
        }
        # 첫 번째 배포
        payload = {"title": "Receipt", "body": "10000"}
        result1 = dispatch_user_notifications_task(
            user_id=str(self.user.id),
            event_type="RECEIPT_PROCESSED",
            payload=payload,
            idempotency_key="receipt_id_123",
        )
        self.assertEqual(result1["status"], "DISPATCHED")

        # 60초 이내 동일 idempotency_key 재배포 요청 -> 차단 확인
        result2 = dispatch_user_notifications_task(
            user_id=str(self.user.id),
            event_type="RECEIPT_PROCESSED",
            payload=payload,
            idempotency_key="receipt_id_123",
        )
        self.assertEqual(result2["status"], "IGNORED")
        self.assertEqual(result2["reason"], "DB 60s window duplicate")

    @patch("apps.notifications.tasks.send_web_push")
    def test_dispatch_notifications_allows_different_budget_thresholds(self, mock_send_push):
        """예산 경보(80% 및 100%)는 동일월/동일 순간 발생 시 중복 필터를 우회하여 전송 가능한지 검증"""
        mock_send_push.return_value = {
            "is_success": True,
            "channel": "FCM",
            "http_status_code": 200,
            "response_body": "OK",
        }
        payload_80 = {"title": "예산 80% 초과", "body": "주의 요망"}
        payload_100 = {"title": "예산 100% 초과", "body": "한도 초과"}

        # 80% 알림 발송
        result_80 = dispatch_user_notifications_task(
            user_id=str(self.user.id),
            event_type="BUDGET_THRESHOLD_ALERT",
            payload=payload_80,
            idempotency_key="budget_202606_80",
        )
        self.assertEqual(result_80["status"], "DISPATCHED")

        # 동일 유저, 동일 이벤트 타입이지만 threshold가 다름 (idempotency_key가 구별됨)
        result_100 = dispatch_user_notifications_task(
            user_id=str(self.user.id),
            event_type="BUDGET_THRESHOLD_ALERT",
            payload=payload_100,
            idempotency_key="budget_202606_100",
        )
        self.assertEqual(result_100["status"], "DISPATCHED")

    def test_cleanup_old_notification_logs(self):
        """30일 경과 로그의 정기적 퍼지 처리 기능 검증"""
        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="cleanup_key",
            title="Title",
            body="Body",
        )

        # 1. 35일 전 로그 생성 및 강제 날짜 갱신
        log_old = NotificationLog.objects.create(
            task=task,
            user=self.user,
            channel="FCM",
            endpoint_hint=self.sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )
        NotificationLog.objects.filter(id=log_old.id).update(created_at=timezone.now() - timedelta(days=35))

        # 2. 방금 생성된 로그
        log_new = NotificationLog.objects.create(
            task=task,
            user=self.user,
            channel="FCM",
            endpoint_hint=self.sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )

        # 퍼지 작업 구동
        cleanup_old_notification_logs()

        # 35일 전 로그는 삭제되고, 최신 로그는 보존되어야 함
        self.assertFalse(NotificationLog.objects.filter(id=log_old.id).exists())
        self.assertTrue(NotificationLog.objects.filter(id=log_new.id).exists())

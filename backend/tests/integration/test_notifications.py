from unittest.mock import patch

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from django.test import TestCase

"""
Notification Task integration test (TDD Failure Baseline)
- Tests Celery async task dispatch behavior
- Validates NotificationLog status transition to 'SENT' or 'FAILED'
"""


class NotificationIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 헌법 VIII조 준수: setUpTestData를 통한 공통 데이터베이스 셋업
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        cls.subscription = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/mock-token",
            p256dh="mock-p256dh",
            auth="mock-auth",
        )
        cls.task = NotificationTask.objects.create(
            user=cls.user,
            subscription=cls.subscription,
            event_type="BUDGET_THRESHOLD_ALERT",
            idempotency_key="unique-idemp-123",
            title="예산 초과 알림",
            body="당월 예산 임계치 80%가 초과되었습니다.",
        )

    @patch("apps.notifications.sender.webpush")
    def test_celery_task_sends_push_and_creates_sent_log(self, mock_webpush):
        # pywebpush가 호출되어 성공 코드를 반환하는 시나리오 모킹
        mock_webpush.return_value.status_code = 201
        mock_webpush.return_value.text = '{"success": true}'

        # Celery 태스크를 직접 가져와서 동기적으로 실행
        from apps.notifications.tasks import send_push_notification_task

        # 태스크 실행
        send_push_notification_task(self.task.id)

        # 발송 완료 이력 확인
        log = NotificationLog.objects.filter(task=self.task).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.is_success)
        self.assertEqual(log.status, "SENT")
        self.assertEqual(log.http_status_code, 201)

    def test_acknowledgement_api_success(self):
        # 1. 테스트용 로그 생성
        log = NotificationLog.objects.create(
            task=self.task,
            user=self.user,
            channel="GENERIC_VAPID",
            endpoint_hint=self.subscription.endpoint[:50],
            is_success=True,
            status="SENT",
        )

        # 2. 인증 설정 및 수신 완료(DELIVERED) 요청
        self.client.force_login(self.user)
        url = f"/api/v1/notifications/{log.id}/acknowledge/"
        payload = {"status": "DELIVERED", "delivered_at": "2026-06-21T01:20:00Z"}

        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["id"], str(log.id))
        self.assertEqual(data["status"], "DELIVERED")

        # 3. DB 갱신 여부 최종 검증
        log.refresh_from_db()
        self.assertEqual(log.status, "DELIVERED")

    def test_acknowledgement_api_invalid_status(self):
        log = NotificationLog.objects.create(
            task=self.task,
            user=self.user,
            channel="GENERIC_VAPID",
            endpoint_hint=self.subscription.endpoint[:50],
            is_success=True,
            status="SENT",
        )
        self.client.force_login(self.user)
        url = f"/api/v1/notifications/{log.id}/acknowledge/"
        payload = {
            "status": "READ",  # 유효하지 않은 상태 값
            "delivered_at": "2026-06-21T01:20:00Z",
        }

        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_acknowledgement_api_not_found(self):
        self.client.force_login(self.user)
        import uuid

        url = f"/api/v1/notifications/{uuid.uuid4()}/acknowledge/"
        payload = {"status": "DELIVERED", "delivered_at": "2026-06-21T01:20:00Z"}

        response = self.client.post(url, payload, content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_sync_api_success(self):
        # 1. 알림 로그 생성
        log = NotificationLog.objects.create(
            task=self.task,
            user=self.user,
            channel="GENERIC_VAPID",
            endpoint_hint=self.subscription.endpoint[:50],
            is_success=True,
            status="SENT",
        )

        # 2. 동기화 요청
        self.client.force_login(self.user)
        url = "/api/v1/notifications/sync/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("synced_at", data)
        self.assertIn("notifications", data)

        # 3. 델타 배열 속성 매칭 대조
        notifications = data["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], str(log.id))
        self.assertEqual(notifications[0]["title"], self.task.title)
        self.assertEqual(notifications[0]["body"], self.task.body)
        self.assertEqual(notifications[0]["status"], "SENT")

    def test_sync_api_with_last_synced_at(self):
        import datetime

        from django.utils import timezone

        # 1. 과거 로그 생성
        past_time = timezone.now() - datetime.timedelta(hours=2)
        past_log = NotificationLog.objects.create(
            task=self.task,
            user=self.user,
            channel="GENERIC_VAPID",
            endpoint_hint=self.subscription.endpoint[:50],
            is_success=True,
            status="SENT",
        )
        NotificationLog.objects.filter(id=past_log.id).update(created_at=past_time)

        # 2. 신규 로그 생성 (현재 시간)
        new_log = NotificationLog.objects.create(
            task=self.task,
            user=self.user,
            channel="GENERIC_VAPID",
            endpoint_hint=self.subscription.endpoint[:50],
            is_success=True,
            status="SENT",
        )

        # 3. past_time 과 new_log 생성 시각 사이를 동기화 기준으로 호출
        self.client.force_login(self.user)
        sync_cutoff = timezone.now() - datetime.timedelta(hours=1)

        import urllib.parse

        encoded_cutoff = urllib.parse.quote(sync_cutoff.isoformat())
        url = f"/api/v1/notifications/sync/?last_synced_at={encoded_cutoff}"

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        notifications = data["notifications"]

        # 4. sync_cutoff 이후에 생성된 new_log만 반환되어야 함
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], str(new_log.id))

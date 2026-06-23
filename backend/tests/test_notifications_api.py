from datetime import timedelta

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


class TestNotificationsAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # 헌법 제VIII조 하이브리드 테스트 작성 규약 준수: setUpTestData를 통한 DB 오버헤드 최적화
        cls.user = User.objects.create_user(username="testuser", password="testpassword123")
        cls.other_user = User.objects.create_user(username="otheruser", password="testpassword123")

    def setUp(self):
        # API 테스트 시 매번 인증 처리
        self.client.login(username="testuser", password="testpassword123")

    def test_vapid_public_key_view(self):
        """VAPID 공개키 조회 API 테스트"""
        url = reverse("notifications:vapid-public-key")
        # 인증 없이 호출 허용 여부 체크 (AllowAny)
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("public_key", response.data)

    def test_subscribe_and_upsert_subscription(self):
        """구독 등록 및 중복 시 Upsert 동작 테스트"""
        url = reverse("notifications:subscription-list")
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/token123",
            "keys": {
                "p256dh": "p256dh_key_data",
                "auth": "auth_token_data",
            },
        }

        # 1. 최초 등록 (201 Created)
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserPushSubscription.objects.filter(user=self.user).count(), 1)

        # 2. 동일 endpoint 재등록 시 Upsert 확인 (200 OK)
        payload["keys"]["p256dh"] = "updated_p256dh_key"
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 레코드 수는 여전히 1개여야 함 (멱등성 보장)
        self.assertEqual(UserPushSubscription.objects.filter(user=self.user).count(), 1)
        sub = UserPushSubscription.objects.get(user=self.user)
        self.assertEqual(sub.p256dh, "updated_p256dh_key")

    def test_unsubscribe_deactivates_subscription(self):
        """구독 해제(DELETE) 시 물리 삭제가 아닌 is_active=False 비활성화 검증"""
        sub = UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token456",
            p256dh="key",
            auth="auth",
            is_active=True,
        )

        url = reverse("notifications:subscription-detail", kwargs={"pk": sub.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # DB에 레코드는 남아있고 is_active만 False여야 함
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_acknowledge_notification(self):
        """웹 푸시 수신 확인(ACK) 시 DELIVERED 상태 갱신 테스트"""
        sub = UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token789",
            p256dh="key",
            auth="auth",
        )
        task = NotificationTask.objects.create(
            user=self.user,
            subscription=sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="key_1",
            title="Title",
            body="Body",
        )
        log = NotificationLog.objects.create(
            task=task,
            user=self.user,
            channel="FCM",
            endpoint_hint=sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )

        url = reverse("notifications:acknowledge", kwargs={"id": log.id})
        payload = {"status": "DELIVERED"}

        # 1. 정상 업데이트
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log.refresh_from_db()
        self.assertEqual(log.status, "DELIVERED")

        # 2. 잘못된 상태 전송 시 400 Bad Request
        payload = {"status": "FAILED"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_acknowledge_other_user_log_fails(self):
        """타인의 알림 로그에 대해 ACK 호출 시 404 반환 검증"""
        sub = UserPushSubscription.objects.create(
            user=self.other_user,
            endpoint="https://fcm.googleapis.com/fcm/send/tokenOther",
            p256dh="key",
            auth="auth",
        )
        task = NotificationTask.objects.create(
            user=self.other_user,
            subscription=sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="key_other",
            title="Title",
            body="Body",
        )
        log = NotificationLog.objects.create(
            task=task,
            user=self.other_user,
            channel="FCM",
            endpoint_hint=sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )

        url = reverse("notifications:acknowledge", kwargs={"id": log.id})
        response = self.client.post(url, {"status": "DELIVERED"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_sync_delta(self):
        """알림 동기화 API의 델타 조회(last_synced_at 기준) 검증"""
        sub = UserPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/tokenSync",
            p256dh="key",
            auth="auth",
        )
        task1 = NotificationTask.objects.create(
            user=self.user,
            subscription=sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="sync_key_1",
            title="Old Title",
            body="Old Body",
        )
        task2 = NotificationTask.objects.create(
            user=self.user,
            subscription=sub,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="sync_key_2",
            title="New Title",
            body="New Body",
        )

        # 과거 로그 (35일 전)
        log_old = NotificationLog.objects.create(
            task=task1,
            user=self.user,
            channel="FCM",
            endpoint_hint=sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )
        NotificationLog.objects.filter(id=log_old.id).update(created_at=timezone.now() - timedelta(days=35))

        # 신규 로그 (방금 전)
        log_new = NotificationLog.objects.create(
            task=task2,
            user=self.user,
            channel="FCM",
            endpoint_hint=sub.endpoint[:255],
            is_success=True,
            status="SENT",
        )

        url = reverse("notifications:sync")

        # 1. last_synced_at 파라미터가 없을 때: 30일 이내 알림만 반환 (log_new만 반환)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notifications = response.data["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["id"], str(log_new.id))

        # 2. last_synced_at이 log_new 직전으로 주어졌을 때: log_new 반환
        sync_time = (timezone.now() - timedelta(seconds=10)).isoformat()
        response = self.client.get(url, {"last_synced_at": sync_time})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["notifications"]), 1)

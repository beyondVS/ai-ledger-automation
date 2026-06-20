from unittest.mock import MagicMock, patch

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.services import (
    enqueue_receipt_notification,
    is_duplicate_notification,
)
from apps.notifications.tasks import (
    dispatch_user_notifications_task,
    send_push_notification_task,
)
from django.test import TestCase
from django.utils import timezone


class NotificationTasksTestCase(TestCase):
    """
    [T021] 알림 Celery 태스크 및 멱등성 이중 방어 테스트 (DB 결합)
    - 헌법 VIII조 준수: TestCase 상속 및 setUpTestData 활용
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="testuser_tasks", email="testuser_tasks@example.com", password="test_secure_password"
        )
        # 활성 구독 2개 생성 (복수 기기 병렬 발송 테스트용)
        cls.sub1 = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token_device_1",
            p256dh="p256dh_1",
            auth="auth_1",
            device_hint="FCM",
        )
        cls.sub2 = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://web.push.apple.com/send/token_device_2",
            p256dh="p256dh_2",
            auth="auth_2",
            device_hint="APPLE",
        )
        # 비활성 구독 1개 생성 (발송 대상 제외 테스트용)
        cls.sub_inactive = UserPushSubscription.objects.create(
            user=cls.user,
            endpoint="https://fcm.googleapis.com/fcm/send/token_inactive",
            p256dh="p256dh_in",
            auth="auth_in",
            is_active=False,
            device_hint="FCM",
        )

    @patch("apps.notifications.tasks.send_web_push")
    def test_send_push_notification_task_success(self, mock_send_push):
        """정상적인 VAPID 발송 성공 시 Task 상태가 SUCCESS로 갱신되고 로그가 생성되는지 검증"""
        # NotificationTask 생성
        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub1,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="RECEIPT_PROCESSED:test_success",
            title="결제 완료",
            body="테스트 본문",
            status="PENDING",
        )

        mock_send_push.return_value = {
            "is_success": True,
            "channel": "FCM",
            "http_status_code": 201,
            "response_body": "Created",
        }

        # 태스크 직접 호출
        result = send_push_notification_task(task.id)

        self.assertEqual(result["status"], "SUCCESS")

        # Task 상태 갱신 검증
        task.refresh_from_db()
        self.assertEqual(task.status, "SUCCESS")

        # Log 생성 검증
        self.assertTrue(NotificationLog.objects.filter(task=task, is_success=True).exists())
        log = NotificationLog.objects.get(task=task)
        self.assertEqual(log.http_status_code, 201)
        self.assertEqual(log.channel, "FCM")

    @patch("apps.notifications.tasks.send_web_push")
    def test_send_push_notification_task_failure_gone(self, mock_send_push):
        """발송 결과가 410 Gone(구독 만료)인 경우 구독이 비활성화되는지 검증"""
        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub2,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="RECEIPT_PROCESSED:test_gone",
            title="결제 완료",
            body="테스트 본문",
            status="PENDING",
        )

        mock_send_push.return_value = {
            "is_success": False,
            "channel": "APPLE_VAPID",
            "http_status_code": 410,
            "response_body": "Subscription Gone",
        }

        result = send_push_notification_task(task.id)

        self.assertEqual(result["status"], "FAILED")

        # 구독 비활성화 확인
        self.sub2.refresh_from_db()
        self.assertFalse(self.sub2.is_active)

        # 로그 생성 검증
        self.assertTrue(NotificationLog.objects.filter(task=task, is_success=False).exists())

    @patch("apps.notifications.tasks.send_push_notification_task.apply_async")
    def test_dispatch_user_notifications_task_dispatches_to_active_only(self, mock_apply_async):
        """디스패치 태스크 호출 시 사용자의 '활성' 구독들에 대해서만 하위 태스크를 병렬 기동시키는지 검증"""
        payload = {"title": "공통 알림", "body": "본문"}
        idempotency_key = "RECEIPT_PROCESSED:test_dispatch_active"

        dispatch_user_notifications_task(
            user_id=str(self.user.id), event_type="RECEIPT_PROCESSED", payload=payload, idempotency_key=idempotency_key
        )

        # 활성 구독인 sub1, sub2 총 2개에 대해서만 apply_async가 호출되었는지 확인
        self.assertEqual(mock_apply_async.call_count, 2)

        # DB에 생성된 NotificationTask들 조회
        tasks = NotificationTask.objects.filter(idempotency_key=idempotency_key)
        self.assertEqual(tasks.count(), 2)
        # 비활성 구독(sub_inactive)에 매핑된 태스크는 없어야 함
        self.assertFalse(tasks.filter(subscription=self.sub_inactive).exists())

    def test_db_60second_idempotency_window(self):
        """60초 내 성공한 동일 유형 알림이 있을 경우 중복 감지 확인"""
        # 가상의 태스크 및 성공 로그 생성
        task = NotificationTask.objects.create(
            user=self.user,
            subscription=self.sub1,
            event_type="RECEIPT_PROCESSED",
            idempotency_key="RECEIPT_PROCESSED:test_dup_1",
            title="1차 결제",
            body="성공",
            status="SUCCESS",
        )
        NotificationLog.objects.create(
            task=task, user=self.user, channel="FCM", endpoint_hint=self.sub1.endpoint[:255], is_success=True
        )

        # 60초 내 중복 검사
        self.assertTrue(is_duplicate_notification(str(self.user.id), "RECEIPT_PROCESSED"))

        # 다른 이벤트 유형은 중복이 아니어야 함
        self.assertFalse(is_duplicate_notification(str(self.user.id), "BUDGET_THRESHOLD_ALERT"))

    @patch("apps.notifications.services.get_redis_client")
    @patch("apps.notifications.tasks.dispatch_user_notifications_task.apply_async")
    def test_redis_idempotency_lock_service(self, mock_dispatch_apply, mock_get_redis):
        """Redis 분산 락에 의한 중복 적재 요청 차단 검증"""
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        # 첫 번째 호출 시 nx=True로 락 획득 성공 (True 반환)
        mock_redis.set.return_value = True
        success1 = enqueue_receipt_notification(
            user_id=str(self.user.id), ledger_id="mock_ledger_uuid", vendor_name="가맹점", total_amount="12000"
        )
        self.assertTrue(success1)
        self.assertEqual(mock_dispatch_apply.call_count, 1)

        # 두 번째 호출 시 nx=True로 락 획득 실패 (False/None 반환)
        mock_redis.set.return_value = False
        success2 = enqueue_receipt_notification(
            user_id=str(self.user.id), ledger_id="mock_ledger_uuid", vendor_name="가맹점", total_amount="12000"
        )
        self.assertFalse(success2)
        # 추가 적재 태스크 호출은 발생하지 않음
        self.assertEqual(mock_dispatch_apply.call_count, 1)

    @patch("apps.notifications.services.enqueue_budget_alert_notification")
    @patch("apps.notifications.services.enqueue_receipt_notification")
    @patch("apps.ledgers.services.LedgerService.ingest_receipt_task")
    def test_receipt_task_success_triggers_notification(self, mock_ingest, mock_enqueue_notify, mock_enqueue_budget):
        """[T023] 영수증 파싱 작업(ReceiptTask) 완료 시, 성공 로그 전 알림 트리거가 정상 연동되는지 검증"""
        from unittest.mock import mock_open

        from apps.ledgers.models import Ledger, ReceiptTask
        from apps.ledgers.tasks import extract_receipt_task

        # 1. 목업 셋업
        mock_ingest.return_value = {"status": "SUCCESS"}

        # 가상의 영수증 데이터와 완료된 Ledger 모의 생성 (supply_value, vat_amount 추가)
        ledger = Ledger.objects.create(
            user=self.user,
            vendor_name="테스트상점",
            total_amount=15000,
            supply_value=13636,
            vat_amount=1364,
            transaction_date=timezone.now(),
        )

        task = ReceiptTask.objects.create(
            user=self.user, file_name="receipt.jpg", file_path="/tmp/receipt.jpg", status="PENDING"
        )

        # ingest_receipt_task 실행 후 db에 ledger가 세팅되도록 Mocking 함수 설정
        def side_effect(*args, **kwargs):
            existing_task = kwargs.get("existing_task")
            existing_task.status = "COMPLETED"
            existing_task.ledger = ledger
            existing_task.save()
            return {"status": "COMPLETED"}

        mock_ingest.side_effect = side_effect

        # 2. 실행
        # 임시 영수증 파일 존재 모의화 (os.path.exists)
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=b"dummy")),
            patch("os.remove", return_value=True),
        ):
            extract_receipt_task(task_id=str(task.id), file_path="/tmp/receipt.jpg")

        # 3. 검증
        mock_enqueue_notify.assert_called_once_with(
            user_id=str(self.user.id), ledger_id=str(ledger.id), vendor_name="테스트상점", total_amount="15000.00"
        )

    @patch("apps.ledgers.signals.enqueue_budget_alert_notification")
    def test_ledger_save_triggers_budget_alert(self, mock_enqueue_budget):
        """[T024] Ledger 저장 시 당월 총 지출이 예산 임계값(80%, 100%)을 넘으면 예산 알림이 적재되는지 검증"""
        import datetime

        import django.db.transaction
        from apps.ledgers.models import Ledger, MonthlyBudget

        # 1. 당월 예산 설정 (100,000원)
        today = timezone.now().date()
        start_of_month = datetime.date(today.year, today.month, 1)

        # 기존 예산 객체가 존재하면 삭제 후 재생성
        MonthlyBudget.objects.filter(user=self.user, budget_month=start_of_month).delete()
        MonthlyBudget.objects.create(user=self.user, budget_month=start_of_month, amount=100000)

        # 기존 Ledger 내역들 청소하여 정확한 합산 지출 테스트 보장
        Ledger.objects.filter(user=self.user).delete()

        # django.db.transaction.on_commit 글로벌 모킹
        original_on_commit = django.db.transaction.on_commit
        django.db.transaction.on_commit = lambda fn: fn()

        try:
            # 2. 지출 내역 생성 - 80,000원 (80% 도달)
            Ledger.objects.create(
                user=self.user,
                vendor_name="상점A",
                total_amount=80000,
                supply_value=72727,
                vat_amount=7273,
                transaction_date=timezone.now(),
            )

            mock_enqueue_budget.assert_called_once_with(
                user_id=str(self.user.id),
                year=today.year,
                month=today.month,
                spent_amount=80000,
                budget_amount=100000,
                threshold_percent=80,
            )

            # 3. 추가 지출 내역 생성 - 20,000원 (총 100,000원, 100% 도달)
            mock_enqueue_budget.reset_mock()
            Ledger.objects.create(
                user=self.user,
                vendor_name="상점B",
                total_amount=20000,
                supply_value=18182,
                vat_amount=1818,
                transaction_date=timezone.now(),
            )

            mock_enqueue_budget.assert_called_once_with(
                user_id=str(self.user.id),
                year=today.year,
                month=today.month,
                spent_amount=100000,
                budget_amount=100000,
                threshold_percent=100,
            )
        finally:
            django.db.transaction.on_commit = original_on_commit

    def test_push_payload_size_limit_validation(self):
        """[T035] 4KB(4,096바이트)를 초과하는 웹 푸시 페이로드 구성 시 PushPayloadTooLargeError가 발생하는지 검증"""
        from apps.notifications.sender import PushPayloadTooLargeError, send_web_push

        # 1. 4KB 초과하는 더미 페이로드 구성 (한글 1글자당 3바이트 인코딩 감안하여 1500글자 초과)
        large_body = "가" * 1500  # 4,500 bytes
        payload = {"title": "엄청나게 긴 푸시 제목", "body": large_body}

        subscription_info = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/token_dummy",
            "keys": {"p256dh": "p256dh_dummy", "auth": "auth_dummy"},
        }

        # 2. 예외 검증
        with self.assertRaises(PushPayloadTooLargeError):
            send_web_push(subscription_info, payload)

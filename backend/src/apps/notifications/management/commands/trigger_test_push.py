import uuid

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.sender import detect_push_channel, send_web_push
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Trigger a synchronous test web push notification to a specific user for diagnostics."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="The username of the user to send the test push notification to.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.") from None

        active_subs = UserPushSubscription.objects.filter(user=user, is_active=True)
        if not active_subs.exists():
            self.stdout.write(f"No active subscriptions found for user '{username}'.")
            return

        self.stdout.write(f"Found {active_subs.count()} active subscription(s) for user '{username}'.")

        for sub in active_subs:
            # 1. 고유한 idempotency_key 생성
            idempotency_key = f"test_push_{uuid.uuid4().hex}"

            # 2. NotificationTask 생성 (이벤트 타입은 TEST_PUSH 적용)
            task = NotificationTask.objects.create(
                user=user,
                subscription=sub,
                event_type="TEST_PUSH",
                idempotency_key=idempotency_key,
                title="진단용 테스트 알림",
                body="서버와 클라이언트 알림망이 정상적으로 연결되었습니다.",
                action_url="https://localhost:8000/",
                status="PROCESSING",
            )

            # 3. VAPID 정보 조립
            subscription_info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
            payload = {"title": task.title, "body": task.body, "action_url": task.action_url}

            try:
                # 4. 즉시(동기) 발송 처리 - 정규 비동기 Celery 큐를 우회함
                result = send_web_push(subscription_info, payload)

                if result["is_success"]:
                    task.status = "SUCCESS"
                    task.save()

                    NotificationLog.objects.create(
                        task=task,
                        user=user,
                        channel=result["channel"],
                        endpoint_hint=sub.endpoint[:255],
                        http_status_code=result["http_status_code"],
                        response_body=result["response_body"],
                        is_success=True,
                        status="SENT",
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully triggered test push for user '{username}' (endpoint: {sub.endpoint[:30]}...)."
                        )
                    )
                else:
                    status_code = result["http_status_code"]
                    if status_code in (404, 410):
                        # 만료된 구독인 경우 비활성화
                        sub.is_active = False
                        sub.save()
                        self.stdout.write(
                            self.style.WARNING(
                                f"Subscription expired (status {status_code}). Deactivated sub: {sub.id}"
                            )
                        )

                    task.status = "FAILED"
                    task.save()

                    NotificationLog.objects.create(
                        task=task,
                        user=user,
                        channel=result["channel"],
                        endpoint_hint=sub.endpoint[:255],
                        http_status_code=status_code,
                        response_body=result["response_body"],
                        is_success=False,
                        status="FAILED",
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed sending web push to endpoint {sub.endpoint[:30]}... Status code: {status_code}"
                        )
                    )

            except Exception as e:
                task.status = "FAILED"
                task.save()

                NotificationLog.objects.create(
                    task=task,
                    user=user,
                    channel=detect_push_channel(sub.endpoint),
                    endpoint_hint=sub.endpoint[:255],
                    http_status_code=None,
                    response_body=str(e)[:2000],
                    is_success=False,
                    status="FAILED",
                )
                self.stdout.write(self.style.ERROR(f"Exception during push dispatch: {str(e)}"))

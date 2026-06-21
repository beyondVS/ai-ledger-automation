import logging
from datetime import timedelta

from apps.accounts.models import User, UserPushSubscription
from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.sender import send_web_push
from apps.notifications.services import is_duplicate_notification
from celery import shared_task
from django.db import IntegrityError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="notifications",
    name="apps.notifications.tasks.send_push_notification",
)
def send_push_notification_task(self, notification_task_id: str) -> dict:
    """
    [T022] 단일 디바이스 구독 단말에 웹 푸시 알림을 발송하는 핵심 Celery 태스크
    - 지수 백오프 기반 재시도(5s -> 10s -> 20s)를 적용합니다.
    - 410 Gone 응답 수신 시 해당 구독을 즉시 비활성화(is_active=False) 처리합니다.
    - 최종 성공/실패 여부를 NotificationLog에 영속 감사 기록합니다.
    """
    try:
        task = NotificationTask.objects.select_related("subscription", "user").get(id=notification_task_id)
    except NotificationTask.DoesNotExist:
        logger.error(f"NotificationTask {notification_task_id} does not exist.")
        return {"status": "FAILED", "error": "Task not found"}

    sub = task.subscription
    if not sub or not sub.is_active:
        logger.warning(f"Subscription {sub.id if sub else 'None'} is inactive or deleted. Aborting push.")
        task.status = "FAILED"
        task.save()
        return {"status": "FAILED", "error": "Inactive subscription"}

    task.status = "PROCESSING"
    task.last_attempted_at = timezone.now()
    task.retry_count = self.request.retries
    task.save()

    subscription_info = {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}}
    payload = {"title": task.title, "body": task.body, "action_url": task.action_url}

    # 외부 웹 푸시 전송 시도 (예외 발생 시 고스트 태스크 방지 방어 코드 적용)
    from apps.notifications.sender import PushPayloadTooLargeError, detect_push_channel

    try:
        result = send_web_push(subscription_info, payload)
    except PushPayloadTooLargeError as exc:
        logger.error(f"VAPID payload size limit exceeded for task {notification_task_id}: {exc}")
        with transaction.atomic():
            task.status = "FAILED"
            task.save()
            NotificationLog.objects.create(
                task=task,
                user=task.user,
                channel=detect_push_channel(sub.endpoint),
                endpoint_hint=sub.endpoint[:255],
                http_status_code=None,
                response_body=str(exc)[:2000],
                is_success=False,
                status="FAILED",
            )
        return {"status": "FAILED", "error": "Payload size limit exceeded"}
    except Exception as exc:
        logger.error(f"Unexpected error in send_web_push for task {notification_task_id}: {exc}")
        with transaction.atomic():
            task.status = "FAILED"
            task.save()
        raise exc

    if result["is_success"]:
        # 성공 시 이력 기록 및 상태 변경
        with transaction.atomic():
            task.status = "SUCCESS"
            task.save()
            NotificationLog.objects.create(
                task=task,
                user=task.user,
                channel=result["channel"],
                endpoint_hint=sub.endpoint[:255],
                http_status_code=result["http_status_code"],
                response_body=result["response_body"],
                is_success=True,
                status="SENT",
            )
        return {"status": "SUCCESS", "task_id": notification_task_id}

    else:
        # 실패 처리
        status_code = result["http_status_code"]
        is_gone = status_code == 410 or status_code == 404

        if is_gone:
            # 410 Gone 또는 404 Not Found의 경우 단말 만료 상태이므로 자동 비활성 및 재시도 배제 (FR-006)
            logger.warning(f"Subscription {sub.id} reported Gone (410). Disabling subscription.")
            with transaction.atomic():
                sub.is_active = False
                sub.save()

                task.status = "FAILED"
                task.save()

                NotificationLog.objects.create(
                    task=task,
                    user=task.user,
                    channel=result["channel"],
                    endpoint_hint=sub.endpoint[:255],
                    http_status_code=status_code,
                    response_body=result["response_body"],
                    is_success=False,
                    status="FAILED",
                )
            return {"status": "FAILED", "error": "Subscription expired"}

        else:
            # 그 외 일시적인 연동 장애 등의 경우 지수 백오프 기반 재시도 태움 (최대 3회)
            logger.warning(f"Failed sending web push. Status: {status_code}. Scheduling retry.")

            # 지수 백오프 계산: default_retry_delay * (2 ** retries)
            next_delay = self.default_retry_delay * (2**self.request.retries)
            try:
                self.retry(exc=Exception(result["response_body"]), countdown=next_delay)
            except self.MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for task {notification_task_id}")
                with transaction.atomic():
                    task.status = "FAILED"
                    task.save()
                    NotificationLog.objects.create(
                        task=task,
                        user=task.user,
                        channel=result["channel"],
                        endpoint_hint=sub.endpoint[:255],
                        http_status_code=status_code,
                        response_body=result["response_body"],
                        is_success=False,
                        status="FAILED",
                    )
                return {"status": "FAILED", "error": "Max retries exceeded"}


@shared_task(queue="notifications", name="apps.notifications.tasks.dispatch_user_notifications")
def dispatch_user_notifications_task(
    user_id: str,
    event_type: str,
    payload: dict,
    idempotency_key: str,
) -> dict:
    """
    [T022] 사용자의 모든 활성 구독 단말에 알림 하위 태스크를 병렬로 배포(Dispatch)합니다.
    - DB 이중 방어: 60초 내 성공한 동일 알림 이력이 존재하는지 검사하여 중복을 차단합니다.
    - 원자적 트랜잭션 블록 내에서 태스크 생성 및 큐 적재를 처리합니다.
    """
    # 1. DB 60초 시간 윈도우 중복 검증
    if is_duplicate_notification(user_id, event_type, window_seconds=60, idempotency_key=idempotency_key):
        logger.warning(f"Duplicate push event blocked by DB 60s window: {idempotency_key}")
        return {"status": "IGNORED", "reason": "DB 60s window duplicate"}

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for notification dispatch.")
        return {"status": "FAILED", "error": "User not found"}

    # 활성 상태인 단말 구독만 추출
    active_subs = list(UserPushSubscription.objects.filter(user=user, is_active=True))
    if not active_subs:
        logger.info(f"No active push subscriptions found for user {user.username}")
        return {"status": "NO_ACTIVE_SUBS"}

    logger.info(f"Dispatching notification {event_type} to {len(active_subs)} devices for user {user.username}")

    dispatched_tasks = []
    for sub in active_subs:
        try:
            with transaction.atomic():
                # 각 단말 구독별로 NotificationTask 생성 (복수 기기 병렬 적재)
                task = NotificationTask.objects.create(
                    user=user,
                    subscription=sub,
                    event_type=event_type,
                    idempotency_key=idempotency_key,
                    title=payload.get("title", ""),
                    body=payload.get("body", ""),
                    action_url=payload.get("action_url", ""),
                    status="PENDING",
                )

            # 생성에 성공했으므로 개별 발송 비동기 태스크 큐에 적재
            send_push_notification_task.apply_async(args=[str(task.id)])
            dispatched_tasks.append(str(task.id))

        except IntegrityError:
            # UniqueConstraint 위반(이미 다른 단말에서 멱등 적재됨 등) 시 중복이므로 안전하게 스킵
            logger.warning(f"IntegrityError: Duplicate idempotency key for sub {sub.id}. Skipped.")
            continue

    return {"status": "DISPATCHED", "task_ids": dispatched_tasks}


@shared_task(queue="notifications", name="apps.notifications.tasks.cleanup_old_notification_logs")
def cleanup_old_notification_logs() -> str:
    """
    [T022] 30일이 경과한 NotificationLog 레코드를 자동으로 정리하는 Celery Beat 태스크
    - 매일 새벽 2시 구동되도록 settings/base.py에 Beat 스케줄러가 등록되어 있습니다.
    """
    cutoff = timezone.now() - timedelta(days=30)
    deleted_count, _ = NotificationLog.objects.filter(created_at__lt=cutoff).delete()
    msg = f"Cleaned up {deleted_count} old notification logs (cutoff: {cutoff})"
    logger.info(msg)
    return msg

import logging
from datetime import timedelta

import redis
from apps.notifications.models import NotificationLog
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_redis_client():
    """Celery 브로커 URL을 파싱하여 redis 클라이언트를 반환합니다."""
    return redis.from_url(settings.CELERY_BROKER_URL)


def acquire_idempotency_lock(lock_key: str, ttl_seconds: int = 300) -> bool:
    """
    [T011] Redis nx=True 옵션을 이용해 분산 락을 획득합니다 (기본 5분 TTL).
    - 락 획득 성공 시 True, 이미 락이 잡혀 중복 제출 시 False를 반환합니다.
    """
    try:
        r = get_redis_client()
        return bool(r.set(lock_key, "1", nx=True, ex=ttl_seconds))
    except Exception as ex:
        logger.error(f"Failed to check Redis idempotency lock: {ex}")
        # Redis 연결 장애 시 안전을 위해 락 획득 성공(True)으로 패스하여 메인 큐 가동을 중단시키지 않음
        return True


def is_duplicate_notification(
    user_id: str, event_type: str, window_seconds: int = 60, idempotency_key: str = None
) -> bool:
    """
    [T011] DB 레벨 시간 윈도우 중복 체크
    - 60초 내에 특정 사용자에게 동일한 이벤트 유형의 성공 알림 이력이 존재하는지 검증합니다.
    - BUDGET_THRESHOLD_ALERT의 경우, 임계치 구분을 위해 idempotency_key 매칭을 수행합니다.
    """
    cutoff = timezone.now() - timedelta(seconds=window_seconds)
    qs = NotificationLog.objects.filter(
        user_id=user_id, task__event_type=event_type, is_success=True, created_at__gte=cutoff
    )
    if idempotency_key and event_type == "BUDGET_THRESHOLD_ALERT":
        qs = qs.filter(task__idempotency_key=idempotency_key)
    return qs.exists()


def enqueue_receipt_notification(user_id: str, ledger_id: str, vendor_name: str, total_amount: str) -> bool:
    """
    [T011] 영수증 처리 완료 알림을 비동기 큐에 적재합니다.
    - 락 키 형식: "push_lock:RECEIPT_PROCESSED:{user_id}:{ledger_id}"
    """
    event_type = "RECEIPT_PROCESSED"
    idempotency_key = f"{event_type}:{user_id}:{ledger_id}"
    lock_key = f"push_lock:{idempotency_key}"

    if not acquire_idempotency_lock(lock_key):
        logger.warning(f"Duplicate receipt notification submit prevented by Redis lock: {idempotency_key}")
        return False

    # 지출 내역 금액 포맷팅 처리
    try:
        amount_fmt = f"{int(float(total_amount)):,}"
    except (ValueError, TypeError):
        amount_fmt = total_amount

    payload = {
        "title": "영수증 처리 완료",
        "body": f"{vendor_name}에서 {amount_fmt}원 결제가 등록되었습니다.",
        "action_url": "/dashboard",
    }

    # Celery 태스크를 비동기 호출합니다. (태스크 임포트 순환 참조 방지를 위해 로컬 임포트)
    from apps.notifications.tasks import dispatch_user_notifications_task

    dispatch_user_notifications_task.apply_async(args=[user_id, event_type, payload, idempotency_key])
    logger.info(f"Enqueued receipt notification task. User: {user_id}, Ledger: {ledger_id}")
    return True


def enqueue_budget_alert_notification(
    user_id: str, year: int, month: int, spent_amount: int, budget_amount: int, threshold_percent: int = 80
) -> bool:
    """
    [T011] 월별 예산 임계 초과 알림을 비동기 큐에 적재합니다.
    - 락 키 형식: "push_lock:BUDGET_THRESHOLD_ALERT:{user_id}:{year}-{month}:{threshold_percent}"
    """
    event_type = "BUDGET_THRESHOLD_ALERT"
    idempotency_key = f"{event_type}:{user_id}:{year}-{month:02d}:{threshold_percent}"
    lock_key = f"push_lock:{idempotency_key}"

    if not acquire_idempotency_lock(lock_key):
        logger.warning(f"Duplicate budget alert notification submit prevented by Redis lock: {idempotency_key}")
        return False

    payload = {
        "title": "월별 지출 경보",
        "body": f"이번 달 예산의 {threshold_percent}%를 초과했습니다. ({spent_amount:,}원 / {budget_amount:,}원)",
        "action_url": "/dashboard",
    }

    from apps.notifications.tasks import dispatch_user_notifications_task

    dispatch_user_notifications_task.apply_async(args=[user_id, event_type, payload, idempotency_key])
    logger.info(
        f"Enqueued budget alert notification task. User: {user_id}, Period: {year}-{month:02d}, Threshold: {threshold_percent}%"
    )
    return True

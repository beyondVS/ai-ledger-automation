from apps.accounts.models import User, UserPushSubscription, generate_uuidv7
from django.db import models


class NotificationTask(models.Model):
    """
    [T008] 알림 발송 큐 태스크 레코드
    - 비동기 Celery 태스크와 1:1로 매핑되는 상태 추적 모델입니다.
    - idempotency_key를 장착하여 중복 발송을 차단합니다.
    """

    STATUS_CHOICES = [
        ("PENDING", "대기 중"),
        ("PROCESSING", "처리 중"),
        ("SUCCESS", "성공"),
        ("FAILED", "실패"),
    ]

    EVENT_TYPE_CHOICES = [
        ("RECEIPT_PROCESSED", "영수증 처리 완료"),
        ("BUDGET_THRESHOLD_ALERT", "월별 예산 임계 초과"),
    ]

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_tasks")
    subscription = models.ForeignKey(
        UserPushSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_tasks",
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    idempotency_key = models.CharField(max_length=255, db_index=True)

    title = models.CharField(max_length=255)
    body = models.TextField()
    action_url = models.URLField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    retry_count = models.PositiveSmallIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_tasks"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key", "subscription"],
                name="unique_notification_task_idempotency",
            )
        ]
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return f"NotificationTask for {self.user.username} - {self.event_type} ({self.status})"


class NotificationLog(models.Model):
    """
    [T008] 알림 발송 감사 이력 감사 로그
    - 성공/실패 여부 및 푸시 게이트웨이의 HTTP 응답 상태를 영구 기록합니다.
    - 보존 기간: 30일 (새벽 2시 Celery Beat 배치 정리 대상)
    """

    CHANNEL_CHOICES = [
        ("FCM", "Firebase Cloud Messaging"),
        ("APPLE_VAPID", "Apple Web Push (VAPID)"),
        ("GENERIC_VAPID", "Generic Web Push (VAPID)"),
    ]

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    task = models.ForeignKey(NotificationTask, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="notification_logs")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    endpoint_hint = models.CharField(max_length=255)  # 감사용 앞부분 255자 저장
    http_status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True, max_length=2000)
    is_success = models.BooleanField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "대기 중"),
            ("SENT", "발송 완료"),
            ("DELIVERED", "수신 완료"),
            ("FAILED", "실패"),
        ],
        default="PENDING",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notification_logs"
        indexes = [
            models.Index(fields=["user", "is_success", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        status = "SUCCESS" if self.is_success else "FAILED"
        return f"NotificationLog for {self.user.username if self.user else 'Unknown'} - {status} ({self.channel})"

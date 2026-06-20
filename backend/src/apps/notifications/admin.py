from apps.notifications.models import NotificationLog, NotificationTask
from apps.notifications.tasks import send_push_notification_task
from django.contrib import admin


@admin.register(NotificationTask)
class NotificationTaskAdmin(admin.ModelAdmin):
    """
    [T028] NotificationTask Django 어드민 설정
    - 생성된 비동기 푸시 태스크들의 상태를 모니터링하고 강제 재발송 액션을 기동합니다.
    """

    list_display = ("id", "user", "event_type", "status", "title", "created_at")
    list_filter = ("status", "event_type")
    search_fields = ("user__username", "title", "idempotency_key")
    actions = ["retry_sending_notifications"]

    @admin.action(description="선택한 태스크들을 큐에 강제 재적재하여 재발송합니다.")
    def retry_sending_notifications(self, request, queryset):
        count = 0
        for task in queryset:
            # 상태를 PENDING으로 전이하고 비동기 재발송 큐 적재
            task.status = "PENDING"
            task.save()
            send_push_notification_task.apply_async(args=[str(task.id)])
            count += 1
        self.message_user(request, f"{count}개의 태스크가 성공적으로 발송 큐에 재적재되었습니다.")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    [T028] NotificationLog Django 어드민 설정
    - 실제 발송된 푸시 알림 전송 이력 및 성공/실패 여부를 세부 로깅 확인합니다.
    """

    list_display = ("task", "user", "channel", "is_success", "http_status_code", "created_at")
    list_filter = ("channel", "is_success", "http_status_code")
    search_fields = ("user__username", "endpoint_hint")
    readonly_fields = (
        "task",
        "user",
        "channel",
        "endpoint_hint",
        "is_success",
        "http_status_code",
        "response_body",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

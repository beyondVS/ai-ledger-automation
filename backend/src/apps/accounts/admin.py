from apps.accounts.models import User, UserPushSubscription
from django.contrib import admin


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    User 모델 어드민 커스텀 설정
    """

    list_display = ("id", "email", "created_at", "updated_at")
    search_fields = ("email", "registered_forward_email_1")
    ordering = ("-created_at",)


@admin.register(UserPushSubscription)
class UserPushSubscriptionAdmin(admin.ModelAdmin):
    """
    [T028] UserPushSubscription Django 어드민 설정
    - 단말 구독 정보를 리스트 조회 및 비활성화 처리할 수 있습니다.
    """

    list_display = ("user", "get_endpoint_hint", "is_active", "device_hint", "created_at", "updated_at")
    list_filter = ("is_active", "device_hint")
    search_fields = ("user__username", "user__email", "endpoint")
    actions = ["deactivate_subscriptions", "activate_subscriptions"]

    @admin.display(description="Endpoint URL")
    def get_endpoint_hint(self, obj):
        if obj.endpoint:
            return f"...{obj.endpoint[-50:]}" if len(obj.endpoint) > 50 else obj.endpoint
        return "-"

    @admin.action(description="선택한 구독을 일괄 비활성화합니다.")
    def deactivate_subscriptions(self, request, queryset):
        rows_updated = queryset.update(is_active=False)
        self.message_user(request, f"{rows_updated}개의 구독이 성공적으로 비활성화되었습니다.")

    @admin.action(description="선택한 구독을 일괄 활성화합니다.")
    def activate_subscriptions(self, request, queryset):
        rows_updated = queryset.update(is_active=True)
        self.message_user(request, f"{rows_updated}개의 구독이 성공적으로 활성화되었습니다.")

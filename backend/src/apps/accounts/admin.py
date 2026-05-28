from django.contrib import admin
from apps.accounts.models import User, UserPushSubscription

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    User 모델 어드민 커스텀 설정
    """
    list_display = ('id', 'email', 'created_at', 'updated_at')
    search_fields = ('email', 'registered_forward_email_1')
    ordering = ('-created_at',)


@admin.register(UserPushSubscription)
class UserPushSubscriptionAdmin(admin.ModelAdmin):
    """
    UserPushSubscription 모델 어드민 커스텀 설정
    """
    list_display = ('id', 'user', 'endpoint', 'created_at')
    search_fields = ('user__email', 'endpoint')
    ordering = ('-created_at',)

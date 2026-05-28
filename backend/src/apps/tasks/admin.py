from django.contrib import admin
from apps.tasks.models import FailedTask

@admin.register(FailedTask)
class FailedTaskAdmin(admin.ModelAdmin):
    """
    FailedTask 모델 어드민 커스텀 설정
    - 에러 로그 데이터의 무결성 보존 및 임의 수정을 예방하기 위해
      원시 페이로드와 예외 콜스택은 조회 전용(readonly)으로 엄격 통제합니다.
    """
    list_display = ('id', 'user', 'task_type', 'error_message', 'created_at')
    list_filter = ('task_type',)
    search_fields = ('error_message', 'task_type', 'user__email')
    ordering = ('-created_at',)
    
    readonly_fields = ('raw_payload', 'error_stacktrace', 'created_at')

from django.db import models
from apps.accounts.models import generate_uuidv7

class FailedTask(models.Model):
    """
    [T014] FailedTask 데이터 모델
    - 비동기 처리(Celery)나 API 트랜잭션 도중 발생한 예외(중복 위배, LLM 실패 등)에 대해
      원시 페이로드와 에러 상세 메시지, 디버깅 콜스택을 영구 격리(Dead Letter Queue) 보존합니다.
    """
    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='failed_tasks')
    
    # 작업 식별 분류 (예: 'API_LEDGER_INGEST', 'EMAIL_WEBHOOK', 'AI_PARSER')
    task_type = models.CharField(max_length=50)
    
    # 실패한 원시 입력 페이로드 (텍스트 또는 JSON 백업)
    raw_payload = models.TextField()
    
    error_message = models.TextField()
    error_stacktrace = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'failed_tasks'
        verbose_name = 'failed_task'
        verbose_name_plural = 'failed_tasks'

    def __str__(self):
        return f"FailedTask [{self.task_type}] ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')}) - {self.error_message[:30]}"

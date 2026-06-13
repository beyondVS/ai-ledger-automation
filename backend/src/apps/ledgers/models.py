from apps.accounts.models import generate_uuidv7
from django.db import models


class Ledger(models.Model):
    """
    [T009, T012] Ledger 데이터 모델
    - 개별 영수증 결제 마스터 지출 정보를 보존합니다.
    - 동일 영수증 복사 업로드를 방지하는 DB 복합 유니크 제약조건을 장착합니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="ledgers")

    # 10자리 사업자번호가 부재할 시 COALESCE 기본값 '0000000000' 적용
    vendor_registration_number = models.CharField(max_length=10, default="0000000000")
    vendor_name = models.CharField(max_length=255)
    transaction_date = models.DateTimeField()
    approval_number = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    supply_value = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # 지출 카테고리 (T004)
    category = models.CharField(max_length=100, default="미분류", db_index=True)

    # LLM 파싱 성공 원시 응답 JSONB 백업 보존
    raw_llm_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ledgers"
        verbose_name = "ledger"
        verbose_name_plural = "ledgers"

        # 헌법 I조 수호: 동일 영수증 이중 삽입 방지를 위한 강력한 복합 고유 제약조건 선언
        constraints = [
            models.UniqueConstraint(
                fields=["user", "vendor_registration_number", "transaction_date", "total_amount"],
                name="unique_ledger_transaction",
            )
        ]

    def __str__(self):
        return f"{self.vendor_name} ({self.total_amount}원) - {self.transaction_date}"

    def save(self, *args, **kwargs):
        # Edge Case 방어: 빈 사업자번호나 공백이 유입되는 경우 기본값 치환
        if not self.vendor_registration_number or self.vendor_registration_number.strip() == "":
            self.vendor_registration_number = "0000000000"
        super().save(*args, **kwargs)


class LedgerItem(models.Model):
    """
    [T010] LedgerItem 데이터 모델
    - 개별 영수증(Ledger) 내의 세부 상세 개별 품목 명세를 1:N 관계로 매핑 보존합니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    ledger = models.ForeignKey(Ledger, on_delete=models.CASCADE, related_name="items")

    item_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_items"
        verbose_name = "ledger_item"
        verbose_name_plural = "ledger_items"

    def __str__(self):
        return f"{self.item_name} ({self.quantity}개 * {self.unit_price}원)"


class VerifiedTemplateManager(models.Manager):
    """
    [T019] VerifiedTemplateManager
    - 오직 수동 검토 완료 및 신뢰가 확보되어 is_verified: True 상태인 규칙만 우회 바이패스에 반영하며,
      미검증 템플릿의 bypass 파서 오동작 진입율을 영구히 0%로 통제합니다.
      블랙리스트(is_blacklisted: True) 상태인 템플릿은 우회 대상에서 제외됩니다.
    """

    def get_bypass_rule(self, vendor_registration_number: str):
        return self.filter(
            vendor_registration_number=vendor_registration_number, is_verified=True, is_blacklisted=False
        ).first()


class MerchantTemplate(models.Model):
    """
    [T018] MerchantTemplate 데이터 모델
    - 가맹점 사업자등록번호 기반 정적 정규식 파싱 규칙 캐시를 보존하여 유료 LLM 비용을 최적화합니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)

    # 10자리 사업자등록번호 고유 키
    vendor_registration_number = models.CharField(unique=True, max_length=10)
    vendor_name = models.CharField(max_length=255)

    # 정규식 레이아웃 파싱 규칙 세트 JSONB
    parsing_rules = models.JSONField()

    # 헌법 III조 수호: 캐시 정보 자율 학습 제안 시 기본값은 반드시 False로 보존
    is_verified = models.BooleanField(default=False)

    # 비동기 Celery 정규식 유효성 테스트 성공 여부
    is_auto_verified = models.BooleanField(default=False)
    # 유효성 검사 실패 시 에러 로그 기록
    regex_error_message = models.TextField(blank=True, null=True)

    consistency_count = models.IntegerField(default=0)
    self_healing_attempts = models.IntegerField(default=0)
    is_blacklisted = models.BooleanField(default=False)
    last_healing_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 기본 매니저와 VAPID 보안용 승인 템플릿 전용 매니저 등록
    objects = models.Manager()
    verified_objects = VerifiedTemplateManager()

    class Meta:
        db_table = "merchant_templates"
        verbose_name = "merchant_template"
        verbose_name_plural = "merchant_templates"

    def __str__(self):
        return f"Template for {self.vendor_name} ({self.vendor_registration_number})"


class ReceiptUploadJob(models.Model):
    """
    [T004, T011] ReceiptUploadJob 데이터 모델
    - 영수증 분석 요청을 추적하기 위한 비동기 작업 정보 테이블입니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="receipt_jobs", null=True, blank=True
    )
    status = models.CharField(max_length=20, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    raw_file_name = models.CharField(max_length=255, null=True, blank=True)
    ledger = models.OneToOneField(Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name="upload_job")
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "receipt_upload_jobs"
        verbose_name = "receipt_upload_job"
        verbose_name_plural = "receipt_upload_jobs"

    def __str__(self):
        return f"Job {self.id} - {self.status}"


class TemplateExecutionHistory(models.Model):
    """
    [T005] TemplateExecutionHistory 데이터 모델
    - 가맹점 템플릿의 실행 이력과 오류 및 사용자 수동 정정 차이(Diff) 데이터를 보존합니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    template = models.ForeignKey(
        MerchantTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="execution_histories"
    )
    ledger = models.ForeignKey(
        Ledger, on_delete=models.SET_NULL, null=True, blank=True, related_name="template_histories"
    )
    execution_time = models.DateTimeField(auto_now_add=True)
    parsing_mode = models.CharField(max_length=10)  # "LLM" or "BYPASS"
    is_success = models.BooleanField(default=True)
    user_corrected = models.BooleanField(default=False)
    corrected_diff = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "template_execution_histories"
        verbose_name = "template_execution_history"
        verbose_name_plural = "template_execution_histories"

    def __str__(self):
        return (
            f"History {self.id} for {self.template.vendor_name if self.template else 'Unknown'} ({self.parsing_mode})"
        )


class MonthlyBudget(models.Model):
    """
    [T004] MonthlyBudget 데이터 모델
    - 사용자별로 특정 월에 설정한 지출 목표 금액(예산) 정보를 저장합니다.
    - UNIQUE (user, budget_month) 복합 고유 제약조건을 장착합니다.
    """

    id = models.UUIDField(primary_key=True, default=generate_uuidv7, editable=False, db_index=True)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="monthly_budgets")

    # 예산 설정 연월. 매월 1일로 정규화하여 저장 (예: 2026-06-01)
    budget_month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=0, default=1000000)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "monthly_budgets"
        verbose_name = "monthly_budget"
        verbose_name_plural = "monthly_budgets"

        # 특정 사용자가 동일한 월에 중복 예산을 생성하는 것을 방어
        constraints = [
            models.UniqueConstraint(
                fields=["user", "budget_month"],
                name="unique_user_budget_month",
            )
        ]

    def __str__(self):
        return f"{self.user.username}의 {self.budget_month.strftime('%Y-%m')} 예산: {self.amount}원"

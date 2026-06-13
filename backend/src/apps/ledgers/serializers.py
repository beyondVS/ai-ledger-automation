from apps.ledgers.models import Ledger, LedgerItem, MonthlyBudget
from rest_framework import serializers


class LedgerItemResponseSerializer(serializers.ModelSerializer):
    """
    [T013] 가계부 상세 품목 응답 직렬화기
    - LedgerItem 모델 필드를 API 규격 필드명으로 매핑합니다.
    """

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, source="total_price")

    class Meta:
        model = LedgerItem
        fields = ["id", "item_name", "unit_price", "quantity", "amount"]


class LedgerListSerializer(serializers.ModelSerializer):
    """
    [T023] 가계부 리스트 조회 응답 직렬화기
    - Ledger 모델 필드를 그대로 응답으로 내보냅니다.
    """

    items = LedgerItemResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Ledger
        fields = [
            "id",
            "vendor_name",
            "vendor_registration_number",
            "transaction_date",
            "total_amount",
            "supply_value",
            "vat_amount",
            "category",
            "items",
            "created_at",
            "updated_at",
        ]

    def validate_vendor_name(self, value):
        if not value or value.strip() == "":
            raise serializers.ValidationError("가맹점명을 입력해주세요.")
        return value


class LedgerDetailResponseSerializer(serializers.ModelSerializer):
    """
    [T008] 이전 통합 테스트 호환을 위한 세부 직렬화기
    - id를 ledger_id로, vendor_name을 merchant_name으로 매핑합니다.
    """

    ledger_id = serializers.UUIDField(source="id")
    merchant_name = serializers.CharField(source="vendor_name")
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    items = LedgerItemResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Ledger
        fields = [
            "ledger_id",
            "merchant_name",
            "vendor_registration_number",
            "transaction_date",
            "total_amount",
            "items",
        ]


class ReceiptUploadResponseSerializer(serializers.Serializer):
    """
    [T013] 영수증 업로드 전체 응답 스키마
    - 3주차 비동기 Celery 아키텍처 하위 호환성을 위해 job_id 및 status를 포함합니다.
    """

    job_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    ledger = LedgerListSerializer(allow_null=True)
    data = LedgerDetailResponseSerializer(source="ledger", allow_null=True, required=False)


class MonthlyBudgetSerializer(serializers.ModelSerializer):
    """
    [T006] 월별 예산 데이터 직렬화기
    - MonthlyBudget 모델의 CRUD 입출력을 담당합니다.
    """

    class Meta:
        model = MonthlyBudget
        fields = ["id", "budget_month", "amount", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("예산 금액은 0원 이상이어야 합니다.")
        return value

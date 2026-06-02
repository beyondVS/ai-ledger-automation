from rest_framework import serializers

class LedgerItemResponseSerializer(serializers.Serializer):
    """
    [T013] 가계부 상세 품목 응답 직렬화기
    - LedgerItem 모델 필드를 API 규격 필드명으로 변환합니다.
    """
    name = serializers.CharField(source='item_name')
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, source='unit_price')


class LedgerDetailsResponseSerializer(serializers.Serializer):
    """
    [T013] 가계부 마스터 상세 응답 직렬화기
    - Ledger 모델 필드를 API 규격 필드명으로 변환합니다.
    """
    ledger_id = serializers.UUIDField(source='id')
    merchant_name = serializers.CharField(source='vendor_name')
    vendor_registration_number = serializers.CharField()
    transaction_date = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    items = LedgerItemResponseSerializer(many=True)


class ReceiptUploadResponseSerializer(serializers.Serializer):
    """
    [T013] 영수증 업로드 전체 응답 스키마
    - 3주차 비동기 Celery 아키텍처 하위 호환성을 위해 job_id 및 status를 포함합니다.
    """
    job_id = serializers.UUIDField()
    status = serializers.CharField()
    data = LedgerDetailsResponseSerializer(allow_null=True)

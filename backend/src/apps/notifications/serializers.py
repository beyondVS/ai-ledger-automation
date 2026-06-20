from apps.accounts.models import UserPushSubscription
from apps.notifications.sender import detect_push_channel
from rest_framework import serializers


class KeysSerializer(serializers.Serializer):
    """구독 등록 요청 내 중첩된 keys 객체 처리를 위한 직렬화"""

    p256dh = serializers.CharField(max_length=255)
    auth = serializers.CharField(max_length=255)


class UserPushSubscriptionSerializer(serializers.ModelSerializer):
    """
    [T015] UserPushSubscription 모델 직렬화 클래스
    - keys 객체를 p256dh, auth 필드로 평탄화하여 생성합니다.
    - list 응답 시에는 민감 정보(endpoint 등)를 제외합니다.
    """

    keys = KeysSerializer(write_only=True)

    class Meta:
        model = UserPushSubscription
        fields = ["id", "endpoint", "keys", "device_hint", "is_active", "created_at"]
        read_only_fields = ["id", "device_hint", "is_active", "created_at"]

    def create(self, validated_data):
        keys_data = validated_data.pop("keys")
        endpoint = validated_data["endpoint"]
        user = self.context["request"].user

        # 디바이스 유형 감지 및 자동 매핑
        device_hint = detect_push_channel(endpoint)

        # 멱등성 보장: 동일 사용자가 동일 엔드포인트를 다시 등록하는 경우
        # 기존 데이터를 갱신(is_active=True) 처리합니다.
        subscription, created = UserPushSubscription.objects.update_or_create(
            user=user,
            endpoint=endpoint,
            defaults={
                "p256dh": keys_data["p256dh"],
                "auth": keys_data["auth"],
                "is_active": True,
                "device_hint": device_hint,
            },
        )
        # 생성된/갱신된 객체 인스턴스에 context를 세팅해 200/201 응답 분기에 기여
        subscription._is_created = created
        return subscription

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")

        # 목록 조회(List) 시에는 민감 보안 정보를 제외합니다.
        if request and request.method == "GET" and "pk" not in request.parser_context.get("kwargs", {}):
            ret.pop("endpoint", None)

        return ret

from apps.accounts.models import UserPushSubscription
from apps.notifications.serializers import UserPushSubscriptionSerializer
from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView


class VapidPublicKeyView(APIView):
    """
    [T016] VAPID 공개키 조회 API 뷰
    - 프론트엔드가 구독 전 공개키 획득을 목적으로 인증 없이 호출 가능합니다.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        public_key = getattr(settings, "VAPID_PUBLIC_KEY", "")
        return Response({"public_key": public_key}, status=status.HTTP_200_OK)


class UserPushSubscriptionViewSet(viewsets.ModelViewSet):
    """
    [T016] UserPushSubscription REST API 뷰셋
    - 로그인한 사용자 본인의 구독에 한해서 조회, 등록, 비활성화(DELETE)를 전담합니다.
    """

    serializer_class = UserPushSubscriptionSerializer
    queryset = UserPushSubscription.objects.all()

    def get_queryset(self):
        # 본인 구독으로 필터 격리
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()

        # 신규 생성(201) 및 기존 갱신(200)에 따른 HTTP 상태 코드 매핑
        is_created = getattr(subscription, "_is_created", True)
        status_code = status.HTTP_201_CREATED if is_created else status.HTTP_200_OK

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code, headers=headers)

    def destroy(self, request, *args, **kwargs):
        # 물리 삭제 대신 is_active=False 비활성화 처리 (contracts/tasks 가이드 수호)
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

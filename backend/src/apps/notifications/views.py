from datetime import timedelta

from apps.accounts.models import UserPushSubscription
from apps.notifications.models import NotificationLog
from apps.notifications.serializers import UserPushSubscriptionSerializer
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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


class NotificationAcknowledgementView(APIView):
    """
    [T016] 웹 푸시 수신 확인 API 뷰
    - 단말의 서비스 워커가 푸시 메시지를 수신했을 때 백엔드 상태를 DELIVERED로 갱신합니다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            log = NotificationLog.objects.get(id=id, user=request.user)
        except (NotificationLog.DoesNotExist, ValueError, ValidationError):
            return Response({"detail": "Notification log record not found."}, status=status.HTTP_404_NOT_FOUND)

        status_val = request.data.get("status")
        if status_val != "DELIVERED":
            return Response(
                {"detail": "Invalid status value. Only 'DELIVERED' status update is permitted via this endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log.status = "DELIVERED"
        log.save()

        return Response({"success": True, "id": str(log.id), "status": "DELIVERED"}, status=status.HTTP_200_OK)


class NotificationSyncView(APIView):
    """
    [T017] 알림 델타 동기화 API 뷰
    - 앱 포그라운드 진입 시 로컬 캐시(IndexedDB)와 백엔드 이력을 대조하고 읽음 상태 등을 보정합니다.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        synced_at = timezone.now()
        queryset = NotificationLog.objects.filter(user=request.user).select_related("task")

        last_synced_at_str = request.query_params.get("last_synced_at")
        last_synced_at = None
        if last_synced_at_str:
            last_synced_at = parse_datetime(last_synced_at_str)

        if last_synced_at:
            queryset = queryset.filter(created_at__gt=last_synced_at)
        else:
            cutoff = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(created_at__gte=cutoff).order_by("-created_at")[:100]

        notifications_data = []
        for log in queryset:
            notifications_data.append(
                {
                    "id": str(log.id),
                    "title": log.task.title,
                    "body": log.task.body,
                    "status": log.status,
                    "created_at": log.created_at.isoformat(),
                }
            )

        return Response(
            {"synced_at": synced_at.isoformat(), "notifications": notifications_data}, status=status.HTTP_200_OK
        )

import logging

from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    백엔드 프레임워크 생존성(Liveness) 및 PostgreSQL DB 연결 건강성을 검증하는 진단 API.
    글로벌 IsAuthenticated 정책의 화이트리스트 예외 우회 제공 (AllowAny).
    """

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        django_status = "up"
        db_status = "down"
        error_msg = None
        response_status = status.HTTP_200_OK

        try:
            # PostgreSQL v18+ 연동 및 DB Liveness 핸드셰이크 정적 검사 (SELECT 1)
            connection = connections["default"]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = "up"
        except OperationalError as e:
            db_status = "down"
            error_msg = f"Database connection failed: {str(e)}"
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            logger.error(error_msg)
        except Exception as e:
            db_status = "down"
            error_msg = f"Unexpected health check error: {str(e)}"
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            logger.error(error_msg)

        response_data = {
            "status": "healthy" if db_status == "up" else "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "services": {"django": django_status, "database": db_status},
        }

        if error_msg:
            response_data["error"] = error_msg

        return Response(response_data, status=response_status)

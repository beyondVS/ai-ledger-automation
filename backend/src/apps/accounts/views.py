from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import UserRegisterSerializer

class UserRegisterView(generics.CreateAPIView):
    """
    [T011] 회원가입 API 뷰 (POST /api/auth/register/)
    - 인증 제한을 해제(AllowAny)하며, 단일 데이터베이스 트랜잭션 블록 내에서
      원자적으로 사용자 레코드가 생성되도록 보장합니다.
    """
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer

class UserLoginView(TokenObtainPairView):
    """
    [T016] 로그인 및 JWT 발급 API 뷰 (POST /api/auth/login/)
    - Custom UserLoginSerializer를 활용하여 이메일 식별자로 자격 증명을 검증합니다.
    """
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]


class UserLogoutView(APIView):
    """
    [T017] 로그아웃 API 뷰 (POST /api/auth/logout/)
    - 클라이언트로부터 전달받은 리프레시 토큰을 블랙리스트에 등록하여 세션을 무효화합니다.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


from rest_framework_simplejwt.views import TokenRefreshView

class UserTokenRefreshView(TokenRefreshView):
    """
    [T028] 토큰 리프레시 API 뷰 (POST /api/auth/refresh/)
    - 향후 토큰 갱신 정책 확장성을 위해 패키지 뷰를 상속하여 제공합니다.
    """
    permission_classes = [AllowAny]

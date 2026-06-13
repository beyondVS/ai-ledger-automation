from django.conf import settings
from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import UserLoginSerializer, UserRegisterSerializer


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


class UserLoginView(TokenObtainPairView):
    """
    [T016] 로그인 및 JWT 발급 API 뷰 (POST /api/auth/login/)
    - Custom UserLoginSerializer를 활용하여 이메일 식별자로 자격 증명을 검증합니다.
    - 리프레시 토큰은 XSS 공격 방지를 위해 httpOnly 쿠키로 주입하고, 바디에는 엑세스 토큰만 반환합니다.
    """

    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            refresh_token = response.data.pop("refresh", None)
            if refresh_token:
                # SameSite는 개발 환경의 http/cors 대응 및 1차 origin 통제를 위해 Lax 설정
                response.set_cookie(
                    key="refresh_token",
                    value=refresh_token,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite="Lax",
                    path="/api/auth/",
                )
        return response


class UserLogoutView(APIView):
    """
    [T017] 로그아웃 API 뷰 (POST /api/auth/logout/)
    - httpOnly 쿠키로부터 리프레시 토큰을 읽어 블랙리스트에 등록하고 세션을 무효화합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token") or request.data.get("refresh")
        response = Response(status=status.HTTP_205_RESET_CONTENT)
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass
        response.delete_cookie("refresh_token", path="/api/auth/")
        return response


class UserTokenRefreshView(TokenRefreshView):
    """
    [T028] 토큰 리프레시 API 뷰 (POST /api/auth/refresh/)
    - httpOnly 쿠키에서 리프레시 토큰을 조회하여 신규 엑세스 토큰을 발행합니다.
    - 토큰 로테이션 활성화 시 갱신된 리프레시 토큰을 쿠키로 재설정합니다.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            # SimpleJWT Serializer 가 request.data 에서 리프레시 토큰을 파싱하므로 주입
            request.data["refresh"] = refresh_token

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200 and "refresh" in response.data:
            new_refresh = response.data.pop("refresh")
            response.set_cookie(
                key="refresh_token",
                value=new_refresh,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                path="/api/auth/",
            )
        return response

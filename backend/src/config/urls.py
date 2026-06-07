from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # 사용자 인증 및 세션 API 연동
    path("api/auth/", include("apps.accounts.urls")),
    # 헬스 체크 API 엔드포인트 연동 (T007, T012)
    path("api/health/", include("apps.health.urls")),
    # [T007] 영수증 업로드 및 상태 조회 API 연동
    path("api/v1/ledgers/", include("apps.ledgers.urls")),
    path("api/v1/receipts/", include("apps.ledgers.urls")),  # 프론트엔드 receipts 호출 호환 추가
]

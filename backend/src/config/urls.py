from admin.views import (
    AdminTemplateHistoryView,
    AdminTemplateListView,
    AdminTemplateResetHealingView,
    MerchantTemplateVerifyView,
)
from apps.accounts.views import UserTimezoneUpdateView
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # 사용자 인증 및 세션 API 연동
    path("api/auth/", include("apps.accounts.urls")),
    # 사용자 타임존 환경설정 갱신 API 연동 (T010)
    path("api/v1/accounts/timezone/", UserTimezoneUpdateView.as_view(), name="user-timezone-update"),
    # 헬스 체크 API 엔드포인트 연동 (T007, T012)
    path("api/health/", include("apps.health.urls")),
    # [T007] 영수증 업로드 및 상태 조회 API 연동
    path("api/v1/ledgers/", include("apps.ledgers.urls")),
    path("api/v1/receipts/", include("apps.ledgers.urls")),  # 프론트엔드 receipts 호출 호환 추가
    # [T019] 어드민 가맹점 템플릿 수동 승인 API
    path(
        "api/admin/merchant-templates/<uuid:template_id>/verify/",
        MerchantTemplateVerifyView.as_view(),
        name="admin-merchant-template-verify",
    ),
    # 신규 어드민 가맹점 템플릿 제어 API 엔드포인트
    path(
        "api/admin/templates/",
        AdminTemplateListView.as_view(),
        name="admin-template-list",
    ),
    path(
        "api/admin/templates/<uuid:template_id>/history/",
        AdminTemplateHistoryView.as_view(),
        name="admin-template-history",
    ),
    path(
        "api/admin/templates/<uuid:template_id>/verify/",
        MerchantTemplateVerifyView.as_view(),
        name="admin-template-verify",
    ),
    path(
        "api/admin/templates/<uuid:template_id>/reset-healing/",
        AdminTemplateResetHealingView.as_view(),
        name="admin-template-reset-healing",
    ),
]

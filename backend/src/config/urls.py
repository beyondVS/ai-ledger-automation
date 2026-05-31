from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 헬스 체크 API 엔드포인트 연동 (T007, T012)
    path('api/health/', include('apps.health.urls')),
]

from apps.ledgers.views import (
    DashboardStatisticsView,
    LedgerCalendarView,
    LedgerIngestView,
    LedgerListView,
    MonthlyBudgetView,
    MyTemplateListView,
    ReceiptDetailView,
    ReceiptStatusView,
    ReceiptUploadView,
)
from django.urls import path

# app_name = "ledgers"

urlpatterns = [
    # [US1] 캘린더 뷰 전용 월별 지출 합산 및 건수 요약 집계 API
    path("calendar/", LedgerCalendarView.as_view(), name="ledger-calendar"),
    # [T023] 가계부 리스트 조회 API
    path("", LedgerListView.as_view(), name="ledger-list"),
    # [T011] 영수증 비동기 업로드 API
    path("upload/", ReceiptUploadView.as_view(), name="receipt-upload"),
    # [T007, T019] 영수증 비동기 호환 상태 조회 API
    path("status/<uuid:job_id>/", ReceiptStatusView.as_view(), name="receipt-status"),
    # [T012, T013] 영수증 비동기 상태 폴링 API
    path("jobs/<uuid:job_id>/", ReceiptStatusView.as_view(), name="receipt-job-status"),
    # [T005, T010, T017] 영수증 수동 수정(PATCH) 및 삭제(DELETE) API (UUID pk 매핑)
    path("<uuid:pk>/", ReceiptDetailView.as_view(), name="receipt-detail"),
    # [T008] [US1] 결제 데이터 인입 및 중복 방어 API
    path("ingest/", LedgerIngestView.as_view(), name="ledger-ingest"),
    # 일반 사용자용 내 가맹점 템플릿 관리 API
    path("my-templates/", MyTemplateListView.as_view(), name="my-template-list"),
    path("my-templates/<uuid:template_id>/", MyTemplateListView.as_view(), name="my-template-detail"),
    # [T009] 대시보드 통계 API
    path("dashboard/", DashboardStatisticsView.as_view(), name="dashboard-statistics"),
    # [T016] 월별 예산 API
    path("budgets/", MonthlyBudgetView.as_view(), name="monthly-budget-list"),
]

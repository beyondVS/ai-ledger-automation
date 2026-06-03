from apps.ledgers.views import LedgerListView, ReceiptStatusView, ReceiptUploadView
from django.urls import path

urlpatterns = [
    # [T023] 가계부 리스트 조회 API
    path("", LedgerListView.as_view(), name="ledger-list"),
    # [T007, T014] 영수증 동기 업로드 API
    path("upload/", ReceiptUploadView.as_view(), name="receipt-upload"),
    # [T007, T019] 영수증 비동기 호환 상태 조회 API
    path("status/<uuid:job_id>/", ReceiptStatusView.as_view(), name="receipt-status"),
]

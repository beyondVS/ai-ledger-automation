from django.urls import path
from apps.ledgers.views import ReceiptUploadView, ReceiptStatusView

urlpatterns = [
    # [T007, T014] 영수증 동기 업로드 API
    path('upload/', ReceiptUploadView.as_view(), name='receipt-upload'),
    # [T007, T019] 영수증 비동기 호환 상태 조회 API
    path('status/<uuid:job_id>/', ReceiptStatusView.as_view(), name='receipt-status'),
]

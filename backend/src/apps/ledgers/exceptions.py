from rest_framework import status
from rest_framework.exceptions import APIException


class PaymentIngestError(APIException):
    """결제 데이터 적재 관련 기본 예외"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Failed to ingest payment data."
    default_code = "payment_ingest_error"


class DuplicatePaymentError(PaymentIngestError):
    """중복 결제 요청 감지 시 발생하는 예외"""

    status_code = status.HTTP_200_OK
    default_detail = "Duplicate payment detected; bypassed without creating redundant records."
    default_code = "duplicate_payment_bypassed"


class TransactionRollbackError(PaymentIngestError):
    """품목 적재 실패 등으로 전체 트랜잭션이 롤백될 시 발생하는 예외"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Failed to ingest payment items. Whole transaction has been rolled back."
    default_code = "transaction_rollback"


class ItemValidationError(PaymentIngestError):
    """개별 품목에 대한 유효성 검사 실패 시 발생하는 예외"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation failed for one or more payment items."
    default_code = "item_validation_error"

import logging
import os

from apps.ledgers.models import ReceiptTask
from apps.ledgers.services import LedgerService
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

logger = logging.getLogger("apps.ledgers")
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def extract_receipt_task(self, task_id: str, file_path: str):
    """
    [T005] [US1] [US2] extract_receipt_task
    - ReceiptTask 모델을 활용하여 3단계 비동기 파이프라인 처리를 수행하는 Celery 태스크입니다.
    - 재시도 요건(최대 3회 지수 백오프) 및 DB 트랜잭션 롤백 정합성을 보장합니다.
    """
    logger.info(f"[Celery] Starting ReceiptTask for TaskID: {task_id}, File: {file_path}")

    # 1. 대상 작업 인스턴스 확인 및 PROCESSING 전이
    try:
        with transaction.atomic():
            task = ReceiptTask.objects.select_for_update().get(id=task_id)
            task.status = "PROCESSING"
            task.save()
            user = task.user
    except ReceiptTask.DoesNotExist:
        logger.error(f"[Celery] ReceiptTask {task_id} not found.")
        return

    # 2. 임시 파일 확인 및 서비스 호출
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"임시 영수증 파일을 찾을 수 없습니다: {file_path}")

        with open(file_path, "rb") as f:
            file_content = f.read()

        file_name = os.path.basename(file_path)
        content_type = "application/pdf" if file_name.lower().endswith(".pdf") else "image/jpeg"
        image_file = SimpleUploadedFile(file_name, file_content, content_type=content_type)

        # 3. 비동기 분석 서비스 실행
        service = LedgerService()
        res = service.ingest_receipt_task(user=user, image_file=image_file, existing_task=task)

        # 임시 파일 정리
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        if res and res.get("status") == "FAILED":
            logger.info(f"[Celery] ReceiptTask completed with failure: {task_id}")
            return res

        logger.info(f"[Celery] ReceiptTask completed successfully: {task_id}")

    except Exception as exc:
        logger.warning(f"[Celery] ReceiptTask failed: {task_id}. Reason: {str(exc)}")

        # 헌법 수호: 복구 불가능한 데이터 예외 감지 시 재시도를 즉시 스킵하고 FAILED 마킹
        from apps.ledgers.exceptions import DuplicatePaymentError
        from django.db import DataError, IntegrityError
        from pydantic import ValidationError

        unrecoverable_exceptions = (
            IntegrityError,
            DataError,
            DuplicatePaymentError,
            ValidationError,
            FileNotFoundError,
        )

        # 예외 체이닝의 근본 원인(cause)도 함께 추적 진단
        cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)

        is_unrecoverable = isinstance(exc, unrecoverable_exceptions) or (
            cause and isinstance(cause, unrecoverable_exceptions)
        )
        if not is_unrecoverable:
            exc_name = exc.__class__.__name__
            cause_name = cause.__class__.__name__ if cause else ""
            if exc_name in [
                "DataError",
                "ValidationError",
                "IntegrityError",
                "DuplicatePaymentError",
                "StringDataRightTruncation",
            ] or cause_name in [
                "DataError",
                "ValidationError",
                "IntegrityError",
                "DuplicatePaymentError",
                "StringDataRightTruncation",
            ]:
                is_unrecoverable = True

        # 복구 가능할 때만 지수 백오프 재시도 기동
        if not is_unrecoverable and self.request.retries < self.max_retries:
            countdown = (2**self.request.retries) * 2
            logger.info(f"[Celery] Retrying task in {countdown}s (Retry {self.request.retries + 1}/{self.max_retries})")
            try:
                with transaction.atomic():
                    task = ReceiptTask.objects.select_for_update().get(id=task_id)
                    task.status = "PENDING"
                    task.save()
            except Exception as db_err:
                logger.error(f"[Celery] Failed to restore task status: {str(db_err)}")

            raise self.retry(exc=exc, countdown=countdown, max_retries=self.max_retries) from exc

        # 재시도 소진 또는 복구 불가 오류 시 즉시 FAILED 처리 및 정리
        try:
            with transaction.atomic():
                task = ReceiptTask.objects.select_for_update().get(id=task_id)
                task.status = "FAILED"
                import traceback

                task.error_message = f"{str(exc)}\n{traceback.format_exc()[:500]}"
                task.save()
        except Exception as db_err:
            logger.error(f"[Celery] Failed to mark task as FAILED: {str(db_err)}")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        raise exc

import logging
import os

from apps.ledgers.models import ReceiptUploadJob
from apps.ledgers.services import LedgerService
from celery import shared_task
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=2)
def extract_receipt_text_task(self, job_id: str, file_path: str):
    """
    [T010] [US1] [US2] extract_receipt_text_task
    - 영수증 파일의 텍스트 추출 및 OCR 분석 처리를 수행하는 Celery 비동기 태스크입니다.
    - 헌법 및 기획 재시도 요건(최대 3회 지수 백오프) 및 원자적 DB 처리를 보장합니다.
    """
    logger.info(f"[Celery] Starting task for Job: {job_id}, File: {file_path}")

    # 1. 대상 작업 인스턴스 확인 및 PROCESSING 전이
    try:
        with transaction.atomic():
            job = ReceiptUploadJob.objects.select_for_update().get(id=job_id)
            job.status = "PROCESSING"
            job.save()
            user = job.user
    except ReceiptUploadJob.DoesNotExist:
        logger.error(f"[Celery] Job {job_id} not found.")
        return

    # 2. 업로드 임시 파일 로드 및 SimpleUploadedFile 래핑
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"임시 영수증 파일을 찾을 수 없습니다: {file_path}")

        with open(file_path, "rb") as f:
            file_content = f.read()

        file_name = os.path.basename(file_path)
        content_type = "application/pdf" if file_name.lower().endswith(".pdf") else "image/jpeg"
        # 2주차 레거시 파일명 시뮬레이션 바이패스 파싱 호환을 위해 원본 파일명 복원 적용 (경로 트래버스 방지 정제)
        orig_name = os.path.basename(job.raw_file_name) if job.raw_file_name else file_name
        image_file = SimpleUploadedFile(orig_name, file_content, content_type=content_type)

        # 3. 비동기 분석 및 적재 서비스 실행
        service = LedgerService()
        res = service.ingest_receipt(user=user, image_file=image_file, existing_job=job)

        # 성공/실패 여부와 무관하게 임시 파일 정리
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        if res and res.get("status") == "FAILED":
            logger.info(f"[Celery] Task completed with normal failure (e.g. duplicate) for Job: {job_id}")
            return res

        logger.info(f"[Celery] Task completed successfully for Job: {job_id}")

    except Exception as exc:
        logger.warning(f"[Celery] Task failed for Job: {job_id}. Reason: {str(exc)}")

        # 복구 가능한 임시 장애 상황 시 지수 백오프 재시도 적용 (최대 3회)
        if self.request.retries < self.max_retries:
            # 지수 백오프 시간 계산: 2^retries * 2 초 (2초, 4초, 8초)
            countdown = (2**self.request.retries) * 2
            logger.info(
                f"[Celery] Retrying task in {countdown} seconds (Retry {self.request.retries + 1}/{self.max_retries})"
            )
            # 재시도 대기 상태이므로 상태를 다시 PENDING으로 복구
            try:
                with transaction.atomic():
                    job = ReceiptUploadJob.objects.select_for_update().get(id=job_id)
                    job.status = "PENDING"
                    job.save()
            except Exception as db_err:
                logger.error(f"[Celery] Failed to restore status on retry: {str(db_err)}")

            raise self.retry(exc=exc, countdown=countdown, max_retries=self.max_retries) from exc

        # 재시도 횟수 소진 또는 복구 불가 오류 시 FAILED 영속화 및 파일 삭제
        try:
            with transaction.atomic():
                job = ReceiptUploadJob.objects.select_for_update().get(id=job_id)
                job.status = "FAILED"
                import traceback

                job.failure_reason = f"{str(exc)}\n{traceback.format_exc()[:500]}"
                job.save()
        except Exception as db_err:
            logger.error(f"[Celery] Failed to update job status to FAILED: {str(db_err)}")

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        raise exc

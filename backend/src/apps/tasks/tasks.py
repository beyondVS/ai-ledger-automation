import logging
import os

from apps.ledgers.models import ReceiptUploadJob
from apps.ledgers.services import LedgerService
from celery import shared_task
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from utils.llm_client import ReceiptLLMClient

logger = logging.getLogger(__name__)


def analyze_receipt_image_with_llm(llm_client, file_buffer, mime_type):
    """
    [T009] 테스트 코드의 Mock 패치 타겟 함수입니다.
    실제 운영 시에는 ReceiptLLMClient의 parse_receipt를 직접 호출해 영수증을 파싱합니다.
    """
    return llm_client.parse_receipt(file_buffer, mime_type=mime_type)


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
        # (analyze_receipt_image_with_llm 모킹 지원을 위해,
        #  LedgerService 내부 parse_receipt 부분을 태스크의 래퍼 메서드를 통하도록 모킹 분기 적용)
        service = LedgerService()

        # ReceiptLLMClient를 mock 함수를 거치도록 교체 패치하여 ingest_receipt를 호출합니다.
        service.llm_client.parse_receipt = lambda buf, mime_type: analyze_receipt_image_with_llm(
            ReceiptLLMClient(), buf, mime_type
        )

        service.ingest_receipt(user=user, image_file=image_file, existing_job=job)

        # 성공 시 임시 파일 정리
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        logger.info(f"[Celery] Task completed successfully for Job: {job_id}")

    except Exception as exc:
        logger.warning(f"[Celery] Task failed for Job: {job_id}. Reason: {str(exc)}")

        # 복구 가능한 임시 장애 상황 시 지수 백오프 재시도 적용 (최대 3회)
        # (IntegrityError 중복 제외하고 일반 예외 및 네트워크 관련에 대해 재시도)
        from django.db import IntegrityError

        if not isinstance(exc, IntegrityError) and self.request.retries < self.max_retries:
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
                # 상세 에러 로그 요약 기록
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

        # 중복 영수증 업로드 등으로 인한 IntegrityError는 시스템 비정상 크래시가 아닌
        # 비즈니스 기대 방어 동작이므로, 예외를 전파하지 않고 로깅 후 정상 종료합니다.
        if isinstance(exc, IntegrityError):
            logger.info(
                f"[Celery] Task resolved expected IntegrityError (Duplicate check). Job {job_id} marked as FAILED."
            )
            return {"status": "FAILED", "reason": "Duplicate transaction detected"}

        raise exc

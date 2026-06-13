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


@shared_task
def verify_proposed_regex_task(
    template_id: str, ocr_text: str, expected_date_raw: str, expected_amount: float, user_timezone: str = "Asia/Seoul"
):
    """
    [US1] verify_proposed_regex_task
    - LLM이 생성 제안한 정규식(date_pattern, amount_pattern)이 실제 영수증 원시 텍스트와 대조 시
      동일한 결과값(expected_date, expected_amount)을 캡처해내는지 비동기 정합성 검증을 수행합니다.
      대조 시 사용자의 고유 타임존 기준으로 안전하게 동일 정합 정규화를 수행합니다.
    - 검증 성공 시 is_auto_verified = True로 마킹하며, 실패 시 에러 사유를 남깁니다.
    """
    import re

    from apps.ledgers.models import MerchantTemplate
    from utils.bypass_parser import BypassParser

    logger.info(f"[Celery] Starting regex verification for template: {template_id}")

    try:
        template = MerchantTemplate.objects.get(id=template_id)
        rules = template.parsing_rules
        if not rules:
            raise ValueError("Template parsing_rules is empty")

        date_pattern = rules.get("date_pattern")
        amount_pattern = rules.get("amount_pattern")

        if not date_pattern or not amount_pattern:
            raise ValueError("Required patterns (date or amount) missing in rules")

        # 1. 결제 일시 매칭 검증
        date_match = re.search(date_pattern, ocr_text)
        if not date_match:
            raise ValueError(f"Date pattern failed to match raw text. Pattern: {date_pattern}")

        normalized_matched_date = BypassParser._normalize_datetime_string(date_match.group(0), user_timezone)
        expected_normalized = BypassParser._normalize_datetime_string(expected_date_raw, user_timezone)

        if normalized_matched_date != expected_normalized:
            raise ValueError(
                f"Date verification mismatch. Matched: {normalized_matched_date}, Expected: {expected_normalized}"
            )

        # 2. 결제 금액 매칭 검증
        amount_match = re.search(amount_pattern, ocr_text)
        if not amount_match:
            raise ValueError(f"Amount pattern failed to match raw text. Pattern: {amount_pattern}")

        raw_amount = amount_match.group(1) if len(amount_match.groups()) >= 1 else amount_match.group(0)
        cleaned_amount = re.sub(r"[^\d.]", "", raw_amount.replace(",", "").strip())
        matched_amount = float(cleaned_amount)

        if abs(matched_amount - expected_amount) > 0.01:
            raise ValueError(f"Amount verification mismatch. Matched: {matched_amount}, Expected: {expected_amount}")

        # 3. 모든 검증 성공 시 auto_verified 반영
        template.is_auto_verified = True
        template.regex_error_message = None
        template.save()
        logger.info(f"[Celery] Regex verification SUCCESS for template: {template_id}")

    except Exception as e:
        logger.warning(f"[Celery] Regex verification FAILED for template: {template_id}. Reason: {str(e)}")
        try:
            template = MerchantTemplate.objects.get(id=template_id)
            template.is_auto_verified = False
            template.regex_error_message = str(e)
            template.save()
        except Exception as db_err:
            logger.error(f"[Celery] Failed to update verification failure to DB: {str(db_err)}")

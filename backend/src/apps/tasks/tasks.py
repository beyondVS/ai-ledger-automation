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


@shared_task
def self_heal_template_task(template_id: str, ledger_id: str, corrected_diff: list, ocr_text: str = None):
    """
    [T016, T017] self_heal_template_task
    - 수동 정정된 데이터(corrected_diff) 혹은 에러가 발생한 영수증에 대해,
      Gemini API를 호출하여 보다 정밀한 새로운 정규식(parsing_rules)을 생성합니다.
    - 생성된 정규식이 현재 Ledger 데이터(Ground Truth)를 정확히 추출해내는지 로컬 RegexParser 검증을 거칩니다.
    - 검증 성공 시 템플릿의 parsing_rules를 업데이트하고 복원합니다.
    - 자가 치유 시도 횟수가 3회에 도달하거나 초과하면 is_blacklisted = True 로 격리 처리합니다.
    """
    import re

    from apps.ledgers.models import Ledger, MerchantTemplate
    from django.conf import settings
    from django.utils import timezone
    from pydantic import BaseModel, Field
    from utils.bypass_parser import BypassParser
    from utils.llm_client import ReceiptLLMClient

    logger.info(f"[Celery] Starting self-healing for template {template_id}")

    try:
        template = MerchantTemplate.objects.get(id=template_id)
        ledger = Ledger.objects.get(id=ledger_id)
    except (MerchantTemplate.DoesNotExist, Ledger.DoesNotExist) as e:
        logger.error(f"[Celery] Template or Ledger not found: {str(e)}")
        return False

    # 이미 블랙리스트 상태인 경우 자가치유 차단
    if template.is_blacklisted:
        logger.warning(f"[Celery] Template {template_id} is blacklisted. Skipping self-healing.")
        return False

    # 1. OCR 텍스트가 없는 경우 모의 OCR 텍스트 생성
    if not ocr_text:
        ocr_text = (
            f"상호: {ledger.vendor_name}\n"
            f"사업자번호: {ledger.vendor_registration_number}\n"
            f"일시: {ledger.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"합계: {int(ledger.total_amount)}원\n"
        )

    # 2. LLM 호출을 위한 프롬프트 및 스키마 구성
    class HealingSchema(BaseModel):
        proposed_date_pattern: str = Field(description="가장 정확하게 결제 일시를 캡처할 수 있는 정적 정규식 패턴")
        proposed_amount_pattern: str = Field(description="가장 정확하게 총 결제 금액을 캡처할 수 있는 정적 정규식 패턴")

    prompt = f"""
    당신은 영수증 정규식 패턴 수정 전문가입니다.
    대상 가맹점의 영수증 원시 텍스트와 현재 오작동하여 수동 정정이 발생한 내역을 분석하여,
    추후 LLM 없이 로컬에서 정확히 값을 추출할 수 있도록 개선된 정규식 패턴을 생성해주세요.

    [영수증 원시 텍스트 (OCR Text)]
    {ocr_text}

    [기존 정규식 패턴]
    - 날짜 패턴: {template.parsing_rules.get("date_pattern", "")}
    - 금액 패턴: {template.parsing_rules.get("amount_pattern", "")}

    [사용자 수동 정정/에러 내역 (Diff)]
    {corrected_diff}

    [기대하는 올바른 추출 결과 (Ground Truth)]
    - 기대 날짜: {ledger.transaction_date.strftime("%Y-%m-%dT%H:%M:%S")}
    - 기대 금액: {ledger.total_amount}

    [지침]
    1. 사용자가 수정한 내용(Diff)을 반영하여, 해당 날짜와 금액이 영수증 텍스트로부터 정확히 추출되도록 정규식 패턴을 수정해야 합니다.
    2. 정규식 패턴은 파이썬 `re.search` 로 매칭 시 타겟 값이 그룹 1 또는 전체 매치(group 0)에 캡처될 수 있어야 합니다.
       - 날짜 패턴은 '{ledger.transaction_date.strftime("%Y-%m-%d")}' 또는 영수증 텍스트 내의 실제 일시 형식을 정확하게 캡처해야 합니다.
       - 금액 패턴은 쉼표를 포함한 숫자(예: '{int(ledger.total_amount)}')를 정확하게 캡처해야 합니다.
    """

    try:
        client = ReceiptLLMClient()
        gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
        is_ollama_target = not (gemini_enabled and gemini_api_key)
        target_model = "receipt-analyzer" if not is_ollama_target else "ollama-fallback"

        messages = [{"role": "user", "content": prompt}]

        logger.info(f"[Celery] Requesting self-healing rules to LLM ({target_model})...")
        response = client.router.completion(
            model=target_model,
            messages=messages,
            response_format=HealingSchema,
            temperature=0.1,
        )

        response_text = response.choices[0].message.content
        if not response_text:
            raise ValueError("LLM returned empty response for self-healing")

        healed_data = HealingSchema.model_validate_json(response_text)
        new_date_pattern = healed_data.proposed_date_pattern
        new_amount_pattern = healed_data.proposed_amount_pattern

        logger.info(f"[Celery] Proposed healed patterns: date='{new_date_pattern}', amount='{new_amount_pattern}'")

        # 3. 로컬 RegexParser 정합성 검증
        # 3-1. 날짜 패턴 검증
        date_match = re.search(new_date_pattern, ocr_text)
        if not date_match:
            raise ValueError(f"New date pattern failed to match OCR text. Pattern: {new_date_pattern}")

        normalized_date = BypassParser._normalize_datetime_string(date_match.group(0), ledger.user.timezone)
        expected_normalized = BypassParser._normalize_datetime_string(
            ledger.transaction_date.isoformat(), ledger.user.timezone
        )
        if normalized_date != expected_normalized:
            raise ValueError(
                f"New date pattern normalized result mismatch. Matched: {normalized_date}, Expected: {expected_normalized}"
            )

        # 3-2. 금액 패턴 검증
        amount_match = re.search(new_amount_pattern, ocr_text)
        if not amount_match:
            raise ValueError(f"New amount pattern failed to match OCR text. Pattern: {new_amount_pattern}")

        raw_amount = amount_match.group(1) if len(amount_match.groups()) >= 1 else amount_match.group(0)
        cleaned_amount = re.sub(r"[^\d.]", "", raw_amount.replace(",", "").strip())
        matched_amount = float(cleaned_amount)

        if abs(matched_amount - float(ledger.total_amount)) > 0.01:
            raise ValueError(
                f"New amount pattern value mismatch. Matched: {matched_amount}, Expected: {ledger.total_amount}"
            )

        # 4. 검증 성공 시 템플릿 업데이트 및 복원
        with transaction.atomic():
            t_obj = MerchantTemplate.objects.select_for_update().get(id=template.id)
            t_obj.parsing_rules["date_pattern"] = new_date_pattern
            t_obj.parsing_rules["amount_pattern"] = new_amount_pattern
            t_obj.is_auto_verified = True
            t_obj.is_verified = True
            t_obj.self_healing_attempts = 0
            t_obj.last_healing_at = timezone.now()
            t_obj.save()

        logger.info(f"[Celery] Self-healing SUCCESS for template {template_id}")
        return True

    except Exception as e:
        logger.warning(f"[Celery] Self-healing FAILED for template {template_id}. Reason: {str(e)}")
        # 실패 횟수 누적 및 3회 초과 시 블랙리스트 처리
        with transaction.atomic():
            t_obj = MerchantTemplate.objects.select_for_update().get(id=template.id)
            t_obj.is_auto_verified = False
            t_obj.regex_error_message = str(e)
            # demote_template가 이미 증가시켰을 수도 있으나, 자가치유 비동기 검증 도중 실패하면 여기서도 누적하여 격리 수호
            t_obj.self_healing_attempts += 1
            if t_obj.self_healing_attempts >= 3:
                t_obj.is_blacklisted = True
            t_obj.save()
        return False

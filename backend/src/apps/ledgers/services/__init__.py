import datetime
import json
import logging
import traceback

from apps.accounts.models import User
from apps.ledgers.exceptions import DuplicatePaymentError
from apps.ledgers.models import Ledger, LedgerItem
from apps.tasks.models import FailedTask
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .payment import ingest_payment_data as ingest_payment_data
from .reporter import ReceiptLoadTestReporter as ReceiptLoadTestReporter

logger = logging.getLogger(__name__)


from utils.llm_client import ReceiptSchema


def _normalize_datetime_string(datetime_str: str, user_timezone: str = "Asia/Seoul") -> str:
    """
    '2026년 6월 11일 오후 3:45' 또는 '2026-06-11' 등의 포맷을
    사용자의 타임존을 기반으로 한 UTC 기준의 ISO 8601 포맷('YYYY-MM-DDTHH:MM:SZ')으로 정규화합니다.
    """
    import datetime
    import re
    from zoneinfo import ZoneInfo

    from django.utils import timezone

    datetime_str = datetime_str.strip()

    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        tz = ZoneInfo("Asia/Seoul")

    # 이미 정상적인 ISO 8601 형식이고 UTC 'Z'가 있으면 파싱 없이 즉시 반환
    if datetime_str.endswith("Z"):
        try:
            parsed_dt = datetime.datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            return parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    # 1. 날짜 정보 추출 (년-월-일)
    year, month, day = None, None, None
    date_match = re.search(r"(\d{4})[-년./]\s*(\d{1,2})[-월./]\s*(\d{1,2})", datetime_str)
    if date_match:
        year, month, day = map(int, date_match.groups())
    else:
        now = timezone.now().astimezone(tz)
        year, month, day = now.year, now.month, now.day

    # 2. 시간 정보 추출 (오전/오후 시:분 또는 HH:MM)
    hour, minute, second = 0, 0, 0

    # 2-1. '오전/오후 시:분' 판독
    time_match = re.search(r"(오전|오후)\s*(\d{1,2}):(\d{2})", datetime_str)
    if time_match:
        period, hour_str, min_str = time_match.groups()
        hour = int(hour_str)
        minute = int(min_str)
        if period == "오후" and hour < 12:
            hour += 12
        elif period == "오전" and hour == 12:
            hour = 0
    else:
        # 2-2. 'HH:MM' 또는 'HH:MM:SS' 판독
        time_match = re.search(r"(\d{2}):(\d{2})(?::(\d{2}))?", datetime_str)
        if time_match:
            hour_str, min_str, sec_str = time_match.groups()
            hour = int(hour_str)
            minute = int(min_str)
            second = int(sec_str) if sec_str else 0

    # 3. Naive 시각 구성 후 사용자 타임존 주입
    local_dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=tz)

    # 4. UTC 변환 및 포맷 반환
    utc_dt = local_dt.astimezone(datetime.UTC)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_ledger_transactional(
    user_id: str,
    receipt_data: ReceiptSchema,
    user_timezone: str = "Asia/Seoul",
    raw_llm_response: dict = None,
    raw_text_hash: str = None,
) -> dict:
    """
    [T011, T015] create_ledger_transactional 서비스 함수
    - Ledger 마스터 레코드와 LedgerItem 상세 배열을 단일 원자적 데이터베이스 트랜잭션 세션 내에서 일괄 생성합니다.
    - 데이터 적재 도중 예외나 데이터베이스 연결 장해 등 오류 발생 시 전역 롤백을 수행하여 파편화를 기계적으로 방지합니다.
    - UNIQUE 제약조건 위배(IntegrityError) 발생 시, 작업을 큐의 낭비 없이 강제 중단하고
      FailedTask 모델에 입력 페이로드와 에러 콜스택을 안전 격리 적재(DLQ)합니다.
    """

    if isinstance(receipt_data, dict):
        # 하위 호환성 지원: 3번째 인자로 items_data(list)가 들어왔을 경우 DTO 합성 처리
        if "items" not in receipt_data and isinstance(user_timezone, list):
            items_list = user_timezone
            user_timezone = "Asia/Seoul"
            receipt_data["items"] = items_list
        if "category" not in receipt_data:
            receipt_data["category"] = "미분류"
        receipt_data = ReceiptSchema(**receipt_data)

    try:
        with transaction.atomic():
            # 1. 연관 사용자(User) 존재 여부 확보
            user = User.objects.get(id=user_id)

            # 날짜 파싱 및 타임존 맞추기 보강
            utc_str = _normalize_datetime_string(receipt_data.transaction_date, user_timezone)
            tx_datetime = datetime.datetime.fromisoformat(utc_str.replace("Z", "+00:00"))

            if settings.USE_TZ and timezone.is_naive(tx_datetime):
                tx_datetime = timezone.make_aware(tx_datetime)
            elif not settings.USE_TZ and timezone.is_aware(tx_datetime):
                tx_datetime = timezone.make_naive(tx_datetime)

            # 1-1. 사전 중복 체크 (Exists 쿼리)
            vendor_reg_num = receipt_data.vendor_registration_number
            if not vendor_reg_num or vendor_reg_num.strip() == "":
                vendor_reg_num = "0000000000"

            total_amount = receipt_data.total_amount
            supply_value = round(total_amount / 1.1, 2)
            vat_amount = round(total_amount - supply_value, 2)

            if Ledger.objects.filter(
                user=user,
                vendor_registration_number=vendor_reg_num,
                transaction_date=tx_datetime,
                total_amount=total_amount,
            ).exists():
                raise DuplicatePaymentError(detail="이미 등록된 중복 영수증입니다.")

            # 2. Ledger 마스터 레코드 삽입
            # (vendor_registration_number가 공백이거나 누락된 상태일 경우, 모델 내 save() 필터에 의해 '0000000000' 자동 치환 적재)
            ledger = Ledger.objects.create(
                user=user,
                vendor_registration_number=vendor_reg_num,
                vendor_name=receipt_data.vendor_name,
                transaction_date=tx_datetime,
                total_amount=total_amount,
                supply_value=supply_value,
                vat_amount=vat_amount,
                category=receipt_data.category or "미분류",
                raw_llm_response=raw_llm_response,
                approval_number=receipt_data.approval_number,
                order_id=receipt_data.order_id,
                raw_text_hash=raw_text_hash,
                ignore_duplicate_check=False,
            )

            # 3. LedgerItem 상세 자식 레코드 벌크(bulk_create) 삽입
            ledger_items = []
            for item in receipt_data.items:
                ledger_items.append(
                    LedgerItem(
                        ledger=ledger,
                        item_name=item.item_name,
                        quantity=item.quantity or 1,
                        unit_price=item.unit_price,
                        total_price=item.total_price,
                    )
                )

            LedgerItem.objects.bulk_create(ledger_items)

            return {"status": "SUCCESS", "ledger_id": str(ledger.id), "items_count": len(ledger_items)}

    except DuplicatePaymentError as dpe:
        # 사전 중복 체크로 검출된 비즈니스 예외 처리 (FailedTask에 격리 적재 후 재전파)
        raw_payload_dict = {
            "user_id": user_id,
            "receipt_data": receipt_data.model_dump(),
            "ledger_data": receipt_data.model_dump(),
            "items_data": [item.model_dump() for item in receipt_data.items],
        }
        FailedTask.objects.create(
            user=user if "user" in locals() else None,
            task_type="API_LEDGER_INGEST_DUPLICATE",
            raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
            error_message=str(dpe),
            error_stacktrace=traceback.format_exc(),
        )
        raise dpe

    except IntegrityError as ie:
        # 중복 영수증 유입 또는 고유성 위배 발생 시 Dead Letter Queue 격리 적재 분기 실행
        raw_payload_dict = {
            "user_id": user_id,
            "receipt_data": receipt_data.model_dump(),
            "ledger_data": receipt_data.model_dump(),
            "items_data": [item.model_dump() for item in receipt_data.items],
        }

        # 동시성 이슈로 DB 레벨에서 고유성 위배가 난 경우 DuplicatePaymentError로 변환하여 전파
        if "unique_ledger_transaction" in str(ie).lower():
            FailedTask.objects.create(
                user=user if "user" in locals() else None,
                task_type="API_LEDGER_INGEST_DUPLICATE",
                raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
                error_message=str(ie),
                error_stacktrace=traceback.format_exc(),
            )
            raise DuplicatePaymentError(detail="이미 등록된 중복 영수증입니다.") from ie

        FailedTask.objects.create(
            user=user if "user" in locals() else None,
            task_type="API_LEDGER_INGEST_SYSTEM_ERROR",
            raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
            error_message=str(ie),
            error_stacktrace=traceback.format_exc(),
        )
        # 상위 라우터나 Celery 태스크에서 처리할 수 있도록 예외 재전파
        raise ie

    except Exception as e:
        # 데이터베이스 강제 단절 등 예기치 않은 시스템 장해 발생 시 전격 자동 롤백 및 에러 적재
        raw_payload_dict = {
            "user_id": user_id,
            "receipt_data": receipt_data.model_dump(),
            "ledger_data": receipt_data.model_dump(),
            "items_data": [item.model_dump() for item in receipt_data.items],
        }

        FailedTask.objects.create(
            user=user if "user" in locals() else None,
            task_type="API_LEDGER_INGEST_SYSTEM_ERROR",
            raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
            error_message=str(e),
            error_stacktrace=traceback.format_exc(),
        )
        raise e


class LedgerService:
    """
    [T015] [US1] 가계부 인제션 통합 서비스 클래스
    - WebP 이미지 변환, Gemini API 파싱, bypass 파싱 처리 후 데이터베이스 적재 트랜잭션을 일괄 통제합니다.
    """

    def __init__(self):
        from utils.llm_client import ReceiptLLMClient

        self.llm_client = ReceiptLLMClient()

    def ingest_receipt_task(self, user, image_file, existing_task=None):
        import re

        from apps.ledgers.exceptions import DuplicatePaymentError
        from apps.ledgers.models import Ledger, ReceiptTask
        from apps.ledgers.services.ocr import extract_text_from_image, extract_text_from_pdf
        from utils.image_processor import ImageProcessor

        raw_ocr_text = ""

        # 1. 작업 추적 Task 생성 또는 기존 Task 사용
        if existing_task:
            task = existing_task
        else:
            task = ReceiptTask.objects.create(
                user=user, status="PENDING", file_name=getattr(image_file, "name", "unknown_receipt.jpg"), file_path=""
            )

        task.status = "PROCESSING"
        task.save()

        try:
            parsed_data = None
            file_name = getattr(image_file, "name", "").lower()
            is_pdf = file_name.endswith(".pdf")
            stage = "NONE"

            # ----------------------------------------------------
            # 1단계: Local OCR + 로컬 Ollama 파싱
            # ----------------------------------------------------
            if is_pdf:
                raw_ocr_text = extract_text_from_pdf(image_file)
            else:
                raw_ocr_text = extract_text_from_image(image_file)

            if raw_ocr_text and raw_ocr_text.strip():
                logger.info("1단계: 로컬 OCR 텍스트 확보 성공, Ollama 파싱을 시도합니다.")
                try:
                    parsed_data = self.llm_client.parse_receipt_local(raw_ocr_text)
                    if parsed_data:
                        stage = "OLLAMA"
                except Exception as ollama_err:
                    logger.warning(f"Ollama parsing exception, falling back: {str(ollama_err)}")
                    parsed_data = None

            if not parsed_data:
                # ----------------------------------------------------
                # 2단계: Cloud Text-only Fallback
                # ----------------------------------------------------
                if raw_ocr_text and raw_ocr_text.strip():
                    logger.info("2단계: 1단계 실패로 인해 Gemini Text-only 폴백을 시도합니다.")
                    parsed_data = self.llm_client.parse_receipt_cloud_text(raw_ocr_text)
                    if parsed_data:
                        stage = "GEMINI_TEXT"

            # 1단계 혹은 2단계 파싱 성공 시 DB 적재 및 종료
            if parsed_data:
                logger.info(f"1/2단계 텍스트 파싱 성공 ({stage}). DB 적재를 시작합니다.")
                raw_biz_num = parsed_data.vendor_registration_number
                clean_biz_num = re.sub(r"\D", "", str(raw_biz_num))[:10]
                parsed_data.vendor_registration_number = clean_biz_num or "0000000000"

                import hashlib

                raw_text_hash = hashlib.sha256(raw_ocr_text.encode("utf-8")).hexdigest() if raw_ocr_text else None

                res = create_ledger_transactional(
                    user_id=str(user.id),
                    receipt_data=parsed_data,
                    user_timezone=user.timezone,
                    raw_llm_response=parsed_data.model_dump(),
                    raw_text_hash=raw_text_hash,
                )

                ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])
                task.ledger = ledger
                task.status = "COMPLETED"
                task.parser_stage = stage
                task.save()

                return {"status": "COMPLETED", "task_id": str(task.id), "ledger": ledger}

            # ----------------------------------------------------
            # 3단계: Cloud Vision Fallback
            # ----------------------------------------------------
            logger.info("1/2단계 파싱 실패. 3단계 Gemini Vision 폴백을 시도합니다.")
            if is_pdf:
                import io

                image_file.seek(0)
                file_buffer = io.BytesIO(image_file.read())
                mime_type = "application/pdf"
            else:
                file_buffer = ImageProcessor.process_image_to_webp(image_file, quality=80)
                mime_type = "image/webp"

            parsed_data = self.llm_client.parse_receipt_cloud_vision(file_buffer, mime_type=mime_type)
            if not parsed_data:
                raise ValueError("Gemini Vision API 영수증 분석 결과 획득 실패")

            stage = "GEMINI_VISION"
            raw_biz_num = parsed_data.vendor_registration_number
            clean_biz_num = re.sub(r"\D", "", str(raw_biz_num))[:10]
            parsed_data.vendor_registration_number = clean_biz_num or "0000000000"

            import hashlib

            file_buffer.seek(0)
            raw_text_hash = hashlib.sha256(file_buffer.read()).hexdigest()

            res = create_ledger_transactional(
                user_id=str(user.id),
                receipt_data=parsed_data,
                user_timezone=user.timezone,
                raw_llm_response=parsed_data.model_dump(),
                raw_text_hash=raw_text_hash,
            )

            ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])
            task.ledger = ledger
            task.status = "COMPLETED"
            task.parser_stage = stage
            task.save()

            return {"status": "COMPLETED", "task_id": str(task.id), "ledger": ledger}

        except DuplicatePaymentError as dpe:
            logger.info(f"ingest_receipt_task duplicate error: {str(dpe)}")
            task.status = "FAILED"
            task.error_message = "이미 등록된 중복 영수증입니다."
            task.save()
            return {"status": "FAILED", "reason": "Duplicate transaction detected"}

        except IntegrityError as ie:
            logger.warning(f"ingest_receipt_task integrity error: {str(ie)}")
            task.status = "FAILED"
            task.error_message = f"IntegrityError: {str(ie)}"
            task.save()
            raise ie

        except Exception as e:
            logger.error(f"ingest_receipt_task system error: {str(e)}", exc_info=True)
            task.status = "FAILED"
            import traceback

            task.error_message = f"{str(e)}\n{traceback.format_exc()[:500]}"
            task.save()
            raise ValueError("영수증 이미지 분석 또는 데이터 파싱에 실패했습니다.") from e

    def ingest_receipt(self, user, image_file, existing_job=None):
        import re

        from apps.ledgers.exceptions import DuplicatePaymentError
        from apps.ledgers.models import Ledger, ReceiptUploadJob
        from apps.ledgers.services.ocr import extract_text_from_image, extract_text_from_pdf
        from utils.image_processor import ImageProcessor

        raw_ocr_text = ""

        # 1. 작업 추적 Job 생성 또는 기존 Job 재사용
        if existing_job:
            job = existing_job
            if getattr(image_file, "name", None):
                job.raw_file_name = image_file.name
                job.save()
        else:
            job = ReceiptUploadJob.objects.create(
                user=user, status="PENDING", raw_file_name=getattr(image_file, "name", "unknown_receipt.jpg")
            )

        job.status = "PROCESSING"
        job.save()

        try:
            parsed_data = None
            file_name = getattr(image_file, "name", "").lower()
            is_pdf = file_name.endswith(".pdf")

            # ----------------------------------------------------
            # 1단계: Local OCR + 로컬 Ollama 파싱
            # ----------------------------------------------------
            # 1-1. OCR 텍스트 추출
            if is_pdf:
                raw_ocr_text = extract_text_from_pdf(image_file)
            else:
                raw_ocr_text = extract_text_from_image(image_file)

            # 1-2. 텍스트가 확보된 경우 로컬 Ollama 파싱 시도
            if raw_ocr_text and raw_ocr_text.strip():
                logger.info("1단계: 로컬 OCR 텍스트 확보 성공, Ollama 파싱을 시도합니다.")
                parsed_data = self.llm_client.parse_receipt_local(raw_ocr_text)

            # 1-3. 로컬 Ollama 파싱 성공 시 DB 적재 및 종료
            if parsed_data:
                logger.info("1단계 로컬 Ollama 파싱 성공. DB 적재를 시작합니다.")
            else:
                # ----------------------------------------------------
                # 2단계: Cloud Text-only Fallback
                # ----------------------------------------------------
                if raw_ocr_text and raw_ocr_text.strip():
                    logger.info("2단계: 1단계 실패로 인해 Gemini Text-only 폴백을 시도합니다.")
                    parsed_data = self.llm_client.parse_receipt_cloud_text(raw_ocr_text)

            # 1단계 혹은 2단계 파싱 성공 시 DB 적재 및 종료
            if parsed_data:
                logger.info("1/2단계 텍스트 파싱 성공. DB 적재를 시작합니다.")
                raw_biz_num = parsed_data.vendor_registration_number
                clean_biz_num = re.sub(r"\D", "", str(raw_biz_num))[:10]
                parsed_data.vendor_registration_number = clean_biz_num or "0000000000"

                import hashlib

                raw_text_hash = hashlib.sha256(raw_ocr_text.encode("utf-8")).hexdigest() if raw_ocr_text else None

                res = create_ledger_transactional(
                    user_id=str(user.id),
                    receipt_data=parsed_data,
                    user_timezone=user.timezone,
                    raw_llm_response=parsed_data.model_dump(),
                    raw_text_hash=raw_text_hash,
                )

                ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])
                job.ledger = ledger
                job.status = "COMPLETED"
                job.save()

                return {"status": "COMPLETED", "job_id": None, "ledger": ledger}

            # ----------------------------------------------------
            # 1/2단계 모두 실패 시 3단계 Gemini Vision 폴백 가동
            # ----------------------------------------------------
            logger.info("1/2단계 파싱 실패 또는 텍스트 없음. 3단계 Gemini Vision 폴백을 시도합니다.")
            if is_pdf:
                import io

                image_file.seek(0)
                file_buffer = io.BytesIO(image_file.read())
                mime_type = "application/pdf"
            else:
                file_buffer = ImageProcessor.process_image_to_webp(image_file, quality=80)
                mime_type = "image/webp"

            parsed_data = self.llm_client.parse_receipt_cloud_vision(file_buffer, mime_type=mime_type)

            if not parsed_data:
                raise ValueError("Gemini Vision API 영수증 분석 결과 획득 실패")

            raw_biz_num = parsed_data.vendor_registration_number
            clean_biz_num = re.sub(r"\D", "", str(raw_biz_num))[:10]
            parsed_data.vendor_registration_number = clean_biz_num or "0000000000"

            import hashlib

            file_buffer.seek(0)
            raw_text_hash = hashlib.sha256(file_buffer.read()).hexdigest()

            res = create_ledger_transactional(
                user_id=str(user.id),
                receipt_data=parsed_data,
                user_timezone=user.timezone,
                raw_llm_response=parsed_data.model_dump(),
                raw_text_hash=raw_text_hash,
            )

            ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])
            job.ledger = ledger
            job.status = "COMPLETED"
            job.save()

            return {"status": "COMPLETED", "job_id": None, "ledger": ledger}

        except DuplicatePaymentError as dpe:
            logger.info(f"ingest_receipt duplicate error (bypassed without raise): {str(dpe)}")
            job.status = "FAILED"
            job.failure_reason = "이미 등록된 중복 영수증입니다."
            job.save()
            return {"status": "FAILED", "reason": "Duplicate transaction detected"}

        except IntegrityError as ie:
            logger.warning(f"ingest_receipt integrity error: {str(ie)}")
            job.status = "FAILED"
            job.save()
            raise ie

        except Exception as e:
            logger.error(f"ingest_receipt system error: {str(e)}", exc_info=True)
            job.status = "FAILED"
            job.save()
            raise ValueError("영수증 이미지 분석 또는 데이터 파싱에 실패했습니다.") from e

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

logger = logging.getLogger(__name__)


from utils.bypass_parser import BypassParser
from utils.llm_client import ReceiptSchema


def create_ledger_transactional(
    user_id: str, receipt_data: ReceiptSchema, user_timezone: str = "Asia/Seoul", raw_llm_response: dict = None
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
            utc_str = BypassParser._normalize_datetime_string(receipt_data.transaction_date, user_timezone)
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

    def ingest_receipt(self, user, image_file, existing_job=None):
        import re

        from apps.ledgers.models import Ledger, ReceiptUploadJob
        from utils.bypass_parser import BypassParser
        from utils.image_processor import ImageProcessor

        raw_ocr_text = None

        # 1. 3주차 호환 작업 추적 Job 생성 또는 기존 Job 재사용
        if existing_job:
            job = existing_job
            if getattr(image_file, "name", None):
                job.raw_file_name = image_file.name
                job.save()
        else:
            job = ReceiptUploadJob.objects.create(
                user=user, status="PENDING", raw_file_name=getattr(image_file, "name", "unknown_receipt.jpg")
            )

        try:
            parsed_data = None
            used_bypass = False
            file_name = getattr(image_file, "name", "").lower()

            # 0. PDF인 경우 선행적으로 내부 텍스트 추출 수행 (바이패스용 raw_ocr_text 확보)
            if file_name.endswith(".pdf"):
                try:
                    import fitz

                    image_file.seek(0)
                    pdf_bytes = image_file.read()
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    extracted_text = ""
                    for page in doc:
                        extracted_text += page.get_text()
                    if extracted_text.strip():
                        raw_ocr_text = extracted_text
                except Exception as pdf_err:
                    logger.warning(f"PDF 텍스트 추출 중 에러 발생: {str(pdf_err)}")
            else:
                try:
                    import pytesseract
                    from PIL import Image

                    image_file.seek(0)
                    img = Image.open(image_file)
                    extracted_text = pytesseract.image_to_string(img, lang="kor+eng")
                    if extracted_text and extracted_text.strip():
                        raw_ocr_text = extracted_text
                except Exception as img_err:
                    logger.warning(f"이미지 OCR 텍스트 추출 중 에러 발생 (Tesseract 미설치 시 무시됨): {str(img_err)}")

            # 2. 1차 로컬 바이패스 파싱 시도 (OCR 텍스트 및 10자리 사업자등록번호 감지 시)
            if raw_ocr_text:
                biz_num_match = re.search(r"\d{10}", raw_ocr_text.replace("-", ""))
                if biz_num_match:
                    biz_num = biz_num_match.group(0)
                    parsed_data = BypassParser.try_bypass_parsing(raw_ocr_text, biz_num, user_timezone=user.timezone)
                    if parsed_data:
                        used_bypass = True

            # 3. 로컬 바이패스 실패 시 2차 Pillow WebP 이미지 변환 및 Gemini API 폴백 가동
            if not parsed_data:
                if file_name.endswith(".pdf"):
                    import io

                    image_file.seek(0)
                    pdf_buffer = io.BytesIO(image_file.read())
                    parsed_data = self.llm_client.parse_receipt(pdf_buffer, mime_type="application/pdf")
                else:
                    webp_buffer = ImageProcessor.process_image_to_webp(image_file, quality=80)
                    parsed_data = self.llm_client.parse_receipt(webp_buffer, mime_type="image/webp")

                if not parsed_data:
                    raise ValueError("Gemini API 영수증 분석 결과 획득 실패")

            if isinstance(parsed_data, dict):
                parsed_data = ReceiptSchema(**parsed_data)

            # 5. 원자적 트랜잭션 함수 호출 (안전한 적재 및 롤백 보장)
            raw_biz_num = parsed_data.vendor_registration_number
            clean_biz_num = re.sub(r"\D", "", str(raw_biz_num))[:10]
            parsed_data.vendor_registration_number = clean_biz_num or "0000000000"

            res = create_ledger_transactional(
                user_id=str(user.id),
                receipt_data=parsed_data,
                user_timezone=user.timezone,
                raw_llm_response=parsed_data.model_dump() if not used_bypass else None,
            )

            # 6. 생성 완료 인스턴스 로드 및 작업 상태 반영
            ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])
            job.ledger = ledger
            job.status = "COMPLETED"
            job.save()

            # 7. 신규 가맹점 캐시 템플릿 자동 제안 등록 (Bypass 미적용 시)
            if not used_bypass:
                template = BypassParser.propose_new_template(
                    vendor_registration_number=parsed_data.vendor_registration_number,
                    vendor_name=parsed_data.vendor_name,
                    parsed_data=parsed_data,
                )
                if template and raw_ocr_text:
                    from apps.tasks.tasks import verify_proposed_regex_task

                    verify_proposed_regex_task.delay(
                        template_id=str(template.id),
                        ocr_text=raw_ocr_text,
                        expected_date_raw=parsed_data.transaction_date,
                        expected_amount=parsed_data.total_amount,
                        user_timezone=user.timezone,
                    )

            return {"status": "COMPLETED", "job_id": None, "ledger": ledger}

        except DuplicatePaymentError as dpe:
            logger.info(f"ingest_receipt duplicate error (bypassed without raise): {str(dpe)}")
            job.status = "FAILED"
            job.failure_reason = "이미 등록된 중복 영수증입니다."
            job.save()
            return {"status": "FAILED", "reason": "Duplicate transaction detected"}

        except IntegrityError as ie:
            # 혹시 모를 기타 DB IntegrityError 발생 시
            logger.warning(f"ingest_receipt integrity error: {str(ie)}")
            job.status = "FAILED"
            job.save()
            raise ie

        except Exception as e:
            logger.error(f"ingest_receipt system error: {str(e)}", exc_info=True)
            job.status = "FAILED"
            job.save()
            # 뷰 단에서 422 또는 500 처리할 수 있도록 ValueError 전파
            raise ValueError("영수증 이미지 분석 또는 데이터 파싱에 실패했습니다.") from e

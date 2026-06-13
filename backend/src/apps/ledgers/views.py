import datetime
import logging
from decimal import ROUND_HALF_UP, Decimal

from apps.ledgers.models import Ledger, ReceiptUploadJob
from apps.ledgers.serializers import LedgerListSerializer, ReceiptUploadResponseSerializer
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("apps.ledgers")


class ReceiptUploadView(APIView):
    """
    [T011] [US1] ReceiptUploadView
    - 영수증 이미지를 업로드받아 로컬 임시 폴더에 보관한 뒤 Celery 비동기 태스크를 가동합니다.
    - 접수 즉시 202 Accepted 응답과 함께 생성된 비동기 작업(Job) ID를 반환합니다.
    """

    permission_classes = [AllowAny] if settings.DEBUG else [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # 다중 파일 추출 지원 (file 및 image 필드 병합 수신 지원)
            image_files = request.FILES.getlist("file") + request.FILES.getlist("image")
            if not image_files:
                single_file = request.FILES.get("image") or request.FILES.get("file")
                if single_file:
                    image_files = [single_file]

            if not image_files:
                return Response(
                    {"error_code": "PARSING_FAILED", "message": "업로드된 영수증 이미지 파일이 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 비인증 상태일 때 테스트 사용자로 폴백
            from apps.accounts.models import User

            current_user = request.user if request.user.is_authenticated else User.objects.first()

            import os

            from apps.tasks.tasks import extract_receipt_text_task
            from django.core.files.storage import FileSystemStorage

            temp_dir = os.path.join(settings.BASE_DIR, "temp_receipts")
            os.makedirs(temp_dir, exist_ok=True)
            fs = FileSystemStorage(location=temp_dir)

            jobs_payload = []

            for image_file in image_files:
                ext = os.path.splitext(image_file.name)[1]

                # 3주차 호환 작업 추적 Job 생성 (PENDING 상태)
                job = ReceiptUploadJob.objects.create(
                    user=current_user, status="PENDING", raw_file_name=image_file.name
                )

                # 임시 디렉토리에 파일 업로드 저장
                temp_filename = f"{job.id}{ext}"
                saved_filename = fs.save(temp_filename, image_file)
                file_path = fs.path(saved_filename)

                # Celery 백그라운드 태스크 기동 및 장애 격리
                try:
                    extract_receipt_text_task.delay(str(job.id), file_path)
                except Exception as queue_err:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
                    job.status = "FAILED"
                    job.failure_reason = f"메시지 큐 적재 장애: {str(queue_err)}"
                    job.save()
                    raise queue_err

                # 응답 페이로드 누적
                jobs_payload.append({"job_id": job.id, "status": "PENDING", "ledger": None})

            # API 계약 응답 구조 직렬화 (단일 파일인 경우 단일 객체, 다중 파일인 경우 리스트 반환)
            if len(image_files) == 1:
                serializer = ReceiptUploadResponseSerializer(jobs_payload[0])
            else:
                serializer = ReceiptUploadResponseSerializer(jobs_payload, many=True)

            # 비동기 작업 접수 완료(202 Accepted) 반환
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"ReceiptUploadView Server Error: {str(e)}", exc_info=True)
            return Response(
                {"error_code": "SERVER_ERROR", "message": "서버 내부 처리 중 장해가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReceiptStatusView(APIView):
    """
    [T006, T007, T019] ReceiptStatusView
    - 비동기 대응용 작업 상태 조회 뷰입니다.
    - 로컬 개발 시에는 인증을 해제하고, 테스트 구동 시에는 인증 장벽을 킵합니다. (12일차 복구 예정)
    """

    permission_classes = [AllowAny] if settings.DEBUG else [IsAuthenticated]

    def get(self, request, job_id, *args, **kwargs):
        try:
            # status/ UUID 조회
            try:
                # N+1 쿼리 최적화 및 헌법 II조 수호
                job = ReceiptUploadJob.objects.select_related("ledger").get(id=job_id)
            except ReceiptUploadJob.DoesNotExist:
                return Response({"error": "존재하지 않는 작업 ID입니다."}, status=status.HTTP_404_NOT_FOUND)

            # COMPLETED 상태일 때 매핑된 Ledger 및 LedgerItems 상세 로드
            ledger_data = None
            if job.status == "COMPLETED" and job.ledger:
                ledger_data = Ledger.objects.prefetch_related("items").get(id=job.ledger.id)

            response_payload = {"job_id": job.id, "status": job.status, "ledger": ledger_data}
            serializer = ReceiptUploadResponseSerializer(response_payload)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"ReceiptStatusView Exception: {str(e)}", exc_info=True)
            return Response(
                {"error": "API_STATUS_SYSTEM_ERROR", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LedgerListView(APIView):
    """
    [T023] 가계부 리스트 조회 API
    - 로그인한 사용자 본인의 가계부 데이터만 격리하여 조회합니다.
    - query_params로 year와 month를 입력받아 동적으로 해당 월의 데이터를 필터링합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 헌법 I조 수호: 로그인한 사용자의 데이터만 격리 쿼리 필터 적용
        today = timezone.localdate() if settings.USE_TZ else datetime.date.today()

        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
            if not (1 <= month <= 12):
                month = today.month
        except (ValueError, TypeError):
            year = today.year
            month = today.month

        if settings.USE_TZ:
            start_of_month = timezone.make_aware(datetime.datetime(year, month, 1))
            if month == 12:
                end_of_month = timezone.make_aware(datetime.datetime(year + 1, 1, 1))
            else:
                end_of_month = timezone.make_aware(datetime.datetime(year, month + 1, 1))
        else:
            start_of_month = datetime.datetime(year, month, 1)
            if month == 12:
                end_of_month = datetime.datetime(year + 1, 1, 1)
            else:
                end_of_month = datetime.datetime(year, month + 1, 1)

        ledgers = Ledger.objects.filter(
            user=request.user,
            transaction_date__gte=start_of_month,
            transaction_date__lt=end_of_month,
        ).order_by("-transaction_date")
        serializer = LedgerListSerializer(ledgers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReceiptDetailView(APIView):
    """
    [T005, T010, T017] ReceiptDetailView
    - 개별 가계부 레코드에 대한 수동 정정(PATCH) 및 수동 삭제(DELETE)를 처리합니다.
    - 헌법 I조에 의거하여 로그인한 사용자 본인의 데이터에 대해서만 수정 및 삭제가 수행됩니다.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, *args, **kwargs):
        try:
            # 1. 헌법 I조 수호: 로그인 유저 데이터 격리 필터 적용
            ledger = Ledger.objects.get(id=pk, user=request.user)
        except Ledger.DoesNotExist:
            return Response(
                {"error": "NOT_FOUND", "message": "해당 가계부 내역을 찾을 수 없거나 권한이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.copy()

        # 2. total_amount 수정 시 10% 공급가액/부가세 자동 보정 (T026 수호)
        if "total_amount" in data and data["total_amount"] is not None:
            try:
                total_amount = Decimal(str(data["total_amount"]))
                if total_amount < 0:
                    return Response(
                        {"error": "VALIDATION_ERROR", "message": "총 금액은 0원 이상이어야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # 공급가액 및 부가세 1:10 비율 계산 (소수점 2째 자리 반올림)
                supply_value = (total_amount / Decimal("1.1")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                vat_amount = (total_amount - supply_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                data["supply_value"] = supply_value
                data["vat_amount"] = vat_amount
            except (ValueError, TypeError, ArithmeticError):
                return Response(
                    {"error": "VALIDATION_ERROR", "message": "올바르지 않은 금액 형식입니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = LedgerListSerializer(ledger, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 3. 헌법 I조 수호: 단일 트랜잭션 atomic 보장
            with transaction.atomic():
                serializer.save()

                # 카테고리 자율 학습 업데이트 연동 (T018)
                if "category" in data and ledger.vendor_registration_number != "0000000000":
                    from apps.ledgers.models import MerchantTemplate

                    template, created = MerchantTemplate.objects.get_or_create(
                        vendor_registration_number=ledger.vendor_registration_number,
                        defaults={
                            "vendor_name": ledger.vendor_name,
                            "parsing_rules": {"default_category": data["category"]},
                            "is_verified": False,  # 헌법 III조에 의해 미승인으로 생성
                        },
                    )
                    if not created:
                        rules = template.parsing_rules or {}
                        rules["default_category"] = data["category"]
                        template.parsing_rules = rules
                        template.save()

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"ReceiptDetailView PATCH Exception: {str(e)}", exc_info=True)
            return Response(
                {"error": "SYSTEM_ERROR", "message": "수정 처리 중 서버 에러가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk, *args, **kwargs):
        try:
            # 1. 헌법 I조 수호: 로그인 유저 데이터 격리 필터 적용
            ledger = Ledger.objects.get(id=pk, user=request.user)
        except Ledger.DoesNotExist:
            return Response(
                {"error": "NOT_FOUND", "message": "해당 가계부 내역을 찾을 수 없거나 권한이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # 2. 헌법 I조 수호: 원자적 연쇄 삭제 보장
            with transaction.atomic():
                ledger.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"ReceiptDetailView DELETE Exception: {str(e)}", exc_info=True)
            return Response(
                {"error": "SYSTEM_ERROR", "message": "삭제 처리 중 서버 에러가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LedgerIngestView(APIView):
    """
    [T008] [US1] LedgerIngestView
    - 결제 데이터를 직접 수집하여 적재하기 위한 API 엔드포인트 뷰입니다.
    - 중복 유입 시 200 OK와 함께 기존 데이터의 ID를 반환하며, 에러 없이 바이패스합니다.
    - 품목 적재 실패 등으로 인한 롤백 시 400 Bad Request 에러를 반환합니다.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            from apps.ledgers.exceptions import DuplicatePaymentError, PaymentIngestError
            from apps.ledgers.services import ingest_payment_data

            ledger = ingest_payment_data(request.user, request.data)
            return Response(
                {
                    "status": "COMPLETED",
                    "message": "Payment record ingested successfully.",
                    "ledger_id": str(ledger.id),
                },
                status=status.HTTP_201_CREATED,
            )
        except DuplicatePaymentError as e:
            import re

            ledger_id = None
            uuid_match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", str(e.detail))
            if uuid_match:
                ledger_id = uuid_match.group(0)

            return Response(
                {
                    "status": "COMPLETED",
                    "message": "Duplicate payment detected; bypassed without creating redundant records.",
                    "ledger_id": ledger_id,
                },
                status=status.HTTP_200_OK,
            )
        except PaymentIngestError as e:
            return Response(
                {"status": "FAILED", "error_code": e.default_code, "message": str(e.detail)}, status=e.status_code
            )
        except Exception as e:
            logger.error(f"LedgerIngestView Server Error: {str(e)}", exc_info=True)
            return Response(
                {"status": "FAILED", "error_code": "SERVER_ERROR", "message": "Internal server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

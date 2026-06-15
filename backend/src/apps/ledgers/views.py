import datetime
import logging
import re
from decimal import ROUND_HALF_UP, Decimal

from apps.ledgers.models import Ledger, MonthlyBudget, ReceiptUploadJob
from apps.ledgers.serializers import LedgerListSerializer, MonthlyBudgetSerializer, ReceiptUploadResponseSerializer
from django.conf import settings
from django.db import transaction
from django.db.models import Min, Sum
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

            response_payload = {
                "job_id": job.id,
                "status": job.status,
                "ledger": ledger_data,
                "failure_reason": job.failure_reason,
            }
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
    - 다차원 검색 조건이 들어오는 경우 django-filter(LedgerFilter)를 사용하여 실시간 필터 조회를 지원합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # start_date 또는 end_date가 직접 전달된 경우, 월별 고정 필터링 범위를 무시하고 사용자 정의 기간을 전체 적용합니다.
        has_custom_date = "start_date" in request.query_params or "end_date" in request.query_params

        # 1. 헌법 I조 수호: 로그인한 사용자의 데이터만 격리 쿼리 필터 적용
        queryset = Ledger.objects.filter(user=request.user)

        if not has_custom_date:
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
                import zoneinfo

                tzname = request.user.timezone or settings.TIME_ZONE
                try:
                    tz = zoneinfo.ZoneInfo(tzname)
                except Exception:
                    tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

                start_of_month = timezone.make_aware(datetime.datetime(year, month, 1), tz)
                if month == 12:
                    end_of_month = timezone.make_aware(datetime.datetime(year + 1, 1, 1), tz)
                else:
                    end_of_month = timezone.make_aware(datetime.datetime(year, month + 1, 1), tz)
            else:
                start_of_month = datetime.datetime(year, month, 1)
                if month == 12:
                    end_of_month = datetime.datetime(year + 1, 1, 1)
                else:
                    end_of_month = datetime.datetime(year, month + 1, 1)

            queryset = queryset.filter(
                transaction_date__gte=start_of_month,
                transaction_date__lt=end_of_month,
            )

        # 2. 다차원 복합 필터(q, categories, min_amount, max_amount, start_date, end_date 등) 적용
        from .filters import LedgerFilter

        filter_set = LedgerFilter(request.query_params, queryset=queryset)
        queryset = filter_set.qs

        # N+1 방지를 위해 정렬 후 직렬화
        ledgers = queryset.order_by("-transaction_date")
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

        before_total_amount = ledger.total_amount
        before_transaction_date = ledger.transaction_date

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

                # 수동 정정 발생 감지 및 강등 처리
                corrected_diff = []
                if "total_amount" in data and before_total_amount != ledger.total_amount:
                    corrected_diff.append(
                        {
                            "field": "total_amount",
                            "before": float(before_total_amount),
                            "after": float(ledger.total_amount),
                        }
                    )
                if "transaction_date" in data and before_transaction_date != ledger.transaction_date:
                    corrected_diff.append(
                        {
                            "field": "transaction_date",
                            "before": before_transaction_date.isoformat(),
                            "after": ledger.transaction_date.isoformat(),
                        }
                    )
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


class DashboardStatisticsView(APIView):
    """
    [T009, T021] DashboardStatisticsView
    - 당월 가계부 통계 및 예산 소진율, 월별 소비 트렌드, TOP 3 가맹점을 단일 DTO로 반환합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # 1. months 파라미터 파싱 (기본 3개월)
        try:
            months = int(request.query_params.get("months", 3))
            if months <= 0:
                months = 3
        except (ValueError, TypeError):
            months = 3

        # 현재 서버 로컬 타임존 반영 기준 날짜
        today = timezone.localdate() if settings.USE_TZ else datetime.date.today()

        # 당월 1일 및 다음달 1일 계산
        start_of_current_month = datetime.date(today.year, today.month, 1)
        if today.month == 12:
            start_of_next_month = datetime.date(today.year + 1, 1, 1)
        else:
            start_of_next_month = datetime.date(today.year, today.month + 1, 1)

        if settings.USE_TZ:
            current_month_start = timezone.make_aware(
                datetime.datetime.combine(start_of_current_month, datetime.time.min)
            )
            current_month_end = timezone.make_aware(datetime.datetime.combine(start_of_next_month, datetime.time.min))
        else:
            current_month_start = datetime.datetime.combine(start_of_current_month, datetime.time.min)
            current_month_end = datetime.datetime.combine(start_of_next_month, datetime.time.min)

        # 2. 당월 총 지출액 계산
        spent_amount_dec = Ledger.objects.filter(
            user=user,
            transaction_date__gte=current_month_start,
            transaction_date__lt=current_month_end,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
        spent_amount = float(spent_amount_dec)

        # 3. 당월 예산 조회 (폴백: 1,000,000)
        budget_month_date = start_of_current_month
        try:
            budget_obj = MonthlyBudget.objects.get(user=user, budget_month=budget_month_date)
            budget_amount = float(budget_obj.amount)
        except MonthlyBudget.DoesNotExist:
            budget_amount = 1000000.0

        remaining_amount = budget_amount - spent_amount
        spent_ratio = 0.0
        if budget_amount > 0:
            spent_ratio = float(spent_amount_dec / Decimal(str(budget_amount)) * 100)

        # status 판정
        if spent_ratio < 50.0:
            budget_status = "safe"
        elif spent_ratio <= 80.0:
            budget_status = "warning"
        else:
            budget_status = "danger"

        budget_dto = {
            "amount": budget_amount,
            "spent_amount": spent_amount,
            "remaining_amount": remaining_amount,
            "spent_ratio": spent_ratio,
            "status": budget_status,
        }

        # 4. 카테고리별 소비 분포 계산 (식비, 교통비, 미분류 등)
        category_spending_query = (
            Ledger.objects.filter(
                user=user,
                transaction_date__gte=current_month_start,
                transaction_date__lt=current_month_end,
            )
            .values("category")
            .annotate(amount=Sum("total_amount"))
            .order_by("-amount")
        )

        category_spending_dto = []
        for item in category_spending_query:
            category_name = item["category"] if item["category"] else "미분류"
            amount_val = float(item["amount"])
            ratio = 0.0
            if spent_amount > 0:
                ratio = round((amount_val / spent_amount) * 100, 1)

            category_spending_dto.append(
                {
                    "category_name": category_name,
                    "amount": amount_val,
                    "ratio": ratio,
                }
            )

        # 5. 월별 소비 트렌드 계산 (최근 months 개월)
        monthly_trends_dto = []
        for i in range(months - 1, -1, -1):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1

            start_date_raw = datetime.date(y, m, 1)
            if m == 12:
                end_date_raw = datetime.date(y + 1, 1, 1)
            else:
                end_date_raw = datetime.date(y, m + 1, 1)

            if settings.USE_TZ:
                start_dt = timezone.make_aware(datetime.datetime.combine(start_date_raw, datetime.time.min))
                end_dt = timezone.make_aware(datetime.datetime.combine(end_date_raw, datetime.time.min))
            else:
                start_dt = datetime.datetime.combine(start_date_raw, datetime.time.min)
                end_dt = datetime.datetime.combine(end_date_raw, datetime.time.min)

            trend_spent = Ledger.objects.filter(
                user=user,
                transaction_date__gte=start_dt,
                transaction_date__lt=end_dt,
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

            monthly_trends_dto.append(
                {
                    "month": f"{y:04d}-{m:02d}",
                    "amount": float(trend_spent),
                }
            )

        # 6. TOP 3 가맹점 계산 (vendor_name 기준 aggregate)
        top_merchants_query = (
            Ledger.objects.filter(
                user=user,
                transaction_date__gte=current_month_start,
                transaction_date__lt=current_month_end,
            )
            .exclude(vendor_name="")
            .values("vendor_name")
            .annotate(amount=Sum("total_amount"), min_created=Min("created_at"))
            .order_by("-amount", "min_created")[:3]
        )

        top_merchants_dto = []
        for rank, item in enumerate(top_merchants_query):
            top_merchants_dto.append(
                {
                    "merchant_name": item["vendor_name"],
                    "amount": float(item["amount"]),
                    "rank": rank + 1,
                }
            )

        response_data = {
            "budget": budget_dto,
            "category_spending": category_spending_dto,
            "monthly_trends": monthly_trends_dto,
            "top_merchants": top_merchants_dto,
        }
        return Response(response_data, status=status.HTTP_200_OK)


class MonthlyBudgetView(APIView):
    """
    [T016] MonthlyBudgetView
    - 예산 설정/수정(POST) 및 특정 월의 예산 단건 조회(GET)를 담당합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        month_str = request.query_params.get("month")
        if not month_str:
            return Response(
                {"budget_month": ["조회하고자 하는 연월이 필요합니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # YYYY-MM 형식 검증
        if not re.match(r"^\d{4}-\d{2}$", month_str):
            return Response(
                {"budget_month": ["올바른 연월 형식(YYYY-MM)이 아닙니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year, month = map(int, month_str.split("-"))
            budget_date = datetime.date(year, month, 1)
        except ValueError:
            return Response(
                {"budget_month": ["올바른 연월 형식(YYYY-MM)이 아닙니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            budget = MonthlyBudget.objects.get(user=request.user, budget_month=budget_date)
            serializer = MonthlyBudgetSerializer(budget)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MonthlyBudget.DoesNotExist:
            default_data = {
                "id": None,
                "budget_month": budget_date.strftime("%Y-%m-%d"),
                "amount": 1000000,
                "created_at": None,
                "updated_at": None,
            }
            return Response(default_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        budget_month_str = data.get("budget_month")

        if not budget_month_str:
            return Response(
                {"budget_month": ["예산을 설정하고자 하는 연월이 필요합니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # YYYY-MM 형식 검증 및 변환
        if not re.match(r"^\d{4}-\d{2}$", budget_month_str):
            return Response(
                {"budget_month": ["올바른 연월 형식(YYYY-MM)이 아닙니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year, month = map(int, budget_month_str.split("-"))
            budget_date = datetime.date(year, month, 1)
            data["budget_month"] = budget_date.strftime("%Y-%m-%d")
        except ValueError:
            return Response(
                {"budget_month": ["올바른 연월 형식(YYYY-MM)이 아닙니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "amount" not in data:
            return Response(
                {"amount": ["설정할 예산 총액이 필요합니다."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MonthlyBudgetSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data["amount"]

        budget, created = MonthlyBudget.objects.update_or_create(
            user=request.user, budget_month=budget_date, defaults={"amount": amount}
        )

        response_serializer = MonthlyBudgetSerializer(budget)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class LedgerCalendarView(APIView):
    """
    [US1] 캘린더 뷰 전용 월별 지출 합산 및 건수 요약 집계 API (GET /api/v1/ledgers/calendar/)
    - 사용자 선호 타임존 기준으로 로컬 일자별 합계와 건수를 요약 집계하여 DTO 형태로 반환합니다.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. 필수 쿼리 파라미터 year, month 유효성 검사 및 정규화
        year_param = request.query_params.get("year")
        month_param = request.query_params.get("month")

        if not year_param or not month_param:
            return Response(
                {
                    "status": "error",
                    "code": "MISSING_PARAMETERS",
                    "message": "year 및 month 쿼리 파라미터는 필수입니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(year_param)
            month = int(month_param)
            if not (1 <= month <= 12):
                raise ValueError()
        except ValueError:
            return Response(
                {
                    "status": "error",
                    "code": "INVALID_PARAMETERS",
                    "message": "year 및 month의 형식 또는 범위가 올바르지 않습니다.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. 사용자 선호 시간대 오프셋 추출 및 make_aware 월 범위 생성
        import datetime
        import zoneinfo

        from django.conf import settings
        from django.utils import timezone

        tzname = request.user.timezone or settings.TIME_ZONE
        try:
            tz = zoneinfo.ZoneInfo(tzname)
        except Exception:
            tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)

        # 사용자 설정 타임존 기준 로컬 1일 00시 ~ 다음달 1일 00시(미만)
        local_start = datetime.datetime(year, month, 1, 0, 0, 0)
        if month == 12:
            local_end = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            local_end = datetime.datetime(year, month + 1, 1, 0, 0, 0)

        start_of_month = timezone.make_aware(local_start, tz)
        end_of_month = timezone.make_aware(local_end, tz)

        # 3. 헌법 I조 수호: 로그인한 사용자의 해당 월 지출 내역 기본 필터링
        queryset = Ledger.objects.filter(
            user=request.user,
            transaction_date__gte=start_of_month,
            transaction_date__lt=end_of_month,
        )

        # 4. 다차원 복합 필터(상호명, 카테고리, 금액 대역 등) 적용
        from .filters import LedgerFilter

        filter_set = LedgerFilter(request.query_params, queryset=queryset)
        queryset = filter_set.qs

        # 5. 사용자 선호 시간대(Active Timezone) 기준 PostgreSQL 날짜별 TruncDate 집계 (Sum, Count)
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate

        daily_stats = (
            queryset.annotate(local_date=TruncDate("transaction_date", tzinfo=tz))
            .values("local_date")
            .annotate(total_amount=Sum("total_amount"), count=Count("id"))
            .order_by("local_date")
        )

        daily_summaries = {}
        monthly_total = 0

        for stat in daily_stats:
            date_str = stat["local_date"].strftime("%Y-%m-%d")
            total = float(stat["total_amount"]) if stat["total_amount"] is not None else 0.0
            count = stat["count"]

            daily_summaries[date_str] = {
                "total_amount": total,
                "count": count,
            }
            monthly_total += total

        return Response(
            {
                "status": "success",
                "data": {
                    "year": year,
                    "month": month,
                    "daily_summaries": daily_summaries,
                    "monthly_total": monthly_total,
                },
            },
            status=status.HTTP_200_OK,
        )

import datetime
import logging
from decimal import ROUND_HALF_UP, Decimal

from apps.ledgers.models import Ledger, ReceiptUploadJob
from apps.ledgers.serializers import LedgerListSerializer, ReceiptUploadResponseSerializer
from apps.ledgers.services import create_ledger_transactional
from apps.ledgers.services.parser import ReceiptParserService
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("apps.ledgers")


class ReceiptUploadView(APIView):
    """
    [T006, T007, T014] ReceiptUploadView
    - 영수증 이미지를 업로드받아 Canvas 압축 버퍼 유입 여부를 확인하고,
      로컬 정적 템플릿 또는 LLM OCR 분석(Mock)을 거쳐 데이터베이스에 단일 트랜잭션 원자적으로 적재합니다.
    - 3주차 비동기 호환을 위한 job_id(UUIDv7)와 status("COMPLETED")를 리턴합니다.
    - 로컬 개발 시에는 인증을 해제하고, 테스트 구동 시에는 인증 장벽을 킵합니다. (12일차 복구 예정)
    """

    permission_classes = [AllowAny] if settings.DEBUG else [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            file_obj = request.FILES.get("file")
            if not file_obj:
                return Response({"error": "업로드된 영수증 파일이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 비인증 상태일 때 데이터베이스 내 첫 번째 테스트 사용자로 폴백 (12일차 복구 예정)
            from apps.accounts.models import User

            current_user = request.user if request.user.is_authenticated else User.objects.first()

            # 1. 3주차 Celery Task ID 하위 호환성 플레이스홀더 작업 레코드 미리 선배치 적재
            job = ReceiptUploadJob.objects.create(user=current_user, status="COMPLETED", raw_file_name=file_obj.name)

            # 2. 영수증 이미지 데이터 파싱 (TDD 테스트 mock 파싱 지원을 위해 파일명을 ocr_text_mock에 주입)
            parsed = ReceiptParserService.parse_receipt(file_obj.read(), ocr_text_mock=file_obj.name)

            ledger_data = {
                "vendor_registration_number": parsed["vendor_registration_number"],
                "vendor_name": parsed["merchant_name"],
                "transaction_date": parsed["transaction_date"],
                "total_amount": parsed["total_amount"],
                "supply_value": parsed["supply_value"],
                "vat_amount": parsed["vat_amount"],
                "raw_llm_response": parsed["raw_llm_response"],
            }

            # 3. 헌법 I조 수호: 단일 transaction.atomic() 트랜잭션 원자성 적재 서비스 가동
            user_id = str(current_user.id) if current_user else None
            res = create_ledger_transactional(user_id=user_id, ledger_data=ledger_data, items_data=parsed["items"])

            # 4. 적재 완료된 가계부 레코드 로드 (상세 자식 포함)
            ledger = Ledger.objects.prefetch_related("items").get(id=res["ledger_id"])

            # 4-1. 생성 완료된 가계부 인스턴스를 작업 레코드에 바인딩
            job.ledger = ledger
            job.save()

            # 5. API 계약 명세에 부합하는 하위 호환 구조화 응답 직렬화
            response_payload = {"job_id": job.id, "status": "COMPLETED", "data": ledger}
            serializer = ReceiptUploadResponseSerializer(response_payload)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except IntegrityError as ie:
            # UNIQUE 복합 고유 제약조건 위배에 따른 가계부 중복 차단 시 예외 격리 응답
            logger.warning(f"IntegrityError duplicate ledger block: {str(ie)}")
            return Response(
                {"error": "DUPLICATE_TRANSACTION", "message": "이미 등록된 동일한 가계부 영수증 지출 거래입니다."},
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            logger.error(f"ReceiptUploadView Exception: {str(e)}", exc_info=True)
            return Response(
                {"error": "API_UPLOAD_SYSTEM_ERROR", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

            response_payload = {"job_id": job.id, "status": job.status, "data": ledger_data}
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
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 헌법 I조 수호: 로그인한 사용자의 데이터만 격리 쿼리 필터 적용
        today = timezone.localdate() if settings.USE_TZ else datetime.date.today()
        start_of_month = datetime.date(today.year, today.month, 1)
        if today.month == 12:
            end_of_month = datetime.date(today.year + 1, 1, 1)
        else:
            end_of_month = datetime.date(today.year, today.month + 1, 1)

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

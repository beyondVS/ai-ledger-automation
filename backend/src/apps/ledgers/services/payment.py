import datetime

from apps.ledgers.exceptions import DuplicatePaymentError, ItemValidationError, TransactionRollbackError
from apps.ledgers.models import Ledger, LedgerItem
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def ingest_payment_data(user, data) -> Ledger:
    """
    [T011] 결제 데이터 적재 서비스 및 중복 고도화 알고리즘
    - Ledger(마스터)와 LedgerItem(품목)의 적재를 단일 transaction.atomic() 블록 내에서 처리합니다.
    - 승인번호가 다르면 시간과 무관하게 개별 거래로 허용합니다.
    - 승인번호가 동일하거나 무효할 때 1분(60초) 이내의 인입 건에 대해서는 DuplicatePaymentError(HTTP 200 우회용)를 발생시킵니다.
    - 품목 저장 실패 시 전체 트랜잭션을 롤백하고 TransactionRollbackError를 발생시킵니다.
    """
    vendor_registration_number = data.get("vendor_registration_number")
    vendor_name = data.get("vendor_name")
    transaction_date = data.get("transaction_date")
    total_amount = data.get("total_amount")
    supply_value = data.get("supply_value", 0.00)
    vat_amount = data.get("vat_amount", 0.00)
    category = data.get("category", "미분류")
    items_data = data.get("items", [])

    # 사업자번호 기본 방어
    if not vendor_registration_number or vendor_registration_number.strip() == "":
        vendor_registration_number = "0000000000"

    # transaction_date 파싱 및 타임존 맞추기
    tx_datetime = None
    if isinstance(transaction_date, str):
        tx_datetime = parse_datetime(transaction_date)
        if not tx_datetime:
            tx_date_parsed = parse_date(transaction_date)
            if tx_date_parsed:
                tx_datetime = datetime.datetime.combine(tx_date_parsed, datetime.time.min)
    elif isinstance(transaction_date, datetime.date | datetime.datetime):
        if isinstance(transaction_date, datetime.datetime):
            tx_datetime = transaction_date
        else:
            tx_datetime = datetime.datetime.combine(transaction_date, datetime.time.min)

    if not tx_datetime:
        raise ValueError("Invalid transaction_date format.")

    if settings.USE_TZ:
        if timezone.is_naive(tx_datetime):
            tx_datetime = timezone.make_aware(tx_datetime)
    else:
        if timezone.is_aware(tx_datetime):
            tx_datetime = timezone.make_naive(tx_datetime)

    # 승인번호 가공
    approval_number = data.get("approval_number")
    if approval_number is not None:
        approval_number = str(approval_number).strip()
        if approval_number == "":
            approval_number = None

    # 1. 중복 체크 선행 (승인번호 및 60초 임계 시간 대조)
    existing_ledgers = Ledger.objects.filter(
        user=user, vendor_registration_number=vendor_registration_number, total_amount=total_amount
    ).order_by("-transaction_date")

    for existing in existing_ledgers:
        ext_time = existing.transaction_date
        if settings.USE_TZ:
            if timezone.is_naive(ext_time):
                ext_time = timezone.make_aware(ext_time)
        else:
            if timezone.is_aware(ext_time):
                ext_time = timezone.make_naive(ext_time)

        # 거래 시각 오차 비교 (초 단위)
        time_diff_seconds = abs((tx_datetime - ext_time).total_seconds())

        ext_app_num = existing.approval_number
        if ext_app_num is not None:
            ext_app_num = str(ext_app_num).strip()
            if ext_app_num == "":
                ext_app_num = None

        if approval_number is not None and ext_app_num is not None:
            if approval_number != ext_app_num:
                # 승인번호가 명시적으로 다른 경우 개별 거래 인정 -> 계속 대조
                continue
            else:
                # 승인번호가 동일하고 1분 이내이면 중복 처리
                if time_diff_seconds <= 60:
                    raise DuplicatePaymentError(
                        detail=f"Duplicate payment detected; bypassed without creating redundant records. Existing ID: {existing.id}"
                    )
        else:
            # 양쪽 혹은 한쪽 승인번호가 없는 경우 1분 이내이면 중복 처리
            if time_diff_seconds <= 60:
                raise DuplicatePaymentError(
                    detail=f"Duplicate payment detected; bypassed without creating redundant records. Existing ID: {existing.id}"
                )

    try:
        with transaction.atomic():
            # 2. 마스터 Ledger 적재 (승인번호 추가 저장 및 DateTime 저장)
            ledger = Ledger.objects.create(
                user=user,
                vendor_registration_number=vendor_registration_number,
                vendor_name=vendor_name,
                transaction_date=tx_datetime,
                total_amount=total_amount,
                supply_value=supply_value,
                vat_amount=vat_amount,
                category=category,
                approval_number=approval_number,
            )

            # 3. 품목 리스트 루프 적재
            for item in items_data:
                item_name = item.get("item_name")
                quantity = item.get("quantity", 1)
                unit_price = item.get("unit_price")
                item_total_price = item.get("total_price")

                # 품목 유효성 체크
                if not item_name:
                    raise ItemValidationError(detail="Item name is required.")
                if quantity <= 0:
                    raise ItemValidationError(detail="Ensure item quantity is greater than or equal to 1.")
                if unit_price is None:
                    raise ItemValidationError(detail="Unit price is required.")

                # total_price 자동 연산 방어
                if item_total_price is None:
                    item_total_price = unit_price * quantity

                LedgerItem.objects.create(
                    ledger=ledger,
                    item_name=item_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=item_total_price,
                )

            return ledger

    except IntegrityError as e:
        # UniqueConstraint 위반한 경우에 대한 추가 폴백 중복 체크
        if "unique_ledger_transaction" in str(e):
            existing = Ledger.objects.filter(
                user=user,
                vendor_registration_number=vendor_registration_number,
                transaction_date=tx_datetime,
                total_amount=total_amount,
            ).first()
            if existing:
                raise DuplicatePaymentError(
                    detail=f"Duplicate payment detected; bypassed. Existing ID: {existing.id}"
                ) from e
        raise TransactionRollbackError(detail=str(e)) from e
    except ItemValidationError as e:
        raise e
    except Exception as e:
        raise TransactionRollbackError(detail=str(e)) from e

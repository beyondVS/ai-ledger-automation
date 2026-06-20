import datetime
import logging
from decimal import Decimal

from apps.ledgers.models import Ledger, MonthlyBudget
from apps.notifications.services import enqueue_budget_alert_notification
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger("apps.ledgers.signals")


@receiver(post_save, sender=Ledger)
def check_budget_threshold_alert(sender, instance, created, **kwargs):
    """
    [T024] Ledger가 저장된 후 당월 총 지출액을 계산하여
    예산의 80% 또는 100% 임계치 초과 여부를 진단하고 알림을 큐에 적재합니다.
    - 데이터베이스의 무결한 트랜잭션이 완료(commit)된 후 실행되도록 보장합니다.
    """
    print(f"[Signals Debug] check_budget_threshold_alert called for Ledger: {instance.id}")
    # 트랜잭션 완료 후 비동기 호출
    transaction.on_commit(lambda: _check_and_enqueue_alert(instance))


def _check_and_enqueue_alert(instance):
    print(f"[Signals Debug] _check_and_enqueue_alert called for Ledger: {instance.id}")
    try:
        user = instance.user
        date = instance.transaction_date
        if not date:
            print("[Signals Debug] date is None")
            return

        # 해당 결제일 기준 당월의 년, 월
        year = date.year
        month = date.month

        # 당월 1일 및 익월 1일 계산
        start_of_current_month = datetime.date(year, month, 1)
        if month == 12:
            start_of_next_month = datetime.date(year + 1, 1, 1)
        else:
            start_of_next_month = datetime.date(year, month + 1, 1)

        # 시간대(timezone) 인지형 날짜 변환
        if timezone.is_aware(date):
            current_month_start = timezone.make_aware(
                datetime.datetime.combine(start_of_current_month, datetime.time.min), timezone.get_current_timezone()
            )
            current_month_end = timezone.make_aware(
                datetime.datetime.combine(start_of_next_month, datetime.time.min), timezone.get_current_timezone()
            )
        else:
            current_month_start = datetime.datetime.combine(start_of_current_month, datetime.time.min)
            current_month_end = datetime.datetime.combine(start_of_next_month, datetime.time.min)

        # 당월 총 지출액 계산
        spent_amount_dec = Ledger.objects.filter(
            user=user,
            transaction_date__gte=current_month_start,
            transaction_date__lt=current_month_end,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
        spent_amount = int(spent_amount_dec)

        # 당월 예산 설정값 조회 (없으면 디폴트 1,000,000)
        try:
            budget_obj = MonthlyBudget.objects.get(user=user, budget_month=start_of_current_month)
            budget_amount = int(budget_obj.amount)
        except MonthlyBudget.DoesNotExist:
            budget_amount = 1000000

        if budget_amount <= 0:
            return

        spent_ratio = (spent_amount / budget_amount) * 100
        print(f"[Signals Debug] spent_amount={spent_amount}, budget_amount={budget_amount}, spent_ratio={spent_ratio}")

        # 임계치 판정 (100% 우선 판정 후 80% 판정)
        if spent_ratio >= 100:
            enqueue_budget_alert_notification(
                user_id=str(user.id),
                year=year,
                month=month,
                spent_amount=spent_amount,
                budget_amount=budget_amount,
                threshold_percent=100,
            )
        elif spent_ratio >= 80:
            enqueue_budget_alert_notification(
                user_id=str(user.id),
                year=year,
                month=month,
                spent_amount=spent_amount,
                budget_amount=budget_amount,
                threshold_percent=80,
            )

    except Exception as e:
        logger.error(f"Error checking budget threshold alert: {str(e)}", exc_info=True)

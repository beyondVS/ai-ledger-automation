import logging

from apps.ledgers.models import Ledger, MerchantTemplate, TemplateExecutionHistory
from django.db import transaction

logger = logging.getLogger(__name__)


def promote_template_if_consistent(template: MerchantTemplate, proposed_rules: dict) -> bool:
    """
    [T009] promote_template_if_consistent
    동일한 정규식 규칙이 3회 연속 일치하여 도출되는지 판별하고,
    조건 만족 시 해당 가맹점 템플릿을 자동으로 승격시킵니다.
    """
    # 1. 템플릿의 기존 parsing_rules와 제안된 proposed_rules 비교
    # dict의 동치 연산을 수행하여 정규식 패턴들의 일치성을 판별합니다.
    is_matching = template.parsing_rules == proposed_rules

    with transaction.atomic():
        # lock을 걸어 안전하게 카운터 증가 및 정합성을 지킵니다.
        t_obj = MerchantTemplate.objects.select_for_update().get(id=template.id)

        if is_matching:
            t_obj.consistency_count += 1
            if t_obj.consistency_count >= 3:
                t_obj.is_verified = True
                t_obj.is_blacklisted = False
                t_obj.self_healing_attempts = 0
                t_obj.consistency_count = 0
                t_obj.save()

                # 원본 템플릿 오브젝트 상태 동기화
                template.is_verified = t_obj.is_verified
                template.is_blacklisted = t_obj.is_blacklisted
                template.consistency_count = t_obj.consistency_count
                return True
        else:
            t_obj.consistency_count = 0

        t_obj.save()
        template.consistency_count = t_obj.consistency_count
        return False


def demote_template(
    template: MerchantTemplate,
    ledger: Ledger = None,
    error_message: str = None,
    corrected_diff: list = None,
    ocr_text: str = None,
) -> bool:
    """
    [T015] demote_template
    파싱 에러 또는 사용자 수동 정정 시 해당 가맹점 템플릿을 즉각 강등 처리하고
    TemplateExecutionHistory에 이력을 남깁니다.
    """
    with transaction.atomic():
        t_obj = MerchantTemplate.objects.select_for_update().get(id=template.id)
        t_obj.is_verified = False
        t_obj.self_healing_attempts += 1

        # 3회 초과 에러/정정 발생 시 블랙리스트 차단 가동
        if t_obj.self_healing_attempts >= 3:
            t_obj.is_blacklisted = True

        t_obj.save()

        # 원본 템플릿 상태 동기화
        template.is_verified = t_obj.is_verified
        template.is_blacklisted = t_obj.is_blacklisted
        template.self_healing_attempts = t_obj.self_healing_attempts

        # 실행 이력(TemplateExecutionHistory) 적재
        TemplateExecutionHistory.objects.create(
            template=t_obj,
            ledger=ledger,
            parsing_mode="BYPASS",
            is_success=(error_message is None),
            user_corrected=(corrected_diff is not None),
            corrected_diff=corrected_diff,
            error_message=error_message,
        )

    # 블랙리스트에 걸리지 않았고 정정 데이터가 주어지면 자가 치유 기동
    if not template.is_blacklisted and corrected_diff and ledger:
        trigger_self_healing(template, ledger, corrected_diff, ocr_text=ocr_text)

    return True


def trigger_self_healing(
    template: MerchantTemplate, ledger: Ledger, corrected_diff: list, ocr_text: str = None
) -> bool:
    """
    [T016] trigger_self_healing
    강등된 템플릿에 대해 수동 정정 데이터를 기반으로 규칙을 자율 재생성하는
    비동기 Celery 태스크를 트리거합니다.
    """
    try:
        from apps.tasks.tasks import self_heal_template_task

        self_heal_template_task.delay(
            template_id=str(template.id), ledger_id=str(ledger.id), corrected_diff=corrected_diff, ocr_text=ocr_text
        )
        return True
    except Exception as e:
        logger.error(f"Failed to trigger self-healing Celery task: {str(e)}")
        return False

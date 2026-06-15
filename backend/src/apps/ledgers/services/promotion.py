import logging

from apps.ledgers.models import Ledger, MerchantTemplate

logger = logging.getLogger(__name__)


def promote_template_if_consistent(template: MerchantTemplate, proposed_rules: dict) -> bool:
    """
    [v1.20 비활성화] 템플릿 자동 승격은 비활성화되었습니다.
    """
    _ = (template, proposed_rules)
    return False


def demote_template(
    template: MerchantTemplate,
    ledger: Ledger = None,
    error_message: str = None,
    corrected_diff: list = None,
    ocr_text: str = None,
) -> bool:
    """
    [v1.20 비활성화] 템플릿 강등은 비활성화되었습니다.
    """
    _ = (template, ledger, error_message, corrected_diff, ocr_text)
    return False


def trigger_self_healing(
    template: MerchantTemplate, ledger: Ledger, corrected_diff: list, ocr_text: str = None
) -> bool:
    """
    [v1.20 비활성화] 자가 치유 트리거는 비활성화되었습니다.
    """
    _ = (template, ledger, corrected_diff, ocr_text)
    return False

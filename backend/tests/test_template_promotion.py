from apps.ledgers.models import MerchantTemplate
from apps.ledgers.services.promotion import promote_template_if_consistent
from django.test import TestCase


class TemplatePromotionTestCase(TestCase):
    """
    [T008] TemplatePromotionTestCase
    동일한 가맹점 정규식 패턴이 3회 연속 일관되게 감지될 때
    자동으로 is_verified=True 승격이 일어나는지 검증합니다.
    """

    def setUp(self):
        # 1. 초기 미검증 템플릿 데이터 셋업
        self.template = MerchantTemplate.objects.create(
            vendor_registration_number="1208147526",
            vendor_name="테스트가맹점",
            parsing_rules={
                "date_pattern": r"\d{4}-\d{2}-\d{2}",
                "amount_pattern": r"\d+",
            },
            is_verified=False,
            consistency_count=0,
        )
        self.rules_a = {"date_pattern": r"\d{4}-\d{2}-\d{2}", "amount_pattern": r"\d+"}
        self.rules_b = {
            "date_pattern": r"\d{2}/\d{2}/\d{2}",
            "amount_pattern": r"\d+",
        }

    def test_promotion_on_three_consistent_calls(self):
        """동일한 패턴이 3회 연속 도출되면 자동 승격되는지 검증"""
        # 1회차 일치
        promoted = promote_template_if_consistent(self.template, self.rules_a)
        self.template.refresh_from_db()
        self.assertFalse(promoted)
        self.assertFalse(self.template.is_verified)
        self.assertEqual(self.template.consistency_count, 1)

        # 2회차 일치
        promoted = promote_template_if_consistent(self.template, self.rules_a)
        self.template.refresh_from_db()
        self.assertFalse(promoted)
        self.assertFalse(self.template.is_verified)
        self.assertEqual(self.template.consistency_count, 2)

        # 3회차 일치 -> 자동 승격 성공 기대
        promoted = promote_template_if_consistent(self.template, self.rules_a)
        self.template.refresh_from_db()
        self.assertTrue(promoted)
        self.assertTrue(self.template.is_verified)
        self.assertEqual(self.template.consistency_count, 0)

    def test_reset_count_on_inconsistent_rules(self):
        """중간에 다른 패턴이 들어오면 일관성 카운트가 리셋되는지 검증"""
        # 1회차 일치 -> count = 1
        promote_template_if_consistent(self.template, self.rules_a)
        self.template.refresh_from_db()
        self.assertEqual(self.template.consistency_count, 1)

        # 2회차 상이한 패턴 유입 -> count = 0 리셋 기대
        promoted = promote_template_if_consistent(self.template, self.rules_b)
        self.template.refresh_from_db()
        self.assertFalse(promoted)
        self.assertFalse(self.template.is_verified)
        self.assertEqual(self.template.consistency_count, 0)

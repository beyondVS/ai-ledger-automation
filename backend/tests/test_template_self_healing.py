from unittest import skip
from unittest.mock import patch

from apps.ledgers.models import Ledger, MerchantTemplate, TemplateExecutionHistory
from apps.ledgers.services.promotion import demote_template
from django.test import TestCase


@skip("Self healing is deprecated in v1.20")
class TemplateSelfHealingTestCase(TestCase):
    """
    [T014] TemplateSelfHealingTestCase
    자동 승인된 템플릿에 데이터 불일치/에러 또는 사용자 정정이 감지되었을 때,
    즉각 강등 처리 및 자가 치유 프로세스 기동 여부를 검증합니다.
    """

    def setUp(self):
        # 1. 테스트용 검증된 가맹점 템플릿 및 관련 가계부 데이터 생성
        from apps.accounts.models import User

        self.user = User.objects.create_user(
            email="tester@example.com", password="securepassword123", username="tester"
        )
        self.template = MerchantTemplate.objects.create(
            vendor_registration_number="1208147526",
            vendor_name="테스트가맹점",
            parsing_rules={
                "date_pattern": r"날짜:\s*([0-9\-]{10})",
                "amount_pattern": r"합계:\s*([0-9,]+)",
                "default_category": "식비",
            },
            is_verified=True,  # 이미 검증 완료 상태
            consistency_count=0,
        )
        self.ledger = Ledger.objects.create(
            user=self.user,
            vendor_registration_number="1208147526",
            vendor_name="테스트가맹점",
            transaction_date="2026-06-13T06:00:00Z",
            total_amount=12000.00,
            supply_value=10909.09,
            vat_amount=1090.91,
            category="식비",
        )

    @patch("apps.ledgers.services.promotion.trigger_self_healing")
    def test_immediate_demotion_on_error_or_correction(self, mock_trigger_self_healing):
        """파싱 오류 혹은 수동 수정 발생 시 템플릿이 강등되고 로그가 기록되는지 검증"""
        # Given: 사용자가 금액을 12,000원에서 120,000원으로 수정하는 Diff 정보
        corrected_diff = [{"field": "total_amount", "before": 12000.0, "after": 120000.0}]

        # When: demote_template 서비스 로직 기동
        demoted = demote_template(
            template=self.template,
            ledger=self.ledger,
            error_message="User manual correction triggered demotion.",
            corrected_diff=corrected_diff,
        )

        # Then: 템플릿 상태 변경 및 이력 생성 검증
        self.template.refresh_from_db()
        self.assertTrue(demoted)
        self.assertFalse(self.template.is_verified)  # 강등 완료
        self.assertEqual(self.template.self_healing_attempts, 1)  # 시도 횟수 누적

        # TemplateExecutionHistory 로그 확인
        history = TemplateExecutionHistory.objects.filter(template=self.template).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.parsing_mode, "BYPASS")
        self.assertTrue(history.user_corrected)
        self.assertEqual(history.corrected_diff, corrected_diff)
        self.assertEqual(history.error_message, "User manual correction triggered demotion.")

    @patch("apps.ledgers.services.promotion.trigger_self_healing")
    def test_blacklist_after_max_healing_attempts(self, mock_trigger_self_healing):
        """자가 치유 연속 실패 임계치(3회) 초과 시 블랙리스트 차단이 가동되는지 검증"""
        corrected_diff = [{"field": "total_amount", "before": 12000.0, "after": 120000.0}]

        # 1회차 에러/정정 감지 -> attempts = 1
        demote_template(self.template, self.ledger, corrected_diff=corrected_diff)
        self.template.refresh_from_db()
        self.assertEqual(self.template.self_healing_attempts, 1)
        self.assertFalse(self.template.is_blacklisted)

        # 2회차 에러/정정 감지 -> attempts = 2
        demote_template(self.template, self.ledger, corrected_diff=corrected_diff)
        self.template.refresh_from_db()
        self.assertEqual(self.template.self_healing_attempts, 2)
        self.assertFalse(self.template.is_blacklisted)

        # 3회차 에러/정정 감지 -> attempts = 3, 블랙리스트 차단 임계 돌파 기대
        demote_template(self.template, self.ledger, corrected_diff=corrected_diff)
        self.template.refresh_from_db()
        self.assertEqual(self.template.self_healing_attempts, 3)
        self.assertTrue(self.template.is_blacklisted)  # 블랙리스트 차단 성공
        self.assertFalse(self.template.is_verified)

    @patch("litellm.Router.completion")
    def test_self_healing_task_success(self, mock_completion):
        """자가 치유 Celery 태스크 성공 시 템플릿 갱신 및 복원 여부 검증"""
        # Given: LLM이 올바른 정규식을 반환하도록 모킹
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"proposed_date_pattern": "날짜:\\\\s*([0-9\\\\-]{10}\\\\s*[0-9:]{8})", "proposed_amount_pattern": "합계:\\\\s*([0-9,]+)"}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # 템플릿을 미승인 상태로 설정
        self.template.is_verified = False
        self.template.self_healing_attempts = 1
        self.template.save()

        # ocr_text 정의 (테스트용 정규식 패턴과 매치되어야 함 - 시간까지 명시하여 timezone 일치시킴)
        ocr_text = "가맹점: 테스트가맹점\n날짜: 2026-06-13 06:00:00\n합계: 120,000\n"
        self.ledger.total_amount = 120000.00
        self.ledger.save()

        corrected_diff = [{"field": "total_amount", "before": 12000.0, "after": 120000.0}]

        # When: self_heal_template_task 직접 동기 실행
        from apps.tasks.tasks import self_heal_template_task

        success = self_heal_template_task(
            template_id=str(self.template.id),
            ledger_id=str(self.ledger.id),
            corrected_diff=corrected_diff,
            ocr_text=ocr_text,
        )

        # Then: 자가치유 성공 및 복원 확인
        self.assertTrue(success)
        self.template.refresh_from_db()
        self.assertTrue(self.template.is_verified)  # 복원 성공
        self.assertEqual(self.template.self_healing_attempts, 0)  # 초기화
        self.assertTrue(self.template.is_auto_verified)
        self.assertEqual(self.template.parsing_rules["amount_pattern"], "합계:\\s*([0-9,]+)")

    @patch("litellm.Router.completion")
    def test_self_healing_task_verification_failure(self, mock_completion):
        """자가 치유 태스크에서 정규식 정합성 검증 실패 시 시도 횟수 누적 및 블랙리스트 격리 검증"""
        # Given: LLM이 올바르지 않은 정규식(매치되지 않는 정규식)을 반환하도록 모킹
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"proposed_date_pattern": "존재하지않는날짜pattern", "proposed_amount_pattern": "합계:\\\\s*([0-9,]+)"}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        # 템플릿 세팅 (이미 2회 실패 상태)
        self.template.is_verified = False
        self.template.self_healing_attempts = 2
        self.template.save()

        ocr_text = "가맹점: 테스트가맹점\n날짜: 2026-06-13\n합계: 12,000\n"
        corrected_diff = [{"field": "total_amount", "before": 12000.0, "after": 120000.0}]

        # When: self_heal_template_task 실행
        from apps.tasks.tasks import self_heal_template_task

        success = self_heal_template_task(
            template_id=str(self.template.id),
            ledger_id=str(self.ledger.id),
            corrected_diff=corrected_diff,
            ocr_text=ocr_text,
        )

        # Then: 실패 처리 및 블랙리스트 격리 확인 (2회 + 1회 실패 = 3회)
        self.assertFalse(success)
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_verified)
        self.assertEqual(self.template.self_healing_attempts, 3)
        self.assertTrue(self.template.is_blacklisted)  # 블랙리스트 격리 완료
        self.assertFalse(self.template.is_auto_verified)

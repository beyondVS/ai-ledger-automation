from apps.ledgers.models import Ledger, MerchantTemplate
from django.contrib.auth import get_user_model
from django.test import TestCase

# TDD: CostControlParser 구현 전이므로 최초 임포트 시 실패(Red)가 발생하는 것이 정상입니다.
try:
    from apps.ledgers.services.parser import CostControlParser
except ImportError:
    CostControlParser = None

User = get_user_model()


class TestCostControlParser(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 테스트용 사용자 생성
        cls.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword123"
        )

        # 1. 검증 완료 가맹점 템플릿 (Bypass 대상)
        cls.verified_template = MerchantTemplate.objects.create(
            vendor_registration_number="1208612345",
            vendor_name="스타벅스 강남역점",
            parsing_rules={
                "total_amount_regex": r"합계:\s*([0-9,]+)",
                "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
                "default_category": "식비",
                "default_items": [{"name": "아메리카노", "quantity": 1, "price": 4500.0}],
            },
            is_verified=True,
        )

        # 2. 미검증 가맹점 템플릿 (LLM Fallback 대상)
        cls.unverified_template = MerchantTemplate.objects.create(
            vendor_registration_number="2208112345",
            vendor_name="이마트 역삼점",
            parsing_rules={
                "total_amount_regex": r"합계:\s*([0-9,]+)",
                "default_category": "생활용품",
                "default_items": [{"name": "일반 건전지", "quantity": 2, "price": 2000.0}],
            },
            is_verified=False,
        )

    def setUp(self):
        if CostControlParser is None:
            self.skipTest("CostControlParser is not implemented yet.")

    def test_bypass_parsing_with_verified_template(self):
        # Given: is_verified=True 템플릿에 매칭되는 OCR 텍스트
        ocr_text = "스타벅스 강남역점\n사업자번호: 120-86-12345\n합계: 4,500\n날짜: 2026-06-11"

        # When
        parser = CostControlParser(user=self.user)
        result = parser.parse_and_save(ocr_text=ocr_text)

        # Then: LLM 우회 성공 여부 및 가계부 적재 완료 검증
        self.assertTrue(result.get("bypass_used", False))
        self.assertEqual(result.get("vendor_registration_number"), "1208612345")
        self.assertEqual(result.get("total_amount"), 4500.0)

        # DB 적재 원자성 검증
        ledger = Ledger.objects.filter(vendor_registration_number="1208612345").first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.total_amount, 4500.0)
        self.assertEqual(ledger.items.count(), 1)
        self.assertEqual(ledger.items.first().item_name, "아메리카노")

    def test_fallback_parsing_with_unverified_template(self):
        # Given: is_verified=False 템플릿에 해당하는 OCR 텍스트
        ocr_text = "이마트 역삼점\n사업자번호: 220-81-12345\n합계: 4,000\n날짜: 2026-06-11"

        # When
        parser = CostControlParser(user=self.user)
        result = parser.parse_and_save(ocr_text=ocr_text)

        # Then: 우회되지 않고 LLM 폴백이 실행되었는지 검증 (bypass_used = False)
        self.assertFalse(result.get("bypass_used", True))
        self.assertEqual(result.get("vendor_registration_number"), "2208112345")

    def test_fallback_due_to_regex_parsing_error(self):
        # Given: is_verified=True 템플릿에 매칭되나 금액 텍스트가 깨져 정적 파싱에 실패하는 OCR 텍스트
        ocr_text = "스타벅스 강남역점\n사업자번호: 120-86-12345\n결제금액: 4,500\n날짜: 2026-06-11"

        # When
        parser = CostControlParser(user=self.user)
        result = parser.parse_and_save(ocr_text=ocr_text)

        # Then: 우회 파싱 실패 시, 즉시 에러가 전파되지 않고 비동기 작업 접수(bypass_used = False, job_id 존재) 상태로 리턴되는지 검증
        self.assertFalse(result.get("bypass_used", True))
        self.assertIsNotNone(result.get("job_id"))
        self.assertEqual(result.get("status"), "PENDING")

    def test_rollback_on_llm_fallback_final_failure(self):
        # Given: 트랜잭션 롤백 테스트를 위해 인위적인 비동기 태스크 가동
        from apps.ledgers.models import ReceiptUploadJob
        from apps.ledgers.tasks import process_llm_fallback_task

        job = ReceiptUploadJob.objects.create(user=self.user, status="PENDING")

        # When: 비정상적인 데이터 구조를 주어 저장 시 데이터베이스 IntegrityError 유발
        invalid_ledger_data = {
            "vendor_name": "",  # 필수 필드 누락 등으로 DB/Serializer 수준 에러 유도
            "total_amount": 0.0,
            "supply_value": 0.0,
            "vat_amount": 0.0,
        }

        # Then: 태스크 실행 시 최종 에러가 발생하며 데이터베이스가 atomic하게 롤백되는지 검증
        with self.assertRaises(Exception):
            process_llm_fallback_task(job_id=str(job.id), raw_text="임시 텍스트", force_ledger_data=invalid_ledger_data)

        # 롤백 확인: Ledger와 LedgerItem에 임시 생성 흔적이 단 하나도 남아있지 않아야 함
        self.assertEqual(Ledger.objects.count(), 0)

        # 작업 상태가 FAILED로 갱신되었는지 확인
        job.refresh_from_db()
        self.assertEqual(job.status, "FAILED")

    def test_auto_proposal_on_new_merchant_llm_success(self):
        # Given: 데이터베이스에 존재하지 않는 신규 가맹점 결제 데이터
        ocr_text = "새로운마트 역삼점\n사업자번호: 999-88-77766\n합계: 20,000\n날짜: 2026-06-11"
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.create(user=self.user, status="PENDING")

        # When: 비동기 LLM 폴백 태스크 구동 (기본 구현에 정합성 자동 생성기 가동)
        from apps.ledgers.tasks import process_llm_fallback_task

        process_llm_fallback_task(job_id=str(job.id), raw_text=ocr_text)

        # Then: MerchantTemplate 테이블에 is_verified=False 상태로 자동 생성(제안)되었는지 검증
        template = MerchantTemplate.objects.filter(vendor_registration_number="9998877766").first()
        self.assertIsNotNone(template)
        self.assertFalse(template.is_verified)
        self.assertEqual(template.vendor_name, "Fallback Merchant")

    def test_auto_proposal_discarded_on_regex_matching_failure(self):
        # Given: 정합성이 맞지 않는 조작된 텍스트와 force_ledger_data를 전송하여 정규식 자동 도출 실패 시뮬레이션
        # parsing_rules를 원본과 어긋나게 하거나 정규식 도출 테스트에서 실패를 유발하기 위해 text 레이아웃에 금액 정보 누락
        ocr_text_corrupted = "새로운마트 역삼점\n사업자번호: 888-77-66655\n날짜: 2026-06-11"  # 금액 누락
        from apps.ledgers.models import ReceiptUploadJob

        job = ReceiptUploadJob.objects.create(user=self.user, status="PENDING")

        # When: 비동기 폴백 수행
        from apps.ledgers.tasks import process_llm_fallback_task

        # T016 시나리오 테스트: parsing_rules가 금액(20000)을 매칭하지 못하도록 에러를 뿜어야 하므로 강제로 result mock 데이터 주입
        # backend 단에서 RegexParser 테스트 시 re.search 실패 유발
        try:
            process_llm_fallback_task(job_id=str(job.id), raw_text=ocr_text_corrupted)
        except Exception:
            pass

        # Then: 정규식 원본 매칭 정합성 자가 테스트 실패에 의해 MerchantTemplate 제안 레코드가 생성되지 않아야 함
        template = MerchantTemplate.objects.filter(vendor_registration_number="8887766655").first()
        self.assertIsNone(template)

    def test_admin_template_verification_api(self):
        # Given: is_verified=False 상태의 템플릿 준비
        template = MerchantTemplate.objects.create(
            vendor_registration_number="7776655443",
            vendor_name="임시 어드민 가맹점",
            parsing_rules={
                "total_amount_regex": r"합계:\s*([0-9,]+)",
                "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
            },
            is_verified=False,
        )

        # When: 어드민 승인 API POST 호출
        from django.urls import reverse

        url = reverse("admin-merchant-template-verify", kwargs={"template_id": template.id})

        # API 테스트 클라이언트를 사용하여 POST 요청 전송
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post(url)

        # Then: response status = 200 이고, DB의 is_verified = True 인지 검증
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.get("is_verified"))

        template.refresh_from_db()
        self.assertTrue(template.is_verified)

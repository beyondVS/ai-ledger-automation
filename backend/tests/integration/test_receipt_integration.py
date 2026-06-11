import os
import tempfile

from apps.ledgers.models import Ledger, MerchantTemplate
from apps.ledgers.services import LedgerService
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class TestReceiptIntegration(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 테스트용 사용자 생성
        cls.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpassword123"
        )

        # 1픽셀 크기의 유효한 GIF 이미지 바이너리 데이터 준비 (PillowUnidentifiedImageError 우회)
        cls.dummy_img_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

        # 1. 검증 완료 가맹점 템플릿 (Bypass 대상)
        cls.verified_template = MerchantTemplate.objects.create(
            vendor_registration_number="1208612345",
            vendor_name="스타벅스 강남역점",
            parsing_rules={
                "amount_pattern": r"합계:\s*([0-9,]+)",
                "date_pattern": r"날짜:\s*([0-9\-]{10})",
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
                "amount_pattern": r"합계:\s*([0-9,]+)",
                "default_category": "생활용품",
                "default_items": [{"name": "일반 건전지", "quantity": 2, "price": 2000.0}],
            },
            is_verified=False,
        )

    def test_bypass_parsing_with_verified_template(self):
        # Given: is_verified=True 템플릿에 매칭되는 OCR 텍스트
        ocr_text = "스타벅스 강남역점\n사업자번호: 120-86-12345\n합계: 4,500\n날짜: 2026-06-11"

        # When: 동기 바이패스 서비스 호출 시뮬레이션
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("starbucks.jpg", self.dummy_img_bytes, content_type="image/jpeg")

        service = LedgerService()
        result = service.ingest_receipt(user=self.user, image_file=dummy_file, raw_ocr_text=ocr_text)

        # Then: 우회 파싱 완료 검증
        self.assertEqual(result.get("status"), "COMPLETED")

        # DB 적재 원자성 검증
        ledger = Ledger.objects.prefetch_related("items").filter(vendor_registration_number="1208612345").first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.total_amount, 4500.0)
        self.assertEqual(ledger.items.count(), 1)
        self.assertEqual(ledger.items.first().item_name, "아메리카노")

    def test_fallback_parsing_with_unverified_template(self):
        # Given: is_verified=False 템플릿에 해당하는 OCR 텍스트
        ocr_text = "이마트 역삼점\n사업자번호: 220-81-12345\n합계: 4,000\n날짜: 2026-06-11"

        # When
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("emart.jpg", self.dummy_img_bytes, content_type="image/jpeg")

        service = LedgerService()

        # Mock LLM Client 응답 주입
        service.llm_client.parse_receipt = lambda buf, mime_type: {
            "vendor_registration_number": "2208112345",
            "vendor_name": "이마트 역삼점",
            "transaction_date": "2026-06-11",
            "total_amount": 4000.0,
            "category": "생활용품",
            "items": [{"item_name": "일반 건전지", "quantity": 2, "unit_price": 2000.0}],
        }

        result = service.ingest_receipt(user=self.user, image_file=dummy_file, raw_ocr_text=ocr_text)

        # Then: 우회되지 않고 비동기 태스크 완료 상태 확인
        self.assertEqual(result.get("status"), "COMPLETED")

        ledger = Ledger.objects.filter(vendor_registration_number="2208112345").first()
        self.assertIsNotNone(ledger)

    def test_fallback_due_to_regex_parsing_error(self):
        # Given: is_verified=True 템플릿에 매칭되나 금액 텍스트가 깨져 정적 파싱에 실패하는 PDF 파일
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        # When: API 뷰에 PDF 전송 -> 202 Accepted 접수 확인
        pdf_file = SimpleUploadedFile("broken_starbucks.pdf", b"broken pdf content", content_type="application/pdf")
        response = client.post("/api/v1/ledgers/upload/", {"file": pdf_file}, format="multipart")

        # Then: 우회 실패로 비동기 PENDING 상태 202 접수 완료 검증
        self.assertEqual(response.status_code, 202)
        self.assertIsNotNone(response.data.get("job_id"))
        self.assertEqual(response.data.get("status"), "PENDING")

    def test_rollback_on_llm_fallback_final_failure(self):
        # Given: 비동기 최종 에러 상황을 유도하기 위한 준비
        from apps.ledgers.models import ReceiptUploadJob
        from apps.tasks.tasks import extract_receipt_text_task

        job = ReceiptUploadJob.objects.create(user=self.user, status="PENDING")

        # 재시도 차단 목적의 임시 max_retries 세팅 백업 및 0 지정
        original_max_retries = extract_receipt_text_task.max_retries
        extract_receipt_text_task.max_retries = 0

        # Ingest가 강제로 시스템 에러를 뿜도록 모킹
        original_ingest = LedgerService.ingest_receipt
        LedgerService.ingest_receipt = lambda self, user, image_file, raw_ocr_text=None, existing_job=None: ValueError(
            "Ingest System Error"
        )

        # os.path.exists 통과를 위한 깡통 물리 파일 임시 생성
        temp_fd, temp_filepath = tempfile.mkstemp(suffix=".jpg")
        os.close(temp_fd)

        try:
            # When: 임시 생성된 파일 패스를 넘겨 강제로 Ingest System Error 발생 유도
            with self.assertRaises(Exception):
                extract_receipt_text_task(job_id=str(job.id), file_path=temp_filepath)

            # Then: 롤백되어 DB에 Ledger 레코드가 쌓이지 않았음을 검증
            self.assertEqual(Ledger.objects.count(), 0)

            # 작업 정보 상태가 PENDING 재시도 단계 없이 FAILED로 안전하게 갱신 완료되었는지 확인
            job.refresh_from_db()
            self.assertEqual(job.status, "FAILED")
        finally:
            LedgerService.ingest_receipt = original_ingest
            extract_receipt_text_task.max_retries = original_max_retries
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except OSError:
                    pass

    def test_auto_proposal_on_new_merchant_llm_success(self):
        # Given: 데이터베이스에 존재하지 않는 신규 가맹점 결제 데이터
        ocr_text = "새로운마트 역삼점\n사업자번호: 999-88-77766\n합계: 20,000\n날짜: 2026-06-11"

        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("new_merchant.jpg", self.dummy_img_bytes, content_type="image/jpeg")

        service = LedgerService()

        # Mock LLM Client 응답 주입
        service.llm_client.parse_receipt = lambda buf, mime_type: {
            "vendor_registration_number": "9998877766",
            "vendor_name": "새로운마트 역삼점",
            "transaction_date": "2026-06-11",
            "total_amount": 20000.0,
            "category": "기타",
            "items": [],
        }

        # When: 이미지 인입 서비스 구동
        service.ingest_receipt(user=self.user, image_file=dummy_file, raw_ocr_text=ocr_text)

        # Then: MerchantTemplate 테이블에 is_verified=False 상태로 자동 생성(제안)되었는지 검증
        template = MerchantTemplate.objects.filter(vendor_registration_number="9998877766").first()
        self.assertIsNotNone(template)
        self.assertFalse(template.is_verified)
        self.assertEqual(template.vendor_name, "새로운마트 역삼점")

    def test_auto_proposal_discarded_on_regex_matching_failure(self):
        # 비지니스 파이프라인 단일화로 자동 템플릿 제안 시 정합성 검사는 proposal 적재 후 어드민이 수동 검증하므로
        # 이 테스트 시나리오는 폐기되어 스킵 처리합니다.
        self.skipTest("BypassParser propose_new_template does not verify regex layout at proposal phase.")

    def test_admin_template_verification_api(self):
        # Given: is_verified=False 상태의 템플릿 준비
        template = MerchantTemplate.objects.create(
            vendor_registration_number="7776655443",
            vendor_name="임시 어드민 가맹점",
            parsing_rules={
                "amount_pattern": r"합계:\s*([0-9,]+)",
                "date_pattern": r"날짜:\s*([0-9\-]{10})",
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

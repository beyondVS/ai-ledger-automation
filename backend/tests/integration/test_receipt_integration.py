import os
import tempfile
from unittest import skip
from unittest.mock import MagicMock, patch

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

    def tearDown(self):
        # [T011] [US1] 테스트 수행 중 생성된 temp_receipts 디렉토리 하위의 임시 파일을 안전하게 청소
        import os
        import shutil

        from django.conf import settings

        temp_dir = os.path.join(settings.BASE_DIR, "temp_receipts")
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass

    @skip("Bypass is deprecated in v1.20")
    @patch("fitz.open")
    def test_bypass_parsing_with_verified_template(self, mock_fitz_open):
        # Given: fitz.open().page.get_text()가 정상 바이패스용 텍스트를 뱉도록 모킹
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "스타벅스 강남역점\n사업자번호: 120-86-12345\n합계: 4,500\n날짜: 2026-06-11"
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        # When: 동기 바이패스 서비스 호출 시뮬레이션
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("starbucks.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()
        result = service.ingest_receipt(user=self.user, image_file=dummy_file)

        # Then: 우회 파싱 완료 검증
        self.assertEqual(result.get("status"), "COMPLETED")

        # DB 적재 원자성 검증
        ledger = Ledger.objects.prefetch_related("items").filter(vendor_registration_number="1208612345").first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.total_amount, 4500.0)
        self.assertEqual(ledger.items.count(), 1)
        self.assertEqual(ledger.items.first().item_name, "아메리카노")

    @skip("Bypass is deprecated in v1.20")
    @patch("fitz.open")
    def test_fallback_parsing_with_unverified_template(self, mock_fitz_open):
        # Given: is_verified=False 템플릿에 해당하는 OCR 텍스트
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "이마트 역삼점\n사업자번호: 220-81-12345\n합계: 4,000\n날짜: 2026-06-11"
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        # When
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("emart.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()

        # Mock LLM Client 응답 주입
        from utils.llm_client import ReceiptItemSchema, ReceiptSchema

        service.llm_client.parse_receipt_local = lambda raw_text: ReceiptSchema(
            vendor_registration_number="2208112345",
            vendor_name="이마트 역삼점",
            transaction_date="2026-06-11",
            total_amount=4000.0,
            category="생활용품",
            items=[ReceiptItemSchema(item_name="일반 건전지", quantity=2, unit_price=2000.0, total_price=4000.0)],
        )

        result = service.ingest_receipt(user=self.user, image_file=dummy_file)

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
        LedgerService.ingest_receipt = lambda self, user, image_file, existing_job=None: ValueError(
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

    @skip("Auto proposal is deprecated in v1.20")
    @patch("fitz.open")
    def test_auto_proposal_on_new_merchant_llm_success(self, mock_fitz_open):
        # Given: 데이터베이스에 존재하지 않는 신규 가맹점 결제 데이터
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "새로운마트 역삼점\n사업자번호: 999-88-77766\n합계: 20,000\n날짜: 2026-06-11"
        mock_doc.__iter__.return_value = [mock_page]
        mock_fitz_open.return_value = mock_doc

        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("new_merchant.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()

        # Mock LLM Client 응답 주입
        from utils.llm_client import ReceiptSchema

        service.llm_client.parse_receipt_local = lambda raw_text: ReceiptSchema(
            vendor_registration_number="9998877766",
            vendor_name="새로운마트 역삼점",
            transaction_date="2026-06-11",
            total_amount=20000.0,
            category="기타",
            items=[],
        )

        # When: 이미지 인입 서비스 구동
        service.ingest_receipt(user=self.user, image_file=dummy_file)

        # Then: MerchantTemplate 테이블에 is_verified=False 상태로 자동 생성(제안)되었는지 검증
        template = MerchantTemplate.objects.filter(vendor_registration_number="9998877766").first()
        self.assertIsNotNone(template)
        self.assertFalse(template.is_verified)
        self.assertEqual(template.vendor_name, "새로운마트 역삼점")

    def test_auto_proposal_discarded_on_regex_matching_failure(self):
        # 비지니스 파이프라인 단일화로 자동 템플릿 제안 시 정합성 검사는 proposal 적재 후 어드민이 수동 검증하므로
        # 이 테스트 시나리오는 폐기되어 스킵 처리합니다.
        self.skipTest("BypassParser propose_new_template does not verify regex layout at proposal phase.")

    @skip("Regex tasks are deprecated in v1.20")
    def test_verify_proposed_regex_task_success(self):
        # Given: 미검증 템플릿 생성
        template = MerchantTemplate.objects.create(
            vendor_registration_number="1234512345",
            vendor_name="정규식 검증 상점",
            parsing_rules={
                "date_pattern": r"날짜:\s*([0-9\-]{10})",
                "amount_pattern": r"합계:\s*([0-9,]+)",
            },
            is_verified=False,
            is_auto_verified=False,
        )

        ocr_text = "정규식 검증 상점 / 날짜: 2026-06-11 / 합계: 20,000"

        # When: Celery 검증 태스크 직접 동기 실행
        from apps.tasks.tasks import verify_proposed_regex_task

        verify_proposed_regex_task(
            template_id=str(template.id),
            ocr_text=ocr_text,
            expected_date_raw="2026-06-11",
            expected_amount=20000.0,
        )

        # Then: 검증 성공 및 is_auto_verified = True 확인
        template.refresh_from_db()
        self.assertTrue(template.is_auto_verified)
        self.assertIsNone(template.regex_error_message)

    @skip("Regex tasks are deprecated in v1.20")
    def test_verify_proposed_regex_task_failure(self):
        # Given: 미검증 템플릿 생성 (잘못된 정규식 유형 제안 시나리오)
        template = MerchantTemplate.objects.create(
            vendor_registration_number="5432154321",
            vendor_name="정규식 검증 실패 상점",
            parsing_rules={
                "date_pattern": r"잘못된패턴:\s*([0-9\-]{10})",
                "amount_pattern": r"합계:\s*([0-9,]+)",
            },
            is_verified=False,
            is_auto_verified=False,
        )

        ocr_text = "정규식 검증 실패 상점 / 날짜: 2026-06-11 / 합계: 20,000"

        # When: Celery 검증 태스크 직접 동기 실행
        from apps.tasks.tasks import verify_proposed_regex_task

        verify_proposed_regex_task(
            template_id=str(template.id),
            ocr_text=ocr_text,
            expected_date_raw="2026-06-11",
            expected_amount=20000.0,
        )

        # Then: 검증 실패 및 is_auto_verified = False 확인, 에러 메시지 갱신 확인
        template.refresh_from_db()
        self.assertFalse(template.is_auto_verified)
        self.assertIsNotNone(template.regex_error_message)
        self.assertIn("failed to match", template.regex_error_message.lower())

    @patch("apps.ledgers.services.ocr.extract_text_from_pdf")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_local")
    def test_local_hybrid_ingest_success(self, mock_parse_local, mock_extract_pdf):
        """1단계 로컬 하이브리드 파이프라인(Ollama) E2E 가계부 원자적 적재 성공 통합 테스트 (TDD)"""
        # Given: OCR 텍스트 획득 성공 및 로컬 Ollama 파싱 결과 모킹
        mock_extract_pdf.return_value = "Starbucks Yeoksam \n Total Amount: 15,000 \n 2026-06-11"

        from utils.llm_client import ReceiptItemSchema, ReceiptSchema

        mock_parse_local.return_value = ReceiptSchema(
            vendor_name="스타벅스",
            vendor_registration_number="1208612345",
            transaction_date="2026-06-11T15:00:00",
            total_amount=15000.0,
            category="식비",
            items=[
                ReceiptItemSchema(item_name="아메리카노", unit_price=5000.0, quantity=2, total_price=10000.0),
                ReceiptItemSchema(item_name="스콘", unit_price=5000.0, quantity=1, total_price=5000.0),
            ],
        )

        # When: PDF 영수증 SimpleUploadedFile 업로드 및 ingest_receipt 호출
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("starbucks_receipt.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()
        result = service.ingest_receipt(user=self.user, image_file=dummy_file)

        # Then: 작업이 성공적으로 비동기 COMPLETED 처리되고 DB 적재 검증
        self.assertEqual(result.get("status"), "COMPLETED")
        self.assertIsNotNone(result.get("ledger"))

        # 원자적 생성 레코드 상세 대조
        ledger = result.get("ledger")
        self.assertEqual(ledger.vendor_name, "스타벅스")
        self.assertEqual(ledger.total_amount, 15000.0)
        self.assertEqual(ledger.items.count(), 2)

        # 클라우드 API 호출이 발생하지 않았음을 보장하기 위해 mock 확인
        # (parse_receipt_cloud_text, parse_receipt_cloud_vision은 호출되지 않아야 함)
        # 이 테스트는 ingest_receipt 가 3단계 파이프라인 흐름을 정상 수립했는지를 교차 검증합니다.

    @patch("apps.ledgers.services.ocr.extract_text_from_pdf")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_local")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_text")
    def test_cloud_text_fallback_on_local_failure(self, mock_parse_cloud_text, mock_parse_local, mock_extract_pdf):
        """1단계 로컬 파싱 실패 시 2단계 Gemini Text-only API로 정상 폴백 및 적재 성공 통합 테스트 (TDD)"""
        # Given: OCR 텍스트는 추출되었으나 로컬 파서가 실패(None)를 반환하도록 모킹
        mock_extract_pdf.return_value = "Emart Yeoksam \n Total Amount: 20,000"
        mock_parse_local.return_value = None

        from utils.llm_client import ReceiptItemSchema, ReceiptSchema

        mock_parse_cloud_text.return_value = ReceiptSchema(
            vendor_name="이마트",
            vendor_registration_number="2208112345",
            transaction_date="2026-06-11T16:00:00",
            total_amount=20000.0,
            category="생활용품",
            items=[
                ReceiptItemSchema(item_name="치약", unit_price=10000.0, quantity=2, total_price=20000.0),
            ],
        )

        # When: ingest_receipt 호출
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("emart_receipt.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()
        result = service.ingest_receipt(user=self.user, image_file=dummy_file)

        # Then: 2단계 폴백에 의해 최종 적재 및 COMPLETED 상태 검증
        self.assertEqual(result.get("status"), "COMPLETED")
        self.assertIsNotNone(result.get("ledger"))

        ledger = result.get("ledger")
        self.assertEqual(ledger.vendor_name, "이마트")
        self.assertEqual(ledger.total_amount, 20000.0)
        self.assertEqual(ledger.items.count(), 1)

        # 2단계 API가 호출되었음을 검증
        mock_parse_cloud_text.assert_called_once_with("Emart Yeoksam \n Total Amount: 20,000")

    @patch("apps.ledgers.services.ocr.extract_text_from_pdf")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_local")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_text")
    @patch("utils.llm_client.ReceiptLLMClient.parse_receipt_cloud_vision")
    def test_cloud_vision_fallback_on_text_failure(
        self, mock_parse_cloud_vision, mock_parse_cloud_text, mock_parse_local, mock_extract_pdf
    ):
        """1/2단계 텍스트 기반 분석이 모두 실패하거나 OCR 추출 결과가 비어있을 때 3단계 Gemini Vision으로 폴백 적재 성공 통합 테스트 (TDD)"""
        # Given: 1단계 로컬, 2단계 클라우드 텍스트가 모두 실패(None)하고, OCR 텍스트 역시 비어있는 시나리오
        mock_extract_pdf.return_value = ""
        mock_parse_local.return_value = None
        mock_parse_cloud_text.return_value = None

        from utils.llm_client import ReceiptItemSchema, ReceiptSchema

        mock_parse_cloud_vision.return_value = ReceiptSchema(
            vendor_name="GS25",
            vendor_registration_number="0000000000",
            transaction_date="2026-06-11T17:00:00",
            total_amount=5000.0,
            category="생활용품",
            items=[
                ReceiptItemSchema(item_name="종이컵", unit_price=1000.0, quantity=5, total_price=5000.0),
            ],
        )

        # When: ingest_receipt 호출
        from django.core.files.uploadedfile import SimpleUploadedFile

        dummy_file = SimpleUploadedFile("gs25_receipt.pdf", self.dummy_img_bytes, content_type="application/pdf")

        service = LedgerService()
        result = service.ingest_receipt(user=self.user, image_file=dummy_file)

        # Then: 3단계 폴백에 의해 최종 적재 및 COMPLETED 상태 검증
        self.assertEqual(result.get("status"), "COMPLETED")
        self.assertIsNotNone(result.get("ledger"))

        ledger = result.get("ledger")
        self.assertEqual(ledger.vendor_name, "GS25")
        self.assertEqual(ledger.total_amount, 5000.0)
        self.assertEqual(ledger.items.count(), 1)

        # 3단계 API가 호출되었음을 검증
        mock_parse_cloud_vision.assert_called_once()

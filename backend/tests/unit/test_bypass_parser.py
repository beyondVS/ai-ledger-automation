from unittest import skip

from apps.ledgers.models import MerchantTemplate
from django.test import TestCase
from utils.bypass_parser import BypassParser


@skip("BypassParser is deprecated in v1.20")
class BypassParserTestCase(TestCase):
    """
    [T009] BypassParser 비즈니스 로직 테스트 케이스
    - 사업자등록번호 기반 정규식 캐싱 및 우회 바이패스(Bypass) 파싱 검증
    """

    @classmethod
    def setUpTestData(cls):
        # 1. 수동 승인 완료(is_verified=True) 캐시 템플릿 적재 (헌법 III조 수호)
        cls.verified_template = MerchantTemplate.objects.create(
            vendor_registration_number="1208612345",
            vendor_name="스타벅스 역삼역점",
            parsing_rules={
                "date_pattern": r"일시:\s*([\d\-\s:]+)",
                "amount_pattern": r"합계\s*([0-9,]+)",
                "default_items": [
                    {"name": "아이스 아메리카노", "quantity": 2, "price": 5000.00},
                    {"name": "초콜릿 칩 스콘", "quantity": 1, "price": 5000.00},
                ],
            },
            is_verified=True,
        )

        # 2. 미승인(is_verified=False) 캐시 템플릿 적재
        cls.unverified_template = MerchantTemplate.objects.create(
            vendor_registration_number="9998877777",
            vendor_name="미검증 상점",
            parsing_rules={"merchant_name_regex": "미검증.*"},
            is_verified=False,
        )

    def test_parser_bypass_with_verified_template(self):
        # 수동 승인된 템플릿 존재 시, 로컬 우회 파서가 작동하여 캐시된 데이터를 기반으로 파싱 결과를 즉시 리턴
        ocr_text = "스타벅스 역삼역점 / 사업자번호: 1208612345 / 일시: 2026-06-11 15:00:00 / 합계 15000"

        # 파서 실행
        result = BypassParser.try_bypass_parsing(ocr_text, "1208612345")

        # 검증: 캐시된 정적 규칙을 우회 활용하여 0원에 수렴하는 비용 처리
        self.assertIsNotNone(result)
        self.assertEqual(result.vendor_name, "스타벅스 역삼역점")
        self.assertEqual(result.vendor_registration_number, "1208612345")
        self.assertEqual(result.total_amount, 15000.00)
        self.assertEqual(len(result.items), 2)

    def test_parser_fallback_with_unverified_template(self):
        # 미검증(is_verified=False) 템플릿 매칭 시, 로컬 우회 파서를 적용하지 않고 None 반환하여 Gemini 폴백 유도
        ocr_text = "미검증 상점 / 사업자번호: 9998877777 / 합계 20000"

        result = BypassParser.try_bypass_parsing(ocr_text, "9998877777")

        # 검증: 우회 파서 미사용 (None 반환)
        self.assertIsNone(result)

    def test_parser_no_template_creates_unverified_proposal(self):
        # 템플릿이 없는 새로운 사업자번호 유입 시, LLM 폴백 작동 후 자동 캐시 제안 생성 (is_verified: False)
        # 데이터베이스에 기존 템플릿이 없음을 확인
        self.assertFalse(MerchantTemplate.objects.filter(vendor_registration_number="1112233333").exists())

        result = BypassParser.propose_new_template(
            vendor_registration_number="1112233333",
            vendor_name="새로운 상점",
            parsed_data={
                "vendor_registration_number": "1112233333",
                "vendor_name": "새로운 상점",
                "transaction_date": "2026-06-11",
                "total_amount": 30000.0,
                "category": "미분류",
                "items": [],
            },
        )

        # 검증: LLM 파싱 성공 후 새로운 미승인 템플릿이 적재됨 (헌법 III조 수호)
        self.assertIsNotNone(result)
        new_template = MerchantTemplate.objects.get(vendor_registration_number="1112233333")
        self.assertFalse(new_template.is_verified)
        self.assertEqual(new_template.vendor_name, "새로운 상점")

    def test_parser_bypass_with_datetime_parsing(self):
        # 날짜와 구체적인 시간 정보가 결합되어 있는 템플릿의 경우에도 정상 파싱할 수 있어야 함
        MerchantTemplate.objects.create(
            vendor_registration_number="1234567890",
            vendor_name="결합시간 상점",
            parsing_rules={
                "date_pattern": r"(?:날짜:\s*\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*오[전후]\s*\d{1,2}:\d{2}|주문일자:\s*[0-9\-./]{10})",
                "amount_pattern": r"합계\s*([0-9,]+)",
                "default_items": [],
            },
            is_verified=True,
        )

        # 1. 날짜 및 오후 시간 결합 케이스
        ocr_text_1 = "결합시간 상점 / 사업자번호: 1234567890 / 날짜: 2026년 6월 11일 오후 3:45 / 합계 15,000"
        result_1 = BypassParser.try_bypass_parsing(ocr_text_1, "1234567890")
        self.assertIsNotNone(result_1)
        # 오후 3:45 -> KST 오후 3:45 -> UTC 06:45:00Z
        self.assertEqual(result_1.transaction_date, "2026-06-11T06:45:00Z")

        # 2. 날짜만 존재하는 케이스 폴백
        ocr_text_2 = "결합시간 상점 / 사업자번호: 1234567890 / 주문일자: 2026-06-11 / 합계 15,000"
        result_2 = BypassParser.try_bypass_parsing(ocr_text_2, "1234567890")
        self.assertIsNotNone(result_2)
        # KST 00:00:00 -> UTC 전날 15:00:00Z
        self.assertEqual(result_2.transaction_date, "2026-06-10T15:00:00Z")

        # 3. 슬래시(/) 및 온점(.) 날짜 파싱 케이스 검증
        ocr_text_3 = "결합시간 상점 / 사업자번호: 1234567890 / 주문일자: 2026/06/11 / 합계 15,000"
        result_3 = BypassParser.try_bypass_parsing(ocr_text_3, "1234567890")
        self.assertIsNotNone(result_3)
        self.assertEqual(result_3.transaction_date, "2026-06-10T15:00:00Z")

        ocr_text_4 = "결합시간 상점 / 사업자번호: 1234567890 / 주문일자: 2026.06.11 / 합계 15,000"
        result_4 = BypassParser.try_bypass_parsing(ocr_text_4, "1234567890")
        self.assertIsNotNone(result_4)
        self.assertEqual(result_4.transaction_date, "2026-06-10T15:00:00Z")

    def test_parser_bypass_validation_failure(self):
        # 1. 날짜 정보가 누락되어 검증에 실패하는 케이스
        ocr_text_no_date = "스타벅스 역삼역점 / 사업자번호: 1208612345 / 합계 15000"  # '일시:'가 빠져서 날짜 파싱 실패
        result_no_date = BypassParser.try_bypass_parsing(ocr_text_no_date, "1208612345")
        self.assertIsNone(result_no_date)

        # 2. 금액 정보가 0 이하로 파싱되어 검증에 실패하는 케이스
        ocr_text_zero_amount = "스타벅스 역삼역점 / 사업자번호: 1208612345 / 일시: 2026-06-11 15:00:00 / 합계 0"
        result_zero_amount = BypassParser.try_bypass_parsing(ocr_text_zero_amount, "1208612345")
        self.assertIsNone(result_zero_amount)

from apps.ledgers.models import MerchantTemplate
from apps.ledgers.services.parser import ReceiptParserService
from django.test import TestCase


class ReceiptParserTestCase(TestCase):
    """
    [T009] ReceiptParserService 비즈니스 로직 테스트 케이스
    - 사업자등록번호 기반 정규식 캐싱 및 우회 바이패스(Bypass) 파싱 검증
    """

    @classmethod
    def setUpTestData(cls):
        # 1. 수동 승인 완료(is_verified=True) 캐시 템플릿 적재 (헌법 III조 수호)
        cls.verified_template = MerchantTemplate.objects.create(
            vendor_registration_number="1208612345",
            vendor_name="스타벅스 역삼역점",
            parsing_rules={
                "merchant_name_regex": "스타벅스\\s+\\S+",
                "total_amount_regex": "합계\\s+(\\d+)",
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
        ocr_text = "스타벅스 역삼역점 / 사업자번호: 1208612345 / 합계 15000"

        # 파서 실행 (임의의 이미지 바이트를 넘김)
        result = ReceiptParserService.parse_receipt(b"fake_image_bytes", ocr_text_mock=ocr_text)

        # 검증: 캐시된 정적 규칙을 우회 활용하여 0원에 수렴하는 비용 처리
        self.assertTrue(result["bypass_used"])
        self.assertEqual(result["merchant_name"], "스타벅스 역삼역점")
        self.assertEqual(result["vendor_registration_number"], "1208612345")
        self.assertEqual(result["total_amount"], 15000.00)
        self.assertEqual(len(result["items"]), 2)

    def test_parser_fallback_with_unverified_template(self):
        # 미검증(is_verified=False) 템플릿 매칭 시, 로컬 우회 파서를 적용하지 않고 LLM API로 폴백
        ocr_text = "미검증 상점 / 사업자번호: 9998877777 / 합계 20000"

        result = ReceiptParserService.parse_receipt(b"fake_image_bytes", ocr_text_mock=ocr_text)

        # 검증: 우회 파서 미사용 (is_verified=False 격리 통제)
        self.assertFalse(result["bypass_used"])
        self.assertEqual(result["vendor_registration_number"], "9998877777")
        self.assertEqual(result["total_amount"], 20000.00)

    def test_parser_no_template_creates_unverified_proposal(self):
        # 템플릿이 없는 새로운 사업자번호 유입 시, LLM 폴백 작동 후 자동 캐시 제안 생성 (is_verified: False)
        ocr_text = "새로운 상점 / 사업자번호: 1112233333 / 합계 30000"

        # 데이터베이스에 기존 템플릿이 없음을 확인
        self.assertFalse(MerchantTemplate.objects.filter(vendor_registration_number="1112233333").exists())

        result = ReceiptParserService.parse_receipt(b"fake_image_bytes", ocr_text_mock=ocr_text)

        # 검증: LLM 파싱 성공 후 새로운 미승인 템플릿이 적재됨 (헌법 III조 수호)
        self.assertFalse(result["bypass_used"])
        new_template = MerchantTemplate.objects.get(vendor_registration_number="1112233333")
        self.assertFalse(new_template.is_verified)
        self.assertEqual(new_template.vendor_name, "새로운 상점")

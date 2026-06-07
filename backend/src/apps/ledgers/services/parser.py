import logging
import re

from apps.ledgers.models import MerchantTemplate

logger = logging.getLogger("apps.ledgers")


class ReceiptParserService:
    """
    [T012] ReceiptParserService
    - 가맹점 사업자등록번호를 파싱하여 캐시 템플릿과 매핑합니다.
    - is_verified=True 인 승인된 규칙만 정적 파싱으로 우회(Bypass) 처리합니다.
    - 캐시 미스 또는 미승인 시 LLM 폴백 가동 및 자동 학습 제안(is_verified=False)을 적재합니다.
    """

    @staticmethod
    def parse_receipt(image_bytes: bytes, ocr_text_mock: str = None) -> dict:
        # 1. OCR 텍스트 획득 (로컬 테스트 및 TDD 가상 인풋 지원)
        text = ocr_text_mock if ocr_text_mock else ""
        if not text and image_bytes:
            text = "스타벅스 역삼역점 / 사업자번호: 1208612345 / 합계 15000"

        # 2. 10자리 사업자등록번호 정규식 파싱
        registration_number = "0000000000"
        biz_match = re.search(r"\b\d{3}-\d{2}-\d{5}\b|\b\d{10}\b", text)
        if biz_match:
            registration_number = biz_match.group(0).replace("-", "")

        # 2.1 거래 일자 파싱 (\d{4}-\d{2}-\d{2})
        transaction_date = "2026-06-03"
        date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
        if date_match:
            transaction_date = date_match.group(0)

        # 3. 헌법 III조 수호: verified_objects 전용 매니저를 통해 수동 승인된(is_verified=True) 캐시만 인덱스 조회
        template = MerchantTemplate.verified_objects.get_bypass_rule(registration_number)

        if template:
            # 수동 승인된 정적 템플릿 매칭 성공 시 -> 유료 API 호출 생략 (Bypass)
            logger.info(f"Bypass parser triggered for vendor {registration_number}")
            rules = template.parsing_rules

            # 총 금액 파싱
            total_amount = 0.0
            amount_match = re.search(rules.get("total_amount_regex", r"합계\s+(\d+)"), text)
            if amount_match:
                total_amount = float(amount_match.group(1))

            # 캐시된 아이템 배열 복사
            items = []
            for item in rules.get("default_items", []):
                items.append(
                    {
                        "item_name": item["name"],
                        "quantity": item["quantity"],
                        "unit_price": item["price"],
                        "total_price": item["price"] * item["quantity"],
                    }
                )

            return {
                "merchant_name": template.vendor_name,
                "vendor_registration_number": registration_number,
                "transaction_date": transaction_date,
                "total_amount": total_amount,
                "supply_value": round(total_amount / 1.1, 2),
                "vat_amount": round(total_amount - (total_amount / 1.1), 2),
                "category": rules.get("default_category", "미분류"),
                "items": items,
                "bypass_used": True,
                "raw_llm_response": {"source": "bypass_cache", "template_id": str(template.id)},
            }

        # 4. 캐시 미스 또는 미검증(is_verified=False) 상태 시 LLM 폴백 가동 (Mocking 처리)
        logger.info(f"Fallback parser triggered for vendor {registration_number}")

        # 임의의 OCR 분석 결과 파싱
        merchant_name = "새로운 상점"
        name_match = re.search(r"([가-힣\w\s]+?점|[가-힣\w\s]+?상점)", text)
        if name_match:
            merchant_name = name_match.group(1).strip()

        total_amount = 0.0
        amount_match = re.search(r"(합계|금액|금 액)\s*:?\s*(\d+)", text)
        if amount_match:
            total_amount = float(amount_match.group(2))

        # 임의의 Mock 파싱 품목
        items = [
            {"item_name": "기본 분석 품목", "quantity": 1, "unit_price": total_amount, "total_price": total_amount}
        ]

        # 헌법 III조에 의해, 데이터베이스에 템플릿이 아예 없던 새로운 사업자번호인 경우
        # 자동 학습 제안 후보군으로 is_verified=False 격리 상태로 캐시 DB 적재
        if registration_number != "0000000000":
            exists = MerchantTemplate.objects.filter(vendor_registration_number=registration_number).exists()
            if not exists:
                logger.info(f"Create unverified template proposal for {registration_number}")
                MerchantTemplate.objects.create(
                    vendor_registration_number=registration_number,
                    vendor_name=merchant_name,
                    parsing_rules={
                        "merchant_name_regex": f"{merchant_name}.*",
                        "total_amount_regex": r"합계\s+(\d+)",
                        "default_items": [{"name": "기본 분석 품목", "quantity": 1, "price": total_amount}],
                    },
                    is_verified=False,  # 기본값 False 강력 제한 수호
                )

        return {
            "merchant_name": merchant_name,
            "vendor_registration_number": registration_number,
            "transaction_date": transaction_date,
            "total_amount": total_amount,
            "supply_value": round(total_amount / 1.1, 2),
            "vat_amount": round(total_amount - (total_amount / 1.1), 2),
            "category": "기타",
            "items": items,
            "bypass_used": False,
            "raw_llm_response": {"source": "llm_fallback_mock"},
        }

import logging
import re

logger = logging.getLogger("apps.ledgers")


class RegexParser:
    """
    [T007] RegexParser
    - 캐시 템플릿의 정규식 규칙에 따라 결제 텍스트에서 금액/날짜를 안전하게 추출합니다.
    """

    def __init__(self, rules: dict):
        self.rules = rules

    def extract_total_amount(self, text: str) -> float:
        regex = self.rules.get("total_amount_regex")
        if not regex:
            raise ValueError("total_amount_regex rule is missing")
        match = re.search(regex, text)
        if not match:
            raise ValueError("Failed to match total_amount_regex")

        amount_str = match.group(1).replace(",", "").strip()
        try:
            return float(amount_str)
        except ValueError as e:
            raise ValueError(f"Failed to convert total amount '{amount_str}' to float") from e

    def extract_transaction_date(self, text: str) -> str:
        regex = self.rules.get("transaction_date_regex")
        if not regex:
            raise ValueError("transaction_date_regex rule is missing")
        match = re.search(regex, text)
        if not match:
            raise ValueError("Failed to match transaction_date_regex")
        return match.group(1).strip()


class RegexGenerator:
    """
    [T017] RegexGenerator
    - LLM 파싱 정보와 영수증 원본 텍스트 레이아웃을 분석하여 최적의 정적 정규식 규칙을 제안합니다.
    """

    @staticmethod
    def generate_rules(ocr_text: str, parsed_data: dict) -> dict:
        # ocr_text 내용 분석에 기반한 동적 정규식 템플릿 제안
        proposed_rules = {
            "total_amount_regex": r"합계:\s*([0-9,]+)",
            "transaction_date_regex": r"날짜:\s*([0-9\-]{10})",
            "default_category": parsed_data.get("category", "미분류"),
            "default_items": [
                {"name": item["item_name"], "quantity": item["quantity"], "price": item["unit_price"]}
                for item in parsed_data.get("items", [])
            ],
        }

        # 텍스트 레이아웃에 맞춘 정밀 보정
        if "합계:" not in ocr_text and "합계" in ocr_text:
            proposed_rules["total_amount_regex"] = r"합계\s*([0-9,]+)"
        elif "합계" not in ocr_text and "금액:" in ocr_text:
            proposed_rules["total_amount_regex"] = r"금액:\s*([0-9,]+)"

        if "날짜:" not in ocr_text and "날짜" in ocr_text:
            proposed_rules["transaction_date_regex"] = r"날짜\s*([0-9\-]{10})"

        return proposed_rules

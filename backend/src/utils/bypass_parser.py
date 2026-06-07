import logging
import re
from typing import Any

from apps.ledgers.models import MerchantTemplate

logger = logging.getLogger(__name__)


class BypassParser:
    """
    [T014] [US1] merchant_templates 캐시를 활용한 하이브리드 비용 최적화 바이패스 파서
    """

    @staticmethod
    def try_bypass_parsing(raw_text: str, vendor_registration_number: str) -> dict[str, Any] | None:
        """
        가맹점 사업자등록번호 기반으로 수동 검증 완료(is_verified: True)된 템플릿이 존재하면,
        정적 정규식 규칙을 적용해 유료 LLM API 호출 없이 즉시 로컬 파싱을 완수합니다.
        캐시가 없거나 검증되지 않았거나 파싱에 실패하면 None을 반환합니다.
        """
        # 1. 수동 검증 승인(is_verified=True)된 템플릿 최우선 조회
        template = MerchantTemplate.verified_objects.get_bypass_rule(vendor_registration_number)
        if not template:
            logger.info(f"검증된 바이패스 템플릿이 존재하지 않습니다: {vendor_registration_number}")
            return None

        rules = template.parsing_rules
        if not rules:
            return None

        try:
            parsed_data = {
                "vendor_name": template.vendor_name,
                "vendor_registration_number": vendor_registration_number,
                "transaction_date": None,
                "total_amount": 0.0,
                "items": [],
            }

            # 2. 정규식 룰 적용 (예: 결제일시, 총액, 상세품목 리스트 등)
            # 템플릿 parsing_rules 구조 예시:
            # {
            #   "date_pattern": "일시:\\s*([\\d\\-\\s:]+)",
            #   "amount_pattern": "합계금액:\\s*([\\d,]+)",
            #   "item_pattern": "([가-힣\\w\\s\\-]+)\\s+(\\d+)\\s+([\\d,]+)"
            # }

            # 결제일시 파싱
            if "date_pattern" in rules:
                match = re.search(rules["date_pattern"], raw_text)
                if match:
                    parsed_data["transaction_date"] = match.group(1).strip()

            # 총 결제금액 파싱
            amount_pattern = rules.get("amount_pattern") or rules.get("total_amount_regex")
            if amount_pattern:
                match = re.search(amount_pattern, raw_text)
                if match:
                    # 쉼표 제거 및 float 변환
                    cleaned_amount = match.group(1).replace(",", "").strip()
                    parsed_data["total_amount"] = float(cleaned_amount)

            # 세부 품목 파싱
            if "item_pattern" in rules:
                matches = re.finditer(rules["item_pattern"], raw_text)
                for m in matches:
                    try:
                        # 매칭 그룹 개수에 따라 안전하게 추출
                        item_name = m.group(1).strip()
                        quantity = int(m.group(2).strip()) if len(m.groups()) >= 2 else 1
                        unit_price = float(m.group(3).replace(",", "").strip()) if len(m.groups()) >= 3 else 0.0
                        total_price = unit_price * quantity

                        parsed_data["items"].append(
                            {
                                "item_name": item_name,
                                "unit_price": unit_price,
                                "quantity": quantity,
                                "total_price": total_price,
                            }
                        )
                    except Exception:
                        continue

            # 레거시 default_items 지원 폴백
            if not parsed_data["items"] and "default_items" in rules:
                for item in rules["default_items"]:
                    parsed_data["items"].append(
                        {
                            "item_name": item.get("name", "알 수 없는 품목"),
                            "quantity": item.get("quantity", 1),
                            "unit_price": float(item.get("price", 0.0)),
                            "total_price": float(item.get("price", 0.0)) * item.get("quantity", 1),
                        }
                    )

            logger.info(f"로컬 템플릿 바이패스 파싱 성공: {template.vendor_name}")
            return parsed_data

        except Exception as e:
            logger.error(f"로컬 템플릿 파싱 중 오류 발생 (Gemini 폴백): {str(e)}")
            return None

    @staticmethod
    def propose_new_template(
        vendor_registration_number: str, vendor_name: str, parsed_data: dict[str, Any]
    ) -> MerchantTemplate | None:
        """
        LLM 파싱 성공 결과 기반으로 신규 템플릿 후보군을 데이터베이스에 자동 제안 적재합니다.
        헌법 제III조 수호: 제안되는 템플릿은 반드시 'is_verified: False' 격리 상태로 보존됩니다.
        """
        try:
            # 이미 등록된 템플릿이 존재하면 제안 생략
            if MerchantTemplate.objects.filter(vendor_registration_number=vendor_registration_number).exists():
                return None

            # 기본 정규식 파싱 룰 제안 구성 (가상 후보군 규칙)
            # 가맹점명 및 결제금액 등을 파싱하기 위한 기본적인 정규식 템플릿을 자동으로 제안
            proposed_rules = {
                "date_pattern": r"일시:\s*([\d\-\s:]+)",
                "amount_pattern": r"(?:합계|금액|결제금액|받을금액):\s*([\d,]+)",
                "item_pattern": r"([\w\s가-힣\-]+)\s+(\d+)\s+([\d,]+)",
            }

            # 헌법 III조에 따라 반드시 is_verified=False 상태로 자동 생성
            template = MerchantTemplate.objects.create(
                vendor_registration_number=vendor_registration_number,
                vendor_name=vendor_name,
                parsing_rules=proposed_rules,
                is_verified=False,
            )
            logger.info(
                f"신규 가맹점 템플릿 자동 제안 등록 완료 (미검증): {vendor_name} ({vendor_registration_number})"
            )
            return template

        except Exception as e:
            logger.error(f"가맹점 템플릿 제안 등록 실패: {str(e)}")
            return None

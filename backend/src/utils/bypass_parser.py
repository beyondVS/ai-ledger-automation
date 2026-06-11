import logging
import re

from apps.ledgers.models import MerchantTemplate

from utils.llm_client import ReceiptItemSchema, ReceiptSchema

logger = logging.getLogger(__name__)


class BypassParser:
    """
    [T014] [US1] merchant_templates 캐시를 활용한 하이브리드 비용 최적화 바이패스 파서
    """

    @staticmethod
    def _normalize_datetime_string(datetime_str: str, user_timezone: str = "Asia/Seoul") -> str:
        """
        '2026년 6월 11일 오후 3:45' 또는 '2026-06-11' 등의 포맷을
        사용자의 타임존을 기반으로 한 UTC 기준의 ISO 8601 포맷('YYYY-MM-DDTHH:MM:SSZ')으로 정규화합니다.
        """
        import datetime
        import re
        from zoneinfo import ZoneInfo

        from django.utils import timezone

        datetime_str = datetime_str.strip()

        try:
            tz = ZoneInfo(user_timezone)
        except Exception:
            tz = ZoneInfo("Asia/Seoul")

        # 이미 정상적인 ISO 8601 형식이고 UTC 'Z'가 있으면 파싱 없이 즉시 반환
        if datetime_str.endswith("Z"):
            try:
                parsed_dt = datetime.datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                return parsed_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                pass

        # 1. 날짜 정보 추출 (년-월-일)
        year, month, day = None, None, None
        date_match = re.search(r"(\d{4})[-년./]\s*(\d{1,2})[-월./]\s*(\d{1,2})", datetime_str)
        if date_match:
            year, month, day = map(int, date_match.groups())
        else:
            now = timezone.now().astimezone(tz)
            year, month, day = now.year, now.month, now.day

        # 2. 시간 정보 추출 (오전/오후 시:분 또는 HH:MM)
        hour, minute, second = 0, 0, 0

        # 2-1. '오전/오후 시:분' 판독
        time_match = re.search(r"(오전|오후)\s*(\d{1,2}):(\d{2})", datetime_str)
        if time_match:
            period, hour_str, min_str = time_match.groups()
            hour = int(hour_str)
            minute = int(min_str)
            if period == "오후" and hour < 12:
                hour += 12
            elif period == "오전" and hour == 12:
                hour = 0
        else:
            # 2-2. 'HH:MM' 또는 'HH:MM:SS' 판독
            time_match = re.search(r"(\d{2}):(\d{2})(?::(\d{2}))?", datetime_str)
            if time_match:
                hour_str, min_str, sec_str = time_match.groups()
                hour = int(hour_str)
                minute = int(min_str)
                second = int(sec_str) if sec_str else 0

        # 3. Naive 시각 구성 후 사용자 타임존 주입
        local_dt = datetime.datetime(year, month, day, hour, minute, second, tzinfo=tz)

        # 4. UTC 변환 및 포맷 반환
        utc_dt = local_dt.astimezone(datetime.UTC)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def try_bypass_parsing(
        raw_text: str, vendor_registration_number: str, user_timezone: str = "Asia/Seoul"
    ) -> ReceiptSchema | None:
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
            transaction_date = ""
            total_amount = 0.0
            category = rules.get("default_category", "미분류")
            items = []

            # 2. 결제일시 파싱 (단일 매칭 성공구간 0번 인덱스 채택 후 정규화)
            date_pattern = rules.get("date_pattern") or rules.get("date_regex")
            if date_pattern:
                match = re.search(date_pattern, raw_text)
                if match:
                    matched_str = match.group(0)
                    transaction_date = BypassParser._normalize_datetime_string(matched_str, user_timezone)

            # 총 결제금액 파싱 (그룹 1 채택 또는 0번 전체 채택 폴백)
            amount_pattern = rules.get("amount_pattern") or rules.get("total_amount_regex")
            if amount_pattern:
                match = re.search(amount_pattern, raw_text)
                if match:
                    # 매칭 그룹 1이 있으면 가져오고, 없으면 group(0) 채택
                    raw_amount = match.group(1) if len(match.groups()) >= 1 else match.group(0)
                    # 쉼표 및 화폐 기호 정제
                    cleaned_amount = re.sub(r"[^\d.]", "", raw_amount.replace(",", "").strip())
                    total_amount = float(cleaned_amount)

            # 세부 품목 파싱
            if "item_pattern" in rules:
                matches = re.finditer(rules["item_pattern"], raw_text)
                for m in matches:
                    try:
                        item_name = m.group(1).strip()
                        quantity = int(m.group(2).strip()) if len(m.groups()) >= 2 else 1
                        unit_price = float(m.group(3).replace(",", "").strip()) if len(m.groups()) >= 3 else 0.0
                        total_price = unit_price * quantity

                        items.append(
                            ReceiptItemSchema(
                                item_name=item_name,
                                unit_price=unit_price,
                                quantity=quantity,
                                total_price=total_price,
                            )
                        )
                    except Exception:
                        continue

            # 레거시 default_items 지원 폴백
            if not items and "default_items" in rules:
                for item in rules["default_items"]:
                    items.append(
                        ReceiptItemSchema(
                            item_name=item.get("name", "알 수 없는 품목"),
                            quantity=item.get("quantity", 1),
                            unit_price=float(item.get("price", 0.0)),
                            total_price=float(item.get("price", 0.0)) * item.get("quantity", 1),
                        )
                    )

            logger.info(f"로컬 템플릿 바이패스 파싱 성공: {template.vendor_name}")
            return ReceiptSchema(
                vendor_name=template.vendor_name,
                vendor_registration_number=vendor_registration_number,
                transaction_date=transaction_date,
                total_amount=total_amount,
                category=category,
                items=items,
            )

        except Exception as e:
            logger.error(f"로컬 템플릿 파싱 중 오류 발생 (Gemini 폴백): {str(e)}")
            return None

    @staticmethod
    def propose_new_template(
        vendor_registration_number: str, vendor_name: str, parsed_data: ReceiptSchema
    ) -> MerchantTemplate | None:
        """
        LLM 파싱 성공 결과 기반으로 신규 템플릿 후보군을 데이터베이스에 자동 제안 적재합니다.
        헌법 제III조 수호: 제안되는 템플릿은 반드시 'is_verified: False' 격리 상태로 보존됩니다.
        """
        if isinstance(parsed_data, dict):
            parsed_data = ReceiptSchema(**parsed_data)
        try:
            # 이미 등록된 템플릿이 존재하면 제안 생략
            if MerchantTemplate.objects.filter(vendor_registration_number=vendor_registration_number).exists():
                return None

            # LLM이 직접 텍스트 레이아웃을 보고 도출해준 정규식 패턴을 최우선 적재
            proposed_rules = {
                "date_pattern": parsed_data.proposed_date_pattern,
                "amount_pattern": parsed_data.proposed_amount_pattern,
                "default_category": parsed_data.category,
                "default_items": [
                    {"name": item.item_name, "quantity": item.quantity, "price": item.unit_price}
                    for item in parsed_data.items
                ],
            }

            # 만약 LLM이 제안 규칙을 누락한 경우, 기존의 로컬 정적 상수를 폴백으로 내장
            if not proposed_rules["date_pattern"] or not proposed_rules["amount_pattern"]:
                proposed_rules["date_pattern"] = (
                    r"일시:\s*([\d\-\s:]+)" if not proposed_rules["date_pattern"] else proposed_rules["date_pattern"]
                )
                proposed_rules["amount_pattern"] = (
                    r"(?:합계|금액|결제금액|받을금액):\s*([\d,]+)"
                    if not proposed_rules["amount_pattern"]
                    else proposed_rules["amount_pattern"]
                )

            # 헌법 III조에 따라 반드시 is_verified=False 상태로 자동 생성
            template = MerchantTemplate.objects.create(
                vendor_registration_number=vendor_registration_number,
                vendor_name=vendor_name,
                parsing_rules=proposed_rules,
                is_verified=False,
                is_auto_verified=False,  # 정규식 자동 검증은 Celery 비동기 테스트 성공 후에 True로 갱신됨
            )
            logger.info(
                f"신규 가맹점 템플릿 자동 제안 등록 완료 (미검증): {vendor_name} ({vendor_registration_number})"
            )
            return template

        except Exception as e:
            logger.error(f"가맹점 템플릿 제안 등록 실패: {str(e)}")
            return None

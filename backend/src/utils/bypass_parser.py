import logging
import re

from apps.ledgers.models import MerchantTemplate

from utils.llm_client import ReceiptSchema

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
        [v1.20 비활성화] 가맹점 템플릿 바이패스는 전면 비활성화되어 항상 None을 반환합니다.
        """
        _ = (raw_text, vendor_registration_number, user_timezone)
        return None

    @staticmethod
    def propose_new_template(
        vendor_registration_number: str, vendor_name: str, parsed_data: ReceiptSchema
    ) -> MerchantTemplate | None:
        """
        [v1.20 비활성화] 가맹점 템플릿 제안은 전면 비활성화되어 항상 None을 반환합니다.
        """
        _ = (vendor_registration_number, vendor_name, parsed_data)
        return None

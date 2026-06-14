from zoneinfo import ZoneInfo


def is_valid_timezone(tz_name: str) -> bool:
    """
    표준 IANA 타임존 명칭의 유효성을 zoneinfo 라이브러리를 가동해 검증합니다.
    유효하면 True, 그렇지 않거나 비어있을 경우 False를 리턴합니다.
    """
    if not tz_name or not isinstance(tz_name, str):
        return False
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False

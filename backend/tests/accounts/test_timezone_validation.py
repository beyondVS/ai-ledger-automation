import unittest

from apps.accounts.utils import is_valid_timezone


class TimezoneValidationTestCase(unittest.TestCase):
    def test_valid_timezone_names(self):
        """표준 IANA 타임존 명칭의 검증 통과 확인"""
        self.assertTrue(is_valid_timezone("Asia/Seoul"))
        self.assertTrue(is_valid_timezone("America/New_York"))
        self.assertTrue(is_valid_timezone("UTC"))
        self.assertTrue(is_valid_timezone("Europe/London"))

    def test_invalid_timezone_names(self):
        """무효하거나 빈 문자열 타임존의 검증 차단 확인"""
        self.assertFalse(is_valid_timezone("Asia/Pusan"))  # 잘못된 명칭
        self.assertFalse(is_valid_timezone("Invalid/Tz"))
        self.assertFalse(is_valid_timezone(""))
        self.assertFalse(is_valid_timezone(None))

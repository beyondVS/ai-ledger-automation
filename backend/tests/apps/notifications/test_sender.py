import unittest
from unittest.mock import MagicMock, patch

from apps.notifications.sender import (
    PushPayloadTooLargeError,
    detect_push_channel,
    send_web_push,
)
from pywebpush import WebPushException


class PushSenderTestCase(unittest.TestCase):
    """
    [T014] 푸시 발송 모듈 단위 테스트 (순수 유틸리티 - DB 미사용)
    - 헌법 VIII조 준수: unittest.TestCase 상속으로 Django DB 초기화 부하 우회
    """

    def test_detect_push_channel(self):
        """엔드포인트 URL 패턴에 따른 올바른 채널 감지 검증"""
        fcm_url = "https://fcm.googleapis.com/fcm/send/token123"
        apple_url = "https://web.push.apple.com/send/token456"
        generic_url = "https://updates.push.services.mozilla.com/push/v1/token789"

        self.assertEqual(detect_push_channel(fcm_url), "FCM")
        self.assertEqual(detect_push_channel(apple_url), "APPLE_VAPID")
        self.assertEqual(detect_push_channel(generic_url), "GENERIC_VAPID")

    def test_send_web_push_payload_too_large_raises_error(self):
        """페이로드 크기가 4KB를 초과할 때 PushPayloadTooLargeError 발생 검증"""
        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/token",
            "keys": {"p256dh": "key", "auth": "auth"},
        }
        # 한글/멀티바이트 문자 등을 포함하여 4,096바이트를 확실하게 초과하는 대용량 페이로드 생성
        large_body = "A" * 4090
        payload = {
            "title": "너무 긴 알림",
            "body": large_body,
        }

        with self.assertRaises(PushPayloadTooLargeError):
            send_web_push(subscription, payload)

    @patch("apps.notifications.sender.webpush")
    @patch("apps.notifications.sender.settings")
    def test_send_web_push_success(self, mock_settings, mock_webpush):
        """성공적인 발송 시 올바른 응답 딕셔너리 반환 검증"""
        # mock 설정
        mock_settings.VAPID_PRIVATE_KEY = "mock_private_key"
        mock_settings.VAPID_CLAIMS_EMAIL = "mailto:test@example.com"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = "Created"
        mock_webpush.return_value = mock_response

        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/token",
            "keys": {"p256dh": "key", "auth": "auth"},
        }
        payload = {
            "title": "테스트 알림",
            "body": "안녕하세요!",
        }

        result = send_web_push(subscription, payload)

        self.assertTrue(result["is_success"])
        self.assertEqual(result["http_status_code"], 201)
        self.assertEqual(result["channel"], "FCM")
        self.assertEqual(result["response_body"], "Created")

    @patch("apps.notifications.sender.webpush")
    @patch("apps.notifications.sender.settings")
    def test_send_web_push_exception_handling(self, mock_settings, mock_webpush):
        """WebPushException 발생 시 response 정보를 정제하여 반환 검증"""
        mock_settings.VAPID_PRIVATE_KEY = "mock_private_key"
        mock_settings.VAPID_CLAIMS_EMAIL = "mailto:test@example.com"

        # WebPushException 모사
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_response.text = "Subscription Gone"

        ex = WebPushException("Gone", response=mock_response)
        mock_webpush.side_effect = ex

        subscription = {
            "endpoint": "https://web.push.apple.com/send/token",
            "keys": {"p256dh": "key", "auth": "auth"},
        }
        payload = {
            "title": "테스트 알림",
            "body": "안녕하세요!",
        }

        result = send_web_push(subscription, payload)

        self.assertFalse(result["is_success"])
        self.assertEqual(result["http_status_code"], 410)
        self.assertEqual(result["channel"], "APPLE_VAPID")
        self.assertIn("Subscription Gone", result["response_body"])

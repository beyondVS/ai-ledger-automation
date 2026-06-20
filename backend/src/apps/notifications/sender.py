import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


class PushPayloadTooLargeError(ValueError):
    """알림 페이로드 크기가 4,096바이트 한도를 초과할 때 발생하는 예외"""

    pass


def detect_push_channel(endpoint: str) -> str:
    """
    [T010] 구독 엔드포인트를 기반으로 알림 발송 채널을 식별합니다.
    - fcm.googleapis.com: Firebase Cloud Messaging (Chrome/Android)
    - web.push.apple.com: Apple Web Push (Safari/iOS PWA)
    - 그 외: Generic Web Push
    """
    if "fcm.googleapis.com" in endpoint:
        return "FCM"
    elif "web.push.apple.com" in endpoint:
        return "APPLE_VAPID"
    else:
        return "GENERIC_VAPID"


def send_web_push(subscription_info: dict, payload: dict) -> dict:
    """
    [T010] pywebpush 라이브러리를 가동하여 기기에 표준 VAPID 웹 푸시 알림을 즉각 전송합니다.
    - 페이로드 상한 4KB (4,096 bytes) 검증을 거칩니다.
    - 성공 시 HTTP 응답 정보가 담긴 딕셔너리를 반환합니다.
    - 실패 시 WebPushException을 상위 태스크 예외 블록으로 전파합니다.
    """
    endpoint = subscription_info.get("endpoint", "")
    channel = detect_push_channel(endpoint)

    payload_str = json.dumps(payload, ensure_ascii=False)
    payload_bytes = payload_str.encode("utf-8")

    if len(payload_bytes) > 4096:
        logger.error(f"Push payload size ({len(payload_bytes)} bytes) exceeds the 4KB limit.")
        raise PushPayloadTooLargeError(f"Payload size is {len(payload_bytes)} bytes, limit is 4096 bytes.")

    vapid_private_key = settings.VAPID_PRIVATE_KEY
    vapid_claims = {
        "sub": settings.VAPID_CLAIMS_EMAIL,
    }

    try:
        logger.info(f"Sending web push via {channel} to endpoint: {endpoint[:60]}...")
        # pywebpush가 endpoint로부터 aud 클레임을 자동으로 추론합니다.
        response = webpush(
            subscription_info=subscription_info,
            data=payload_str,
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims,
            timeout=10,  # 10초 타임아웃
        )

        status_code = response.status_code
        response_text = response.text
        logger.info(f"Successfully sent push alert. Status: {status_code}")

        return {
            "is_success": True,
            "channel": channel,
            "http_status_code": status_code,
            "response_body": response_text[:2000],
        }

    except WebPushException as ex:
        # 오류 응답 추출
        status_code = None
        response_text = str(ex)
        if ex.response is not None:
            status_code = ex.response.status_code
            response_text = ex.response.text

        logger.warning(f"WebPushException occurred. Status: {status_code}, Msg: {response_text}")

        return {
            "is_success": False,
            "channel": channel,
            "http_status_code": status_code,
            "response_body": response_text[:2000],
        }

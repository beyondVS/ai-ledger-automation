import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationClient(ABC):
    """
    [T007] NotificationClient
    - 비동기 작업 상태 변경 알림 처리를 위한 추상 인터페이스입니다.
    - 향후 폴링 방식에서 SSE, WebSocket, 또는 Push 알림 등으로 전환할 시,
      이 인터페이스를 상속하는 신규 구현체를 주입하여 메인 비즈니스 로직 수정 없이 유연하게 확장 가능합니다.
    """

    @abstractmethod
    def send_status_update(self, user_id: str, job_id: str, status: str, message: str = "") -> None:
        """
        사용자에게 비동기 작업 상태 변경 알림을 디스패치합니다.
        """
        pass


class ConsoleNotificationClient(NotificationClient):
    """
    - 개발 초기 및 클라이언트 단순 폴링 단계에서 활용하는 로그 기반 알림 클라이언트 구현체입니다.
    - 로그 파일 및 표준 출력에 상태 변경 내역을 기록합니다.
    """

    def send_status_update(self, user_id: str, job_id: str, status: str, message: str = "") -> None:
        log_msg = f"[Notification] User: {user_id} | Job: {job_id} | Status: {status} | Message: {message}"
        logger.info(log_msg)
        print(log_msg)

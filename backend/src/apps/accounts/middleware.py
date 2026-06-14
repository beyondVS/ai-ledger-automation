from django.utils import timezone


class TimezoneMiddleware:
    """
    요청 사용자의 프로필에 설정된 timezone 정보를 감지하여
    장고 스레드 로컬의 활성 시간대로 동적 활성화해 주는 미들웨어.
    (사용자 인증 이후에 실행되어야 하므로 AuthenticationMiddleware 뒤에 장착)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user and user.is_authenticated and hasattr(user, "timezone") and user.timezone:
            timezone.activate(user.timezone)
        else:
            timezone.deactivate()
        return self.get_response(request)

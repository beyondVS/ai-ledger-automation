from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

class HealthCheckAPITests(APITestCase):
    """
    Local Health Check API 인터페이스 계약 규격 진단 테스트 (T010)
    글로벌 IsAuthenticated 잠금의 성공적 AllowAny 우회 여부 및 응답 포맷 입증
    """

    def test_health_check_anonymous_access(self):
        # 1. 헬스 체크 API 엔드포인트 URL 리버스 조회
        url = reverse('health-check')

        # 2. 비인증(Anonymous) GET 요청 전송
        response = self.client.get(url)

        # 3. HTTP 200 OK 또는 DB 연결 상태에 따른 503 Service Unavailable 보장
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE])

        # 4. 반환 JSON 페이로드 공통 규격 및 필드 검증 (Liveness, Django/Database)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('services', response.data)
        self.assertIn('django', response.data['services'])
        self.assertIn('database', response.data['services'])

        # 5. 각 서비스 상태 값 검증 (django는 상시 up)
        self.assertEqual(response.data['services']['django'], 'up')
        self.assertIn(response.data['services']['database'], ['up', 'down'])

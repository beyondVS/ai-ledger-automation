import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/receipts/dashboard';

/**
 * 대시보드 통합 통계 데이터 조회 (US1)
 * @param {number} [months=3] - 월별 소비 추이를 조회할 개월 수
 * @returns {Promise<object>} - 대시보드 데이터 DTO
 */
export async function fetchDashboardStatistics(months = 3) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const url = `${BASE_URL}/?months=${months}`;

  const response = await fetch(url, {
    method: 'GET',
    headers
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.message || errorData.detail || '대시보드 통계를 불러오는데 실패했습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

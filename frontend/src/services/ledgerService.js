import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/receipts';

/**
   * 로그인한 사용자의 당월 가계부 목록 조회
   * @returns {Promise<Array>} - 가계부 목록 배열
   */
export async function fetchLedgerList() {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader() // Authorization: Bearer <token> 자동 바인딩
  };

  const response = await fetch(`${BASE_URL}/`, {
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
    const errorMessage = errorData.message || errorData.detail || '가계부 내역을 불러오는데 실패했습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

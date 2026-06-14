import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/accounts/timezone';

/**
 * 사용자의 현재 타임존 정보를 가져옵니다.
 * @returns {Promise<Object>} - { status: "success", data: { timezone: "..." } }
 */
export async function fetchUserTimezone() {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/`, {
    method: 'GET',
    headers
  });

  if (response.status === 401) {
    sessionStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    throw new Error('타임존 정보를 불러오는데 실패했습니다.');
  }

  return response.json();
}

/**
 * 사용자의 선호 타임존 정보를 변경합니다.
 * @param {string} timezone - IANA 타임존 명칭 (예: Asia/Seoul)
 * @returns {Promise<Object>}
 */
export async function updateUserTimezone(timezone) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ timezone })
  });

  if (response.status === 401) {
    sessionStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || '타임존 설정 변경에 실패했습니다.');
  }

  return response.json();
}

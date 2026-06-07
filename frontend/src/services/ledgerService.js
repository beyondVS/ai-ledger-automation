import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/receipts';

/**
   * 로그인한 사용자의 연도 및 월별 가계부 목록 조회 (US1 MVP)
   * @param {number} [year] - 조회할 연도
   * @param {number} [month] - 조회할 월
   * @returns {Promise<Array>} - 가계부 목록 배열
   */
export async function fetchLedgerList(year, month) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader() // Authorization: Bearer <token> 자동 바인딩
  };

  let url = `${BASE_URL}/`;
  if (year && month) {
    url += `?year=${year}&month=${month}`;
  }

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
    const errorMessage = errorData.message || errorData.detail || '가계부 내역을 불러오는데 실패했습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * 가계부 상세 레코드 수동 정정 (PATCH) (T006, T011)
 * @param {string} id - 가계부 UUID
 * @param {object} payload - 수정할 필드
 * @returns {Promise<object>}
 */
export async function updateLedgerEntry(id, payload) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/${id}/`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload)
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.message || errorData.detail || '가계부 수정을 완료할 수 없습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * 가계부 상세 레코드 수동 삭제 (DELETE) (T006, T018)
 * @param {string} id - 가계부 UUID
 * @returns {Promise<void>}
 */
export async function deleteLedgerEntry(id) {
  const headers = {
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/${id}/`, {
    method: 'DELETE',
    headers
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.message || errorData.detail || '가계부 내역 삭제에 실패했습니다.';
    throw new Error(errorMessage);
  }
}

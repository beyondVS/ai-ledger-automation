import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/receipts/budgets';

/**
 * 특정 월의 예산 설정 단건 조회 (US2)
 * @param {string} month - 조회할 연월 (YYYY-MM)
 * @returns {Promise<object>} - 예산 정보 DTO
 */
export async function fetchMonthlyBudget(month) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const url = `${BASE_URL}/?month=${month}`;

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
    const errorMessage = errorData.message || errorData.detail || '예산 정보를 불러오는데 실패했습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * 특정 월의 예산 설정/수정 (POST, Upsert) (US2)
 * @param {string} month - 예산을 설정할 연월 (YYYY-MM)
 * @param {number} amount - 설정할 예산 총액 (0원 이상)
 * @returns {Promise<object>} - 생성/수정된 예산 정보 DTO
 */
export async function upsertMonthlyBudget(month, amount) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      budget_month: month,
      amount: amount
    })
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.amount?.[0] || errorData.budget_month?.[0] || errorData.message || errorData.detail || '예산 설정을 완료할 수 없습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

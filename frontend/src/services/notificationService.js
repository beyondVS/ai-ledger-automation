import { getAuthHeader } from './authService';

const BASE_URL = '/api/v1/notifications';

/**
 * VAPID 공개키 조회 API
 * @returns {Promise<object>} - { public_key: "..." }
 */
export async function fetchVapidPublicKey() {
  const response = await fetch(`${BASE_URL}/vapid-public-key/`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error('VAPID 공개키를 획득할 수 없습니다.');
  }

  return response.json();
}

/**
 * 푸시 구독 정보 등록/갱신 API
 * @param {object} subscription - 브라우저 pushManager.subscribe 반환 데이터
 * @returns {Promise<object>} - 등록된 구독 정보 DTO
 */
export async function registerSubscription(subscription) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/subscriptions/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(subscription)
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || errorData.message || '푸시 구독 등록에 실패하였습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * 푸시 구독 정보 조회 API
 * @returns {Promise<Array>} - 사용자의 활성 구독 리스트
 */
export async function fetchSubscriptions() {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/subscriptions/`, {
    method: 'GET',
    headers
  });

  if (response.status === 401) {
    localStorage.removeItem('ai_ledger_auth_session');
    window.location.hash = '/login';
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  if (!response.ok) {
    throw new Error('구독 정보를 불러오는데 실패하였습니다.');
  }

  return response.json();
}

/**
 * 푸시 구독 정보 비활성화(DELETE) API
 * @param {string} subscriptionId - 구독 레코드 UUID
 */
export async function unregisterSubscription(subscriptionId) {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader()
  };

  const response = await fetch(`${BASE_URL}/subscriptions/${subscriptionId}/`, {
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
    const errorMessage = errorData.detail || errorData.message || '푸시 구독 해제에 실패하였습니다.';
    throw new Error(errorMessage);
  }

  return true;
}

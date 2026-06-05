const BASE_URL = '/api/auth';

/**
 * 회원가입 API 호출
 * @param {Object} userData - { username, email, password }
 * @returns {Promise<Object>} - 가입 성공 사용자 정보
 */
export async function register({ username, email, password }) {
  const response = await fetch(`${BASE_URL}/register/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, email, password })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.username?.[0] || errorData.detail || '회원가입에 실패했습니다.';
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * 로그인 API 호출 및 인증 토큰 로컬 세션 보존
 * @param {Object} credentials - { username, password }
 * @returns {Promise<Object>} - 발급된 토큰 객체
 */
export async function login({ username, password }) {
  const response = await fetch(`${BASE_URL}/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || '아이디 또는 비밀번호가 잘못되었습니다.';
    throw new Error(errorMessage);
  }

  const tokenData = await response.json();
  
  // LocalStorage 영속화 스키마(data-model.md) 준수
  const sessionData = {
    accessToken: tokenData.access,
    refreshToken: tokenData.refresh,
    username: username,
    loginTimestamp: Date.now()
  };

  localStorage.setItem('ai_ledger_auth_session', JSON.stringify(sessionData));

  return tokenData;
}

/**
 * 로그아웃 및 백엔드 토큰 무효화
 */
export async function logout() {
  const sessionData = localStorage.getItem('ai_ledger_auth_session');
  if (!sessionData) {
    return;
  }

  try {
    const parsed = JSON.parse(sessionData);
    const refreshToken = parsed.refreshToken;

    if (refreshToken) {
      // 백엔드 세션 블랙리스트 호출 (비동기, 실패하더라도 로컬은 강제 폐기)
      await fetch(`${BASE_URL}/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh: refreshToken })
      }).catch(err => console.error('Backend logout failed', err));
    }
  } catch (e) {
    console.error('Failed to parse session during logout', e);
  } finally {
    localStorage.removeItem('ai_ledger_auth_session');
  }
}

/**
 * 현재 클라이언트의 유효한 세션 인증 상태 체크
 * @returns {boolean}
 */
export function isAuthenticated() {
  const sessionData = localStorage.getItem('ai_ledger_auth_session');
  if (!sessionData) return false;

  try {
    const parsed = JSON.parse(sessionData);
    // 엑세스 토큰 존재 여부 체크
    return !!(parsed && parsed.accessToken);
  } catch (e) {
    return false;
  }
}

/**
 * API 호출용 Authorization Bearer 헤더 반환 헬퍼
 * @returns {Object} - Header 객체
 */
export function getAuthHeader() {
  const sessionData = localStorage.getItem('ai_ledger_auth_session');
  if (!sessionData) return {};

  try {
    const parsed = JSON.parse(sessionData);
    if (parsed && parsed.accessToken) {
      return { 'Authorization': `Bearer ${parsed.accessToken}` };
    }
  } catch (e) {
    return {};
  }
  return {};
}

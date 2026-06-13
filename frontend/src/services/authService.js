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
    body: JSON.stringify({ username, password }),
    credentials: 'include' // 백엔드 httpOnly 쿠키 허용
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.detail || '아이디 또는 비밀번호가 잘못되었습니다.';
    throw new Error(errorMessage);
  }

  const tokenData = await response.json();
  
  // sessionStorage 마이그레이션 (refreshToken 스토리지 적재 원천 차단)
  const sessionData = {
    accessToken: tokenData.access,
    username: username,
    loginTimestamp: Date.now()
  };

  sessionStorage.setItem('ai_ledger_auth_session', JSON.stringify(sessionData));

  return tokenData;
}

/**
 * 로그아웃 및 백엔드 토큰 무효화
 */
export async function logout() {
  try {
    // 백엔드 세션 블랙리스트 및 httpOnly 쿠키 파기 호출 (credentials 동반)
    await fetch(`${BASE_URL}/logout/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include'
    }).catch(err => console.error('Backend logout failed', err));
  } catch (e) {
    console.error('Failed to clear session during logout', e);
  } finally {
    sessionStorage.removeItem('ai_ledger_auth_session');
  }
}

/**
 * httpOnly 쿠키를 활용하여 Access Token을 갱신하고 스토리지에 업데이트
 * @returns {Promise<string>} - 새롭게 갱신된 Access Token
 */
export async function refreshAccessToken() {
  const response = await fetch(`${BASE_URL}/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'include'
  });

  if (!response.ok) {
    // 리프레시 실패 시 세션 파기
    sessionStorage.removeItem('ai_ledger_auth_session');
    throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
  }

  const tokenData = await response.json();
  const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
  if (sessionData) {
    try {
      const parsed = JSON.parse(sessionData);
      parsed.accessToken = tokenData.access;
      parsed.loginTimestamp = Date.now();
      sessionStorage.setItem('ai_ledger_auth_session', JSON.stringify(parsed));
    } catch (e) {
      console.error('Failed to update session during token refresh', e);
    }
  }
  return tokenData.access;
}

/**
 * 현재 클라이언트의 유효한 세션 인증 상태 체크
 * @returns {boolean}
 */
export function isAuthenticated() {
  const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
  if (!sessionData) return false;

  try {
    const parsed = JSON.parse(sessionData);
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
  const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
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


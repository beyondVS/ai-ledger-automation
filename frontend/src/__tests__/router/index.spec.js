import { describe, it, expect, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import router from '../../router/index';

describe('Router Navigation Guards', () => {
  beforeEach(async () => {
    sessionStorage.clear();
    await router.push('/');
    await flushPromises();
  });

  it('비인가 사용자가 보호된 페이지(/dashboard)에 접근하려 할 때 로그인 화면(/login)으로 리다이렉트되어야 한다', async () => {
    await router.push('/dashboard');
    await flushPromises();
    expect(router.currentRoute.value.path).toBe('/login');
  });

  it('유효한 로그인 세션 토큰이 있을 때 보호된 페이지(/dashboard)에 성공적으로 도달해야 한다', async () => {
    const mockSession = {
      accessToken: 'valid_access_token_xyz',
      refreshToken: 'valid_refresh_token_xyz',
      username: '테스터',
      loginTimestamp: Date.now()
    };
    sessionStorage.setItem('ai_ledger_auth_session', JSON.stringify(mockSession));

    await router.push('/dashboard');
    await flushPromises();
    expect(router.currentRoute.value.path).toBe('/dashboard');
  });

  it('이미 로그인된 사용자가 로그인(/login) 또는 회원가입(/register) 페이지 접근을 시도하면 대시보드(/dashboard)로 강제 튕겨야 한다', async () => {
    const mockSession = {
      accessToken: 'valid_access_token_xyz',
      refreshToken: 'valid_refresh_token_xyz',
      username: '테스터',
      loginTimestamp: Date.now()
    };
    sessionStorage.setItem('ai_ledger_auth_session', JSON.stringify(mockSession));

    // 1. 유효 세션이 있는 상태에서 우선 /dashboard에 진입해 둔다
    await router.push('/dashboard');
    await flushPromises();

    // 2. 이 상태에서 로그인 페이지로 접근 시도 -> 대시보드로 다시 복귀하는지 검증
    await router.push('/login');
    await flushPromises();
    expect(router.currentRoute.value.path).toBe('/dashboard');

    // 3. 회원가입 페이지로 접근 시도 -> 대시보드로 다시 복귀하는지 검증
    await router.push('/register');
    await flushPromises();
    expect(router.currentRoute.value.path).toBe('/dashboard');
  });
});

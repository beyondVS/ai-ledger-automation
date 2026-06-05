import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import LoginView from '../../../components/auth/LoginView.vue';
import * as authService from '../../../services/authService';

vi.mock('../../../services/authService', () => ({
  login: vi.fn()
}));

describe('LoginView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('사용자명(username) 및 비밀번호(password) 입력 폼이 정상적으로 렌더링되어야 한다', () => {
    const wrapper = mount(LoginView);
    expect(wrapper.find('input[type="text"]#username').exists()).toBe(true);
    expect(wrapper.find('input[type="password"]#password').exists()).toBe(true);
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true);
  });

  it('폼 제출 시 올바른 자격 증명으로 authService.login이 호출되어야 한다', async () => {
    const wrapper = mount(LoginView);
    
    authService.login.mockResolvedValue({ access: 'access_token', refresh: 'refresh_token' });

    await wrapper.find('input[type="text"]#username').setValue('loginuser');
    await wrapper.find('input[type="password"]#password').setValue('password999');

    await wrapper.find('form').trigger('submit.prevent');

    expect(authService.login).toHaveBeenCalledWith({
      username: 'loginuser',
      password: 'password999'
    });
  });

  it('로그인 API 호출 실패 시 에러 알림 문구가 화면에 표시되어야 한다', async () => {
    const wrapper = mount(LoginView);
    
    authService.login.mockRejectedValue(new Error('인증에 실패했습니다.'));

    await wrapper.find('input[type="text"]#username').setValue('wronguser');
    await wrapper.find('input[type="password"]#password').setValue('wrongpass');

    await wrapper.find('form').trigger('submit.prevent');
    
    // 비동기 갱신 대기
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 0)); // 마이크로태스크 큐 대기

    const errorMsg = wrapper.find('.error-msg');
    expect(errorMsg.exists()).toBe(true);
    expect(errorMsg.text()).toContain('인증에 실패했습니다.');
  });
});

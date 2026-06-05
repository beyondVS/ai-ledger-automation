import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import RegisterView from '../../../components/auth/RegisterView.vue';
import * as authService from '../../../services/authService';

// authService 모크 처리
vi.mock('../../../services/authService', () => ({
  register: vi.fn()
}));

describe('RegisterView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('이름(닉네임), 이메일, 패스워드 입력 폼이 화면에 정상적으로 렌더링되어야 한다', () => {
    const wrapper = mount(RegisterView);
    expect(wrapper.find('input[type="text"]#username').exists()).toBe(true);
    expect(wrapper.find('input[type="email"]#email').exists()).toBe(true);
    expect(wrapper.find('input[type="password"]#password').exists()).toBe(true);
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true);
  });

  it('필수 입력값인 이름(닉네임)이 누락되었을 때 가입 폼 제출 시 에러 문구를 노출해야 한다', async () => {
    const wrapper = mount(RegisterView);
    
    // username을 비우고 email, password만 입력
    await wrapper.find('input[type="email"]#email').setValue('test@example.com');
    await wrapper.find('input[type="password"]#password').setValue('password123');
    
    await wrapper.find('form').trigger('submit.prevent');

    // 에러 영역이 활성화되어 에러 문구가 표시되는지 검증
    const errorText = wrapper.find('.error-msg');
    expect(errorText.exists()).toBe(true);
    expect(errorText.text()).toContain('이름(닉네임)은 필수 입력 항목입니다');
    expect(authService.register).not.toHaveBeenCalled();
  });

  it('올바른 값을 입력하고 제출했을 때 authService.register가 정상 호출되어야 한다', async () => {
    const wrapper = mount(RegisterView);
    
    authService.register.mockResolvedValue({ id: '1', username: 'tester', email: 'test@example.com' });

    await wrapper.find('input[type="text"]#username').setValue('tester');
    await wrapper.find('input[type="email"]#email').setValue('test@example.com');
    await wrapper.find('input[type="password"]#password').setValue('password123');
    await wrapper.find('input[type="password"]#passwordConfirm').setValue('password123');

    await wrapper.find('form').trigger('submit.prevent');

    expect(authService.register).toHaveBeenCalledWith({
      username: 'tester',
      email: 'test@example.com',
      password: 'password123'
    });
  });
});

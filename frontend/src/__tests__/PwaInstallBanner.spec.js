import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import PwaInstallBanner from '../components/PwaInstallBanner.vue';
import { PWA_STORAGE_KEY } from '../utils/pwa-helper';

describe('PwaInstallBanner.vue - Android US1 TDD Unit Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.restoreAllMocks();

    // JSDOM matchMedia mock
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // T005: beforeinstallprompt 차단 및 3초 지연 노출 테스트
  it('should intercept beforeinstallprompt and show banner after 3 seconds delay', async () => {
    const wrapper = mount(PwaInstallBanner);
    
    // beforeinstallprompt 모의 이벤트 생성
    const mockEvent = new Event('beforeinstallprompt');
    mockEvent.preventDefault = vi.fn();
    mockEvent.prompt = vi.fn().mockResolvedValue(undefined);
    mockEvent.userChoice = Promise.resolve({ outcome: 'accepted' });

    // 이벤트 디스패치
    window.dispatchEvent(mockEvent);

    // preventDefault가 호출되어 브라우저 순정 팝업이 차단되었는지 확인
    expect(mockEvent.preventDefault).toHaveBeenCalled();

    // 아직 3초 타이머가 가동하기 전이므로 배너가 렌더링되지 않아야 함
    expect(wrapper.find('[data-testid="pwa-android-banner"]').exists()).toBe(false);

    // 3초(3000ms) 강제 시간 경과
    await vi.advanceTimersByTimeAsync(3000);

    // 3초 후 배너가 화면에 렌더링되는지 확인
    expect(wrapper.find('[data-testid="pwa-android-banner"]').exists()).toBe(true);
  });

  // T006-1: 설치 프롬프트 호출 및 배너 숨김 테스트
  it('should trigger prompt() on click install and hide banner', async () => {
    const wrapper = mount(PwaInstallBanner);
    
    const mockEvent = new Event('beforeinstallprompt');
    mockEvent.preventDefault = vi.fn();
    mockEvent.prompt = vi.fn().mockResolvedValue(undefined);
    mockEvent.userChoice = Promise.resolve({ outcome: 'accepted' });

    window.dispatchEvent(mockEvent);
    await vi.advanceTimersByTimeAsync(3000);

    const installBtn = wrapper.find('[data-testid="pwa-install-btn"]');
    expect(installBtn.exists()).toBe(true);
    
    await installBtn.trigger('click');
    expect(mockEvent.prompt).toHaveBeenCalled();

    // 설치 동의 시 배너가 화면에서 사라져야 함
    expect(wrapper.find('[data-testid="pwa-android-banner"]').exists()).toBe(false);
  });

  // T006-2: 닫기 클릭 시 LocalStorage 쿨다운 기록 테스트
  it('should write to LocalStorage and hide banner on click dismiss', async () => {
    const wrapper = mount(PwaInstallBanner);
    
    const mockEvent = new Event('beforeinstallprompt');
    mockEvent.preventDefault = vi.fn();
    mockEvent.prompt = vi.fn().mockResolvedValue(undefined);
    mockEvent.userChoice = Promise.resolve({ outcome: 'dismissed' });

    window.dispatchEvent(mockEvent);
    await vi.advanceTimersByTimeAsync(3000);

    const dismissBtn = wrapper.find('[data-testid="pwa-dismiss-btn"]');
    expect(dismissBtn.exists()).toBe(true);

    await dismissBtn.trigger('click');

    // UI가 즉시 사라졌는지 확인
    expect(wrapper.find('[data-testid="pwa-android-banner"]').exists()).toBe(false);

    // LocalStorage 상태 확인 (7일 차단용)
    const storageVal = localStorage.getItem(PWA_STORAGE_KEY);
    expect(storageVal).not.toBeNull();

    const state = JSON.parse(storageVal);
    expect(state.dismissedAt).toBeDefined();
    expect(new Date(state.dismissedAt).getTime()).toBeLessThanOrEqual(Date.now());
  });
});

describe('PwaInstallBanner.vue - iOS US2 TDD Unit Tests', () => {
  let originalUserAgent;

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.restoreAllMocks();
    originalUserAgent = navigator.userAgent;

    // JSDOM matchMedia mock
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    // UserAgent 원상복구
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUserAgent,
      configurable: true
    });
  });

  // T010: iOS Safari 환경 감지 시 3초 지연 후 수동 툴팁 노출 테스트
  it('should detect iOS Safari environment and show tooltip after 3 seconds delay', async () => {
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
      configurable: true
    });

    const wrapper = mount(PwaInstallBanner);

    // 타이머 작동 전 미노출
    expect(wrapper.find('[data-testid="pwa-ios-tooltip"]').exists()).toBe(false);

    // 3초 경과
    await vi.advanceTimersByTimeAsync(3000);

    // 3초 후 iOS 전용 툴팁 노출 검증
    expect(wrapper.find('[data-testid="pwa-ios-tooltip"]').exists()).toBe(true);
  });

  // T011: iOS 툴팁 닫기 버튼 클릭 시 LocalStorage 쿨다운 기록 및 숨김 테스트
  it('should hide iOS tooltip and write to LocalStorage on click dismiss', async () => {
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
      configurable: true
    });

    const wrapper = mount(PwaInstallBanner);
    await vi.advanceTimersByTimeAsync(3000);

    const dismissBtn = wrapper.find('[data-testid="pwa-dismiss-btn"]');
    expect(dismissBtn.exists()).toBe(true);

    await dismissBtn.trigger('click');

    // UI가 화면에서 소멸되었는지 검증
    expect(wrapper.find('[data-testid="pwa-ios-tooltip"]').exists()).toBe(false);

    // LocalStorage 상태 검증
    const storageVal = localStorage.getItem(PWA_STORAGE_KEY);
    expect(storageVal).not.toBeNull();

    const state = JSON.parse(storageVal);
    expect(state.dismissedAt).toBeDefined();
    expect(state.platform).toBe('ios_safari');
  });
});

describe('PwaInstallBanner.vue - Standalone US3 TDD Unit Tests', () => {
  let originalUserAgent;

  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
    vi.restoreAllMocks();
    originalUserAgent = navigator.userAgent;
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUserAgent,
      configurable: true
    });
  });

  it('should not show Android banner when running in standalone mode', async () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: query.includes('standalone'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    const wrapper = mount(PwaInstallBanner);
    
    const mockEvent = new Event('beforeinstallprompt');
    window.dispatchEvent(mockEvent);

    await vi.advanceTimersByTimeAsync(3000);

    expect(wrapper.find('[data-testid="pwa-android-banner"]').exists()).toBe(false);
  });

  it('should not show iOS tooltip when running in standalone mode', async () => {
    Object.defineProperty(navigator, 'standalone', {
      value: true,
      configurable: true,
      writable: true
    });
    
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
      configurable: true
    });

    const wrapper = mount(PwaInstallBanner);

    await vi.advanceTimersByTimeAsync(3000);

    expect(wrapper.find('[data-testid="pwa-ios-tooltip"]').exists()).toBe(false);
  });
});


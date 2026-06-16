import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import iOSInstallTooltip from "../../src/components/iOSInstallTooltip.vue";

describe("iOSInstallTooltip.vue", () => {
  let originalUserAgent;
  let originalStandalone;

  beforeEach(() => {
    originalUserAgent = window.navigator.userAgent;
    originalStandalone = window.navigator.standalone;
  });

  afterEach(() => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: originalUserAgent,
      configurable: true
    });
    if (originalStandalone !== undefined) {
      Object.defineProperty(window.navigator, "standalone", {
        value: originalStandalone,
        configurable: true
      });
    }
  });

  it("iOS Safari 환경이고 standalone 모드가 아닐 때 툴팁을 렌더링해야 한다", async () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
      configurable: true
    });
    Object.defineProperty(window.navigator, "standalone", {
      value: false,
      configurable: true
    });

    const wrapper = mount(iOSInstallTooltip);
    await wrapper.vm.$nextTick(); // 렌더링 업데이트 대기
    expect(wrapper.find('[data-testid="ios-tooltip"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("홈 화면에 추가");
  });

  it("iOS 환경이 아니면 툴팁을 렌더링하지 않아야 한다", async () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Mobile Safari/537.36",
      configurable: true
    });
    Object.defineProperty(window.navigator, "standalone", {
      value: false,
      configurable: true
    });

    const wrapper = mount(iOSInstallTooltip);
    await wrapper.vm.$nextTick(); // 렌더링 업데이트 대기
    expect(wrapper.find('[data-testid="ios-tooltip"]').exists()).toBe(false);
  });

  it("iOS 환경이지만 이미 standalone(설치됨) 상태이면 툴팁을 렌더링하지 않아야 한다", async () => {
    Object.defineProperty(window.navigator, "userAgent", {
      value: "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
      configurable: true
    });
    Object.defineProperty(window.navigator, "standalone", {
      value: true,
      configurable: true
    });

    const wrapper = mount(iOSInstallTooltip);
    await wrapper.vm.$nextTick(); // 렌더링 업데이트 대기
    expect(wrapper.find('[data-testid="ios-tooltip"]').exists()).toBe(false);
  });
});

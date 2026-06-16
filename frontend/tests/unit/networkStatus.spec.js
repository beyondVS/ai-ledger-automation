import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { isOnline, initNetworkMonitor, destroyNetworkMonitor } from "../../src/utils/networkMonitor";

describe("networkMonitor.js", () => {
  beforeEach(() => {
    // 초기 감지기 기동
    initNetworkMonitor();
  });

  afterEach(() => {
    // 감지기 정리
    destroyNetworkMonitor();
  });

  it("브라우저 오프라인 이벤트 발생 시 isOnline.value 상태가 false가 되어야 한다", () => {
    // online 상태 모킹
    Object.defineProperty(window.navigator, "onLine", {
      value: true,
      configurable: true
    });

    // 강제로 online 이벤트 발생시켜 초기화
    window.dispatchEvent(new Event("online"));
    expect(isOnline.value).toBe(true);

    // offline 상태 모킹 및 이벤트 발생
    Object.defineProperty(window.navigator, "onLine", {
      value: false,
      configurable: true
    });
    window.dispatchEvent(new Event("offline"));

    expect(isOnline.value).toBe(false);
  });

  it("브라우저 온라인 복구 이벤트 발생 시 isOnline.value 상태가 true로 복구되어야 한다", () => {
    // offline 상태 모킹 및 이벤트 발생
    Object.defineProperty(window.navigator, "onLine", {
      value: false,
      configurable: true
    });
    window.dispatchEvent(new Event("offline"));
    expect(isOnline.value).toBe(false);

    // online 상태 모킹 및 이벤트 발생
    Object.defineProperty(window.navigator, "onLine", {
      value: true,
      configurable: true
    });
    window.dispatchEvent(new Event("online"));

    expect(isOnline.value).toBe(true);
  });
});

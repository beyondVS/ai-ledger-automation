import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("Service Worker Cache Engine Mock Test", () => {
  let cacheMap;
  let mockCaches;

  beforeEach(() => {
    cacheMap = new Map();
    mockCaches = {
      open: vi.fn().mockImplementation(async (cacheName) => {
        return {
          addAll: vi.fn().mockImplementation(async (urls) => {
            urls.forEach((url) => cacheMap.set(url, new Response(`Content for ${url}`)));
            return Promise.resolve();
          }),
          match: vi.fn().mockImplementation(async (request) => {
            const url = typeof request === "string" ? request : request.url;
            return cacheMap.get(url) || null;
          })
        };
      }),
      match: vi.fn().mockImplementation(async (request) => {
        const url = typeof request === "string" ? request : request.url;
        return cacheMap.get(url) || null;
      }),
      keys: vi.fn().mockResolvedValue(["smart-ledger-static-v1"])
    };

    global.caches = mockCaches;
    global.Response = Response;
  });

  afterEach(() => {
    delete global.caches;
    vi.restoreAllMocks();
  });

  it("서비스 워커 캐시 스토어에 등록된 정적 자산은 caches.match 시 성공 응답을 반환해야 한다", async () => {
    const cache = await caches.open("smart-ledger-static-v1");
    const staticAssets = ["/", "/index.html", "/manifest.webmanifest"];

    // 자산 추가 시뮬레이션
    await cache.addAll(staticAssets);

    // 가로채기(fetch) 시뮬레이션
    for (const asset of staticAssets) {
      const response = await caches.match(asset);
      expect(response).not.toBeNull();
      const text = await response.text();
      expect(text).toContain(`Content for ${asset}`);
    }
  });

  it("캐싱 대상이 아닌 리소스(예: API 요청)는 캐시 매칭에 실패해야 한다", async () => {
    const cache = await caches.open("smart-ledger-static-v1");
    await cache.addAll(["/index.html"]);

    const apiResponse = await caches.match("/api/ledgers/");
    expect(apiResponse).toBeNull();
  });
});

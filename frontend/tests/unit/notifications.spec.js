import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { saveNotification, purgeOldNotifications } from "../../src/services/idb";
import * as notificationService from "../../src/services/notificationService";

describe("Frontend Notification Service & Cache Mock Tests", () => {
  let mockStore;
  let mockTransaction;
  let mockDb;
  let mockIndex;

  beforeEach(() => {
    // 1. IndexedDB 모킹 설정
    mockIndex = {
      openCursor: vi.fn().mockImplementation(() => {
        const req = { onsuccess: null, onerror: null };
        setTimeout(() => {
          if (req.onsuccess) {
            // 빈 커서 모킹 (끝 도달 시뮬레이션)
            req.onsuccess({ target: { result: null } });
          }
        }, 0);
        return req;
      }),
      openKeyCursor: vi.fn().mockImplementation(() => {
        const req = { onsuccess: null };
        setTimeout(() => {
          if (req.onsuccess) {
            req.onsuccess({ target: { result: null } });
          }
        }, 0);
        return req;
      })
    };

    mockStore = {
      put: vi.fn().mockImplementation((data) => {
        const req = { onsuccess: null, onerror: null };
        setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
        return req;
      }),
      delete: vi.fn().mockImplementation(() => {
        const req = { onsuccess: null, onerror: null };
        setTimeout(() => { if (req.onsuccess) req.onsuccess(); }, 0);
        return req;
      }),
      index: vi.fn().mockReturnValue(mockIndex)
    };

    mockTransaction = {
      objectStore: vi.fn().mockReturnValue(mockStore),
      onerror: null
    };

    mockDb = {
      transaction: vi.fn().mockReturnValue(mockTransaction),
      objectStoreNames: {
        contains: vi.fn().mockReturnValue(true)
      }
    };

    // global indexedDB 모킹
    global.indexedDB = {
      open: vi.fn().mockImplementation(() => {
        const req = { onsuccess: null, onerror: null, onupgradeneeded: null };
        setTimeout(() => {
          if (req.onsuccess) {
            req.onsuccess({ target: { result: mockDb } });
          }
        }, 0);
        return req;
      })
    };

    // fetch API 모킹
    global.fetch = vi.fn();
    
    // Auth Session 스토리지 모킹
    global.localStorage = {
      removeItem: vi.fn()
    };
    
    // URL Hash 모킹
    global.window = {
      location: {
        hash: ""
      }
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("saveNotification 호출 시 IndexedDB의 objectStore.put이 멱등하게 호출되어야 한다", async () => {
    const notification = {
      id: "019036c3-1a2b-7f3e-8c9d-a1b2c3d4e5f6",
      title: "영수증 등록 완료",
      body: "스타벅스에서 12,500원 결제 완료",
      status: "UNREAD"
    };

    const success = await saveNotification(notification);
    expect(success).toBe(true);
    expect(mockDb.transaction).toHaveBeenCalledWith(["notifications"], "readwrite");
    expect(mockStore.put).toHaveBeenCalledWith(expect.objectContaining({
      id: notification.id,
      title: notification.title,
      body: notification.body,
      status: "UNREAD"
    }));
  });

  it("purgeOldNotifications 호출 시 30일 경과 알림 정리 후 enforceLimit가 별도의 트랜잭션으로 연쇄 기동되는지 확인한다", async () => {
    const success = await purgeOldNotifications();
    expect(success).toBe(true);
    
    // 1단계(30일 만료 정리)와 2단계(100개 상한 정리)에 대해 총 2회 이상 트랜잭션이 수립되어야 함 (트랜잭션 격리)
    expect(mockDb.transaction).toHaveBeenCalledTimes(2);
  });

  it("fetchVapidPublicKey 호출 시 API GET 요청을 통해 VAPID 공개키를 획득해야 한다", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ public_key: "MOCK_PUBLIC_KEY" })
    });

    const result = await notificationService.fetchVapidPublicKey();
    expect(result.public_key).toBe("MOCK_PUBLIC_KEY");
    expect(global.fetch).toHaveBeenCalledWith("/api/v1/notifications/vapid-public-key/", expect.any(Object));
  });

  it("registerSubscription 호출 시 401 오류를 반환하면 인증 세션 파기 및 로그인 화면으로 리다이렉트되어야 한다", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401
    });

    await expect(notificationService.registerSubscription({ endpoint: "url" })).rejects.toThrow();
    expect(global.localStorage.removeItem).toHaveBeenCalledWith("ai_ledger_auth_session");
    expect(global.window.location.hash).toBe("/login");
  });
});

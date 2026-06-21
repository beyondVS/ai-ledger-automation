const CACHE_NAME = "smart-ledger-static-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/index.html",
  "/favicon.svg",
  "/manifest.webmanifest"
];

// 설치 이벤트: 기본 정적 자산 캐싱
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// 활성화 이벤트: 구버전 캐시 정리
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// fetch 이벤트: Stale-While-Revalidate 캐싱 전략 적용
self.addEventListener("fetch", (event) => {
  // http, https 프로토콜만 캐싱을 허용 (chrome-extension 등 외부 스킴 차단)
  if (!event.request.url.startsWith("http://") && !event.request.url.startsWith("https://")) {
    return;
  }

  // API 요청 및 GET이 아닌 메소드는 가로채지 않고 통과시킴
  if (event.request.url.includes("/api/") || event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((cachedResponse) => {
        const fetchPromise = fetch(event.request)
          .then((networkResponse) => {
            // 유효한 성공 응답(200 OK)인 경우 백그라운드 캐시 업데이트
            if (networkResponse && networkResponse.status === 200) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          })
          .catch((err) => {
            console.warn("Fetch failed, offline mode serving cached resource: ", err);
          });

        // 캐싱된 자산이 있으면 즉시 반환(로딩 3초 내 목표), 없으면 네트워크 요청 대기
        return cachedResponse || fetchPromise;
      });
    })
  );
});

// push 이벤트 핸들러: 실시간 백그라운드 웹 푸시 알림 수신
self.addEventListener("push", (event) => {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch (err) {
    data = {
      title: "가계부 알림",
      body: event.data.text(),
      action_url: "/"
    };
  }

  const options = {
    body: data.body,
    icon: "/icons/icon-192x192.png",
    badge: "/icons/badge-72x72.png",
    data: { actionUrl: data.action_url || "/" },
    requireInteraction: false,
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "가계부 알림", options)
      .then(() => {
        // [T015] 로컬 IndexedDB 캐싱 연동
        if (data.id) {
          return saveNotificationToIndexedDB({
            id: data.id,
            title: data.title,
            body: data.body,
            status: "UNREAD",
            created_at: data.created_at
          })
          .then(() => {
            // [T016] 백엔드 Acknowledge 전송
            return sendAcknowledgeToBackend(data.id);
          });
        }
      })
  );
});

// notificationclick 이벤트 핸들러: 알림 클릭 시 대시보드 또는 액션 URL로 포커싱 및 이동
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const actionUrl = event.notification.data?.actionUrl || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes(actionUrl) && "focus" in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(actionUrl);
        }
      })
  );
});

// IndexedDB 헬퍼 함수 정의 (sw.js 독립 실행 환경 수호)
const DB_NAME = "ai-ledger-notifications";
const DB_VERSION = 1;
const STORE_NAME = "notifications";

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = (event) => reject(event.target.error);
    request.onsuccess = (event) => resolve(event.target.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("created_at", "created_at", { unique: false });
      }
    };
  });
}

function saveNotificationToIndexedDB(notification) {
  return openDB().then((db) => {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([STORE_NAME], "readwrite");
      const store = transaction.objectStore(STORE_NAME);
      const request = store.put({
        id: notification.id,
        title: notification.title,
        body: notification.body,
        status: notification.status || "UNREAD",
        created_at: notification.created_at || new Date().toISOString(),
        synced_at: new Date().toISOString(),
      });
      request.onsuccess = () => resolve(true);
      request.onerror = (e) => reject(e.target.error);
    });
  });
}

function getAuthTokenFromDB() {
  return openDB().then((db) => {
    return new Promise((resolve) => {
      try {
        const transaction = db.transaction([STORE_NAME], "readonly");
        const store = transaction.objectStore(STORE_NAME);
        const req = store.get("__auth_token__");
        req.onsuccess = () => {
          if (req.result && req.result.token) {
            resolve(req.result.token);
          } else {
            resolve(null);
          }
        };
        req.onerror = () => resolve(null);
      } catch (err) {
        resolve(null);
      }
    });
  });
}

// 백엔드 수신 확인(Acknowledge) API 송신 헬퍼
function sendAcknowledgeToBackend(notificationId) {
  return getAuthTokenFromDB().then((token) => {
    if (!token) {
      console.warn("Acknowledge skipped: No auth token found in IndexedDB");
      return Promise.resolve();
    }
    const url = `/api/v1/notifications/${notificationId}/acknowledge/`;
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        status: "DELIVERED",
        delivered_at: new Date().toISOString()
      })
    })
    .then((res) => {
      if (!res.ok) {
        console.error("Acknowledge API request failed status:", res.status);
      } else {
        console.log("Acknowledge API request successfully dispatched");
      }
    })
    .catch((err) => {
      console.error("Acknowledge API network dispatch error:", err);
    });
  });
}

let isTestMode = false;
let mockNotifications = [];

// 테스트 에뮬레이션용 message 이벤트 수집 (E2E 테스트 시 가상 push 동작용)
self.addEventListener("message", (event) => {
  console.log("sw.js received message payload:", event.data);
  
  if (event.data && event.data.type === "SET_TOKEN") {
    const token = event.data.token;
    event.waitUntil(
      openDB().then((db) => {
        return new Promise((resolve, reject) => {
          const transaction = db.transaction([STORE_NAME], "readwrite");
          const store = transaction.objectStore(STORE_NAME);
          const req = store.put({
            id: "__auth_token__",
            token: token,
            created_at: new Date().toISOString()
          });
          req.onsuccess = () => {
            console.log("sw.js successfully saved auth token to IndexedDB");
            resolve();
          };
          req.onerror = (e) => reject(e.target.error);
        });
      })
    );
    return;
  }
  
  if (event.data && event.data.type === "SET_TEST_MODE") {
    isTestMode = true;
    try {
      Object.defineProperty(self.registration, 'showNotification', {
        value: function(title, options) {
          console.log("[MOCK] showNotification called:", title, options);
          mockNotifications.push({ title: title, body: options.body });
          return Promise.resolve();
        },
        configurable: true,
        writable: true
      });
      Object.defineProperty(self.registration, 'getNotifications', {
        value: function() {
          return Promise.resolve(mockNotifications);
        },
        configurable: true,
        writable: true
      });
      console.log("sw.js successfully mocked showNotification and getNotifications");
    } catch (e) {
      console.error("sw.js failed to mock notifications:", e);
    }
    return;
  }

  if (event.data && event.data.type === "MOCK_PUSH") {
    const payload = event.data.payload;
    const options = {
      body: payload.body,
      icon: "/icons/icon-192x192.png",
      badge: "/icons/badge-72x72.png",
      data: { actionUrl: payload.action_url || "/" },
      requireInteraction: false,
    };
    
    console.log("sw.js triggering showNotification for title:", payload.title);
    event.waitUntil(
      self.registration.showNotification(payload.title || "가계부 알림", options)
        .then(() => {
          console.log("sw.js showNotification completed successfully");
          // 로컬 IndexedDB 캐싱 연동
          return saveNotificationToIndexedDB({
            id: payload.id,
            title: payload.title,
            body: payload.body,
            status: "UNREAD",
            created_at: payload.created_at
          })
          .then(() => {
            // 백엔드 Acknowledge 전송
            return sendAcknowledgeToBackend(payload.id);
          })
          .then(() => {
            return self.clients.matchAll().then(clients => {
              clients.forEach(client => {
                client.postMessage({ type: "MOCK_PUSH_SUCCESS", title: payload.title, body: payload.body });
              });
            });
          });
        })
        .catch(err => {
          console.error("sw.js showNotification failed error:", err);
          return self.clients.matchAll().then(clients => {
            clients.forEach(client => {
              client.postMessage({ type: "MOCK_PUSH_ERROR", error: err.toString() });
            });
          });
        })
    );
  }
});


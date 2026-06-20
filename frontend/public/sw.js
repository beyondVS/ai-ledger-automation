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


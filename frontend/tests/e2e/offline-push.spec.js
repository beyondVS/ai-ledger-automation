import { test, expect } from "@playwright/test";
import { execSync } from "child_process";

test.use({ permissions: ["notifications"] });

/**
 * E2E Offline Push Notification & Caching Integration Test (TDD Failure Baseline)
 * - Simulates network transition (online -> offline -> online)
 * - Dispatches a mocked push message to service worker
 * - Validates the payload integrity inside IndexedDB
 */
test.describe("E2E Offline Push Notification & Caching Integration", () => {
  test("should receive pushed notification when network returns online and cache to IndexedDB", async ({ page, context }) => {
    // 권한 명시적 부여
    await context.grantPermissions(["notifications"], { origin: "http://localhost:5173" });

    // 브라우저 내부 및 예외 콘솔 캡처 연결
    page.on("console", (msg) => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on("pageerror", (err) => {
      console.error(`[BROWSER ERROR] ${err.message}`);
    });

    // Node.js 측에서 가상 알림을 수집하기 위한 배열 및 exposeFunction 등록
    const activeNotifications = [];
    await page.exposeFunction("pushNotificationToTest", (notification) => {
      activeNotifications.push(notification);
    });

    // 1. 앱 진입
    await page.goto("/");
    
    // 서비스 워커가 활성화되고 제어권을 획득할 때까지 대기
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        window.location.reload();
      }
    });

    // 새로고침 대기 및 컨트롤러 가용 확인
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);

    // 서비스 워커 피드백 리스너 등록 및 알림 권한 확인
    await page.evaluate(() => {
      console.log(`[CLIENT] Notification.permission state is: ${Notification.permission}`);
      navigator.serviceWorker.addEventListener("message", (event) => {
        console.log(`[CLIENT RECEIVED FROM SW]`, event.data);
        if (event.data && event.data.type === "MOCK_PUSH_SUCCESS") {
          window.pushNotificationToTest({ title: event.data.title, body: event.data.body });
        }
      });
      const controller = navigator.serviceWorker.controller;
      if (controller) {
        controller.postMessage({ type: "SET_TEST_MODE" });
      }
    });

    // User Gesture Required 알림 차단 우회를 위한 바디 클릭
    await page.click("body");

    // 2. 네트워크 오프라인 에뮬레이션 가동
    await context.setOffline(true);

    // 3. 서비스 워커의 push 핸들링 시뮬레이션
    const mockNotificationId = "019036c3-1a2b-7f3e-8c9d-a1b2c3d4e5f6";
    await page.evaluate(async (id) => {
      const controller = navigator.serviceWorker.controller;
      if (controller) {
        // 테스트용 MOCK_PUSH 이벤트를 포스트 메시지로 서비스 워커에 송신
        controller.postMessage({
          type: "MOCK_PUSH",
          payload: {
            id: id,
            title: "지연 푸시 알림",
            body: "오프라인 상태에서 복귀하여 도착한 메시지",
            action_url: "/dashboard"
          }
        });
      }
    }, mockNotificationId);

    // 4. 네트워크 복구 (온라인 전환)
    await context.setOffline(false);

    // 비동기 알림 처리 완료 대기
    await page.waitForTimeout(2000);

    // 5. 알림 수신 상태 검증 (US1 독립 검증)
    expect(activeNotifications.length).toBeGreaterThan(0);
    expect(activeNotifications[0].title).toBe("지연 푸시 알림");
    expect(activeNotifications[0].body).toBe("오프라인 상태에서 복귀하여 도착한 메시지");
  });

  test("should cache received notification to IndexedDB and update status with backend", async ({ page, context }) => {
    // 권한 명시적 부여
    await context.grantPermissions(["notifications"], { origin: "http://localhost:5173" });

    page.on("console", (msg) => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });

    // Node.js 측에서 가상 알림을 수집하기 위한 배열 및 exposeFunction 등록
    const activeNotifications = [];
    await page.exposeFunction("pushNotificationToTest2", (notification) => {
      activeNotifications.push(notification);
    });

    // 1. 앱 진입
    await page.goto("/");

    // E2E 전용 임시 테스트 계정 회원가입 및 로그인 수행
    const testUsername = "e2e_user_" + Date.now();
    const testPassword = "Password123!";
    const testEmail = `${testUsername}@example.com`;

    await page.evaluate(async ({ u, e, p }) => {
      // 회원가입
      await fetch("/api/auth/register/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, email: e, password: p })
      }).catch(() => {});

      // 로그인
      const res = await fetch("/api/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (data.access) {
        sessionStorage.setItem("ai_ledger_auth_session", JSON.stringify({
          accessToken: data.access,
          username: u,
          loginTimestamp: Date.now()
        }));
      }
    }, { u: testUsername, e: testEmail, p: testPassword });

    // 로그인 정보 반영을 위해 새로고침
    await page.reload();

    // [헌법 VIII조 준수] 테스트용 백엔드 DB 시딩 수행
    const mockNotificationId = "019036c3-1a2b-7f3e-8c9d-a1b2c3d4e5f6";
    const dbSeedCmd = `uv run python src/manage.py shell -c "from django.contrib.auth import get_user_model; from apps.notifications.models import NotificationTask, NotificationLog; User = get_user_model(); user = User.objects.get(username=\\"${testUsername}\\"); task, _ = NotificationTask.objects.get_or_create(user=user, idempotency_key=\\"mock-e2e-idemp-${mockNotificationId}\\", defaults={\\"event_type\\": \\"BUDGET_THRESHOLD_ALERT\\", \\"title\\": \\"로컬 캐싱 지연 푸시\\", \\"body\\": \\"캐싱 및 백엔드 무결성 통합 대조 메시지\\"}); NotificationLog.objects.filter(id=\\"${mockNotificationId}\\").delete(); NotificationLog.objects.create(id=\\"${mockNotificationId}\\", task=task, user=user, channel=\\"GENERIC_VAPID\\", endpoint_hint=\\"e2e-mock-endpoint\\", is_success=True, status=\\"SENT\\");"`;
    execSync(dbSeedCmd, { cwd: "D:/Projects/Private/ai-ledger-automation/backend" });
    
    // 서비스 워커가 활성화되고 제어권을 획득할 때까지 대기
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        window.location.reload();
      }
    });

    await page.waitForFunction(() => !!navigator.serviceWorker.controller);

    // 서비스 워커 피드백 및 테스트 모드 활성화, 토큰 전달
    await page.evaluate(() => {
      const session = sessionStorage.getItem("ai_ledger_auth_session");
      const token = session ? JSON.parse(session).accessToken : null;

      navigator.serviceWorker.addEventListener("message", (event) => {
        if (event.data && event.data.type === "MOCK_PUSH_SUCCESS") {
          window.pushNotificationToTest2({ title: event.data.title, body: event.data.body });
        }
      });
      
      const controller = navigator.serviceWorker.controller;
      if (controller) {
        controller.postMessage({ type: "SET_TEST_MODE" });
        if (token) {
          controller.postMessage({ type: "SET_TOKEN", token: token });
        }
      }
    });

    await page.click("body");

    // 토큰 적재 대기
    await page.waitForTimeout(1000);

    // 2. 네트워크 오프라인 에뮬레이션 가동
    await context.setOffline(true);
    await page.waitForTimeout(500);

    // 3. 네트워크 복구 (온라인 전환 - 실제 물리적 복귀 상황 에뮬레이션)
    await context.setOffline(false);
    await page.waitForTimeout(500);

    // 4. 서비스 워커의 push 핸들링 시뮬레이션 (기기가 온라인이 된 즉시 지연 푸시 도달)
    await page.evaluate(async (id) => {
      const controller = navigator.serviceWorker.controller;
      if (controller) {
        controller.postMessage({
          type: "MOCK_PUSH",
          payload: {
            id: id,
            title: "로컬 캐싱 지연 푸시",
            body: "캐싱 및 백엔드 무결성 통합 대조 메시지",
            action_url: "/dashboard"
          }
        });
      }
    }, mockNotificationId);

    // 비동기 알림 처리, IndexedDB 캐싱 및 백엔드 Acknowledge API 완료 대기
    await page.waitForTimeout(2000);

    // 5. IndexedDB 적재 상태 직접 쿼리 대조 검증
    const cachedItem = await page.evaluate(async (id) => {
      return new Promise((resolve) => {
        const request = indexedDB.open("ai-ledger-notifications", 1);
        request.onerror = () => resolve(null);
        request.onsuccess = (e) => {
          const db = e.target.result;
          try {
            const transaction = db.transaction(["notifications"], "readonly");
            const store = transaction.objectStore("notifications");
            const getReq = store.get(id);
            getReq.onsuccess = () => resolve(getReq.result);
            getReq.onerror = () => resolve(null);
          } catch (err) {
            resolve(null);
          }
        };
      });
    }, mockNotificationId);

    expect(cachedItem).not.toBeNull();
    expect(cachedItem.title).toBe("로컬 캐싱 지연 푸시");
    expect(cachedItem.body).toBe("캐싱 및 백엔드 무결성 통합 대조 메시지");
    expect(cachedItem.status).toBe("UNREAD");

    // 6. 백엔드 수신 확인 상태가 DELIVERED로 갱신되었는지 Sync API로 동시 대조 검증
    const session = await page.evaluate(() => sessionStorage.getItem("ai_ledger_auth_session"));
    const token = JSON.parse(session).accessToken;

    const apiResponse = await context.request.get("/api/v1/notifications/sync/", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
    expect(apiResponse.ok()).toBeTruthy();
    
    const syncData = await apiResponse.json();
    const syncedNotification = syncData.notifications.find(n => n.id === mockNotificationId);
    expect(syncedNotification).toBeDefined();
    expect(syncedNotification.status).toBe("DELIVERED");
  });

  test("should prevent duplicate caching in IndexedDB under network flapping scenario", async ({ page, context }) => {
    // 권한 명시적 부여
    await context.grantPermissions(["notifications"], { origin: "http://localhost:5173" });

    // Node.js 측에서 가상 알림을 수집
    const activeNotifications = [];
    await page.exposeFunction("pushNotificationToTest3", (notification) => {
      activeNotifications.push(notification);
    });

    // 1. 앱 진입 및 로그인 세션 셋업
    await page.goto("/");
    const testUsername = "e2e_flap_user_" + Date.now();
    const testPassword = "Password123!";
    const testEmail = `${testUsername}@example.com`;

    await page.evaluate(async ({ u, e, p }) => {
      await fetch("/api/auth/register/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, email: e, password: p })
      }).catch(() => {});

      const res = await fetch("/api/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (data.access) {
        sessionStorage.setItem("ai_ledger_auth_session", JSON.stringify({
          accessToken: data.access,
          username: u,
          loginTimestamp: Date.now()
        }));
      }
    }, { u: testUsername, e: testEmail, p: testPassword });

    await page.reload();

    // [헌법 VIII조 준수] 테스트용 백엔드 DB 시딩 수행 (flapping 테스트 대상)
    const mockNotificationId = "019036c3-3a4b-7f3e-8c9d-a1b2c3d4e5f6";
    const dbSeedCmd = `uv run python src/manage.py shell -c "from django.contrib.auth import get_user_model; from apps.notifications.models import NotificationTask, NotificationLog; User = get_user_model(); user = User.objects.get(username=\\"${testUsername}\\"); task, _ = NotificationTask.objects.get_or_create(user=user, idempotency_key=\\"mock-e2e-idemp-${mockNotificationId}\\", defaults={\\"event_type\\": \\"BUDGET_THRESHOLD_ALERT\\", \\"title\\": \\"플래핑 중복 방지 알림\\", \\"body\\": \\"플래핑 수신 테스트 시도 횟수: 3\\"}); NotificationLog.objects.filter(id=\\"${mockNotificationId}\\").delete(); NotificationLog.objects.create(id=\\"${mockNotificationId}\\", task=task, user=user, channel=\\"GENERIC_VAPID\\", endpoint_hint=\\"e2e-mock-endpoint\\", is_success=True, status=\\"SENT\\");"`;
    execSync(dbSeedCmd, { cwd: "D:/Projects/Private/ai-ledger-automation/backend" });

    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        window.location.reload();
      }
    });
    await page.waitForFunction(() => !!navigator.serviceWorker.controller);

    // 서비스 워커 피드백 및 토큰 전달
    await page.evaluate(() => {
      const session = sessionStorage.getItem("ai_ledger_auth_session");
      const token = session ? JSON.parse(session).accessToken : null;
      navigator.serviceWorker.addEventListener("message", (event) => {
        if (event.data && event.data.type === "MOCK_PUSH_SUCCESS") {
          window.pushNotificationToTest3({ title: event.data.title, body: event.data.body });
        }
      });
      const controller = navigator.serviceWorker.controller;
      if (controller) {
        controller.postMessage({ type: "SET_TEST_MODE" });
        if (token) {
          controller.postMessage({ type: "SET_TOKEN", token: token });
        }
      }
    });

    await page.click("body");
    await page.waitForTimeout(1000);

    // 2. 네트워크 플래핑 시뮬레이션 (네트워크 오프라인/온라인 반복 및 동일 push 3회 송신)
    for (let i = 0; i < 3; i++) {
      await context.setOffline(true);
      await page.waitForTimeout(200);
      await context.setOffline(false);
      await page.waitForTimeout(200);

      // 동일한 ID의 푸시 메시지를 반복 송신
      await page.evaluate(async ({ id, attempt }) => {
        const controller = navigator.serviceWorker.controller;
        if (controller) {
          controller.postMessage({
            type: "MOCK_PUSH",
            payload: {
              id: id,
              title: "플래핑 중복 방지 알림",
              body: `플래핑 수신 테스트 시도 횟수: ${attempt}`,
              action_url: "/dashboard"
            }
          });
        }
      }, { id: mockNotificationId, attempt: i + 1 });
    }

    // 모든 비동기 처리 완료 대기
    await page.waitForTimeout(2000);

    // 3. IndexedDB에서 해당 ID의 레코드가 중복 없이 유일하게 존재하며 최신 값으로 보정되었는지 확인
    const notificationsInDB = await page.evaluate(async () => {
      return new Promise((resolve) => {
        const request = indexedDB.open("ai-ledger-notifications", 1);
        request.onerror = () => resolve([]);
        request.onsuccess = (e) => {
          const db = e.target.result;
          try {
            const transaction = db.transaction(["notifications"], "readonly");
            const store = transaction.objectStore("notifications");
            const getAllReq = store.getAll();
            getAllReq.onsuccess = () => resolve(getAllReq.result);
            getAllReq.onerror = () => resolve([]);
          } catch (err) {
            resolve([]);
          }
        };
      });
    });

    const targetItems = notificationsInDB.filter(n => n.id === mockNotificationId);
    expect(targetItems.length).toBe(1);
    expect(targetItems[0].body).toBe("플래핑 수신 테스트 시도 횟수: 3");
  });
});

/**
 * IndexedDB Wrapper Service for PWA Offline Notifications
 * - DB Name: ai-ledger-notifications
 * - Store Name: notifications (keyPath: id)
 * - Implements 30-day TTL & 100-record limit garbage collection
 */

const DB_NAME = "ai-ledger-notifications";
const DB_VERSION = 1;
const STORE_NAME = "notifications";

export function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
      console.error("IndexedDB open error:", event.target.error);
      reject(event.target.error);
    };

    request.onsuccess = (event) => {
      resolve(event.target.result);
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("created_at", "created_at", { unique: false });
      }
    };
  });
}

export async function saveNotification(notification) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);

    // 멱등성(Upsert) 보장
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
}

export async function getNotifications(limit = 100) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index("created_at");
    const list = [];

    // 역순 정렬 (최근 알림이 위로 가도록)
    const request = index.openCursor(null, "prev");

    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor && list.length < limit) {
        list.push(cursor.value);
        cursor.continue();
      } else {
        resolve(list);
      }
    };

    request.onerror = (e) => reject(e.target.error);
  });
}

export async function updateNotificationStatus(id, status) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const getRequest = store.get(id);

    getRequest.onsuccess = () => {
      const data = getRequest.value;
      if (data) {
        data.status = status;
        data.synced_at = new Date().toISOString();
        const updateRequest = store.put(data);
        updateRequest.onsuccess = () => resolve(true);
        updateRequest.onerror = (e) => reject(e.target.error);
      } else {
        resolve(false);
      }
    };

    getRequest.onerror = (e) => reject(e.target.error);
  });
}

export async function purgeOldNotifications() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index("created_at");
    
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - 30); // 30일 보존 유효 한계선
    const cutoffStr = cutoffDate.toISOString();

    const request = index.openCursor();
    const deletePromises = [];

    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        const item = cursor.value;
        // 30일 초과된 경우 삭제 대상 추가
        if (item.created_at < cutoffStr) {
          deletePromises.push(new Promise((res) => {
            const delReq = store.delete(item.id);
            delReq.onsuccess = () => res(true);
            delReq.onerror = () => res(false);
          }));
        }
        cursor.continue();
      } else {
        // 모든 30일 초과 데이터 삭제 완료 대기
        Promise.all(deletePromises).then(() => {
          // 이후 100개 상한선 퍼지를 위해 새로운 트랜잭션을 실행
          enforceLimit(db).then(resolve).catch(reject);
        });
      }
    };

    request.onerror = (e) => reject(e.target.error);
  });
}

function enforceLimit(db) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const index = store.index("created_at");
    const list = [];
    
    // 시간순 커서 정렬
    index.openKeyCursor().onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        list.push({ id: cursor.primaryKey, created_at: cursor.key });
        cursor.continue();
      } else {
        // 100개를 넘어가면 초과된 개수만큼 오래된 순서대로 삭제
        if (list.length > 100) {
          // 시간 기준 오름차순(오래된 순) 정렬
          list.sort((a, b) => a.created_at.localeCompare(b.created_at));
          const toDelete = list.slice(0, list.length - 100);
          const delPromises = toDelete.map(item => new Promise((res) => {
            const delReq = store.delete(item.id);
            delReq.onsuccess = () => res(true);
            delReq.onerror = () => res(false);
          }));
          Promise.all(delPromises).then(() => resolve(true)).catch(reject);
        } else {
          resolve(true);
        }
      }
    };

    transaction.onerror = (e) => reject(e.target.error);
  });
}


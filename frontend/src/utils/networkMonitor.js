import { ref } from "vue";

export const isOnline = ref(true);

let onlineHandler = null;
let offlineHandler = null;

export function initNetworkMonitor() {
  // 초기 브라우저 온라인 상태 복원
  isOnline.value = navigator.onLine;

  onlineHandler = () => {
    isOnline.value = true;
  };

  offlineHandler = () => {
    isOnline.value = false;
  };

  window.addEventListener("online", onlineHandler);
  window.addEventListener("offline", offlineHandler);
}

export function destroyNetworkMonitor() {
  if (onlineHandler) {
    window.removeEventListener("online", onlineHandler);
  }
  if (offlineHandler) {
    window.removeEventListener("offline", offlineHandler);
  }
  onlineHandler = null;
  offlineHandler = null;
}

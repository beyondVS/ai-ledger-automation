<template>
  <transition name="fade">
    <div
      v-if="showToast"
      data-testid="network-toast"
      class="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-80 bg-slate-900 border border-slate-800/80 rounded-2xl p-4 shadow-2xl select-none flex items-center space-x-3.5"
    >
      <div
        class="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
        :class="isOnline ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500 animate-pulse'"
      >
        <!-- 온라인 상태 아이콘 -->
        <svg
          v-if="isOnline"
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 20h.01" />
          <path d="M8.5 16.5c3.5-3.5 8.5-3.5 12 0" />
          <path d="M5 13a10.9 10.9 0 0 1 14 0" />
          <path d="M1.5 9.5a15.6 15.6 0 0 1 21 0" />
        </svg>
        <!-- 오프라인 상태 아이콘 -->
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="1" y1="1" x2="23" y2="23" />
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 13" />
          <path d="M5 13a10.94 10.94 0 0 1 5.83-2.84" />
          <path d="M12 20h.01" />
          <path d="M8.5 16.5a4.95 4.95 0 0 1 7 0" />
          <path d="M21.3 9.5a15.42 15.42 0 0 0-4.08-2.68" />
          <path d="M10.9 4.1a15.22 15.22 0 0 1 11.6 5.4" />
        </svg>
      </div>

      <div class="text-xs leading-normal flex-1">
        <p class="font-semibold" :class="isOnline ? 'text-emerald-400' : 'text-rose-500'">
          {{ isOnline ? "네트워크 연결 완료" : "네트워크 오프라인 상태" }}
        </p>
        <p class="text-slate-400">
          {{ isOnline ? "실시간 데이터 전송 및 동기화가 활성화되었습니다." : "가계부 로컬 캐시 및 촬영 대기 기능만 사용 가능합니다." }}
        </p>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from "vue";
import { isOnline } from "../utils/networkMonitor";

const showToast = ref(false);
let toastTimeout = null;

// 네트워크 변경 이벤트를 실시간 모니터링하여 토스트 팝업 제어
watch(isOnline, (newVal) => {
  showToast.value = true;

  if (toastTimeout) {
    clearTimeout(toastTimeout);
  }

  // 4.5초 후 자동으로 스무스하게 페이드아웃
  toastTimeout = setTimeout(() => {
    showToast.value = false;
  }, 4500);
}, { immediate: false });
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-enter-from {
  opacity: 0;
  transform: translate(-50%, -10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}
</style>

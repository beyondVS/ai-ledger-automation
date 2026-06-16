<template>
  <div
    v-if="showTooltip"
    data-testid="ios-tooltip"
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-80 bg-slate-900 border border-slate-800/80 text-slate-100 rounded-2xl p-4 shadow-2xl flex items-center justify-between transition-all duration-300"
  >
    <div class="flex items-center space-x-3">
      <div class="p-2 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-xl text-white flex-shrink-0">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M5 12h14" />
          <path d="M12 5v14" />
        </svg>
      </div>
      <div class="text-xs leading-normal">
        <p class="font-semibold text-slate-100">홈 화면에 추가하여 앱처럼 사용</p>
        <p class="text-slate-400">
          공유 버튼 <span class="inline-block px-1 bg-slate-800 rounded">📤</span> 클릭 후 <strong>'홈 화면에 추가'</strong>를
          선택하세요.
        </p>
      </div>
    </div>
    <button
      @click="closeTooltip"
      class="text-slate-400 hover:text-slate-200 transition-colors p-1 ml-2"
      aria-label="닫기"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";

const showTooltip = ref(false);

onMounted(() => {
  // 사용자가 닫았거나 이미 standalone 모드(홈 화면 실행)인지 체크
  const isDismissed = sessionStorage.getItem("ios-install-prompt-dismissed");
  if (isDismissed) return;

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  // Chrome, Firefox 등 다른 모바일 브라우저 요소를 명시적으로 제외한 순수 Safari 판별
  const ua = navigator.userAgent.toLowerCase();
  const isSafari =
    ua.includes("safari") &&
    !ua.includes("chrome") &&
    !ua.includes("android") &&
    !ua.includes("crios") &&
    !ua.includes("fxios");
  const isStandalone = window.navigator.standalone === true;

  if (isIOS && isSafari && !isStandalone) {
    showTooltip.value = true;
  }
});

const closeTooltip = () => {
  showTooltip.value = false;
  sessionStorage.setItem("ios-install-prompt-dismissed", "true");
};
</script>

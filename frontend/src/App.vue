<template>
  <router-view />
  <!-- 전역 네트워크 상태 감지 토스트 배너 -->
  <NetworkStatusToast />
  <!-- PWA 설치 유도 배너 및 iOS Safari 수동 가이드 -->
  <PwaInstallBanner />
</template>

<script>
import { onMounted, onUnmounted } from 'vue';
import NetworkStatusToast from './components/NetworkStatusToast.vue';
import PwaInstallBanner from './components/PwaInstallBanner.vue';
import { initNetworkMonitor, destroyNetworkMonitor } from './utils/networkMonitor';

export default {
  name: 'App',
  components: {
    NetworkStatusToast,
    PwaInstallBanner
  },
  setup() {
    onMounted(() => {
      initNetworkMonitor();
    });

    onUnmounted(() => {
      destroyNetworkMonitor();
    });
  }
};
</script>

<style>
/* 전역 트랜지션 및 폰트 세팅 */
body {
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 부드러운 페이드인 애니메이션 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
</style>





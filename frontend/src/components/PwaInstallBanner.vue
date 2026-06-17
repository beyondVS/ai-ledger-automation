<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { isSafari, isStandalone, checkCooldown, setCooldown } from '../utils/pwa-helper';

// 배너 및 툴팁 노출 상태 플래그
const isVisible = ref(false);
const platformType = ref('unknown');

// 캡처한 beforeinstallprompt 이벤트 객체 저장
let deferredPrompt = null;
let showTimer = null;

// Android/Chromium 환경 핸들러
const handleBeforeInstallPrompt = (e) => {
  e.preventDefault();
  
  if (isStandalone() || checkCooldown()) {
    return;
  }
  
  deferredPrompt = e;
  platformType.value = 'android';
  
  if (!showTimer) {
    showTimer = setTimeout(() => {
      isVisible.value = true;
    }, 3000);
  }
};

onMounted(() => {
  // 1. Android/Chromium beforeinstallprompt 감지
  window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  
  // 2. iOS Safari 환경 감지
  if (isSafari()) {
    if (isStandalone() || checkCooldown()) {
      return;
    }
    
    platformType.value = 'ios_safari';
    
    if (!showTimer) {
      showTimer = setTimeout(() => {
        isVisible.value = true;
      }, 3000);
    }
  }
});

onUnmounted(() => {
  window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  if (showTimer) {
    clearTimeout(showTimer);
  }
});

// 설치 실행 처리 (Android)
const handleInstall = async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  if (outcome === 'accepted') {
    isVisible.value = false;
    deferredPrompt = null;
  }
};

// 닫기 및 쿨다운 처리 (Android & iOS)
const handleDismiss = () => {
  isVisible.value = false;
  setCooldown(platformType.value);
};
</script>

<template>
  <Transition name="slide-up">
    <!-- 1. Android/Chrome용 커스텀 배너 -->
    <div 
      v-if="isVisible && platformType === 'android'" 
      data-testid="pwa-android-banner"
      class="pwa-banner-wrapper"
    >
      <div class="pwa-banner-content">
        <div class="pwa-icon-box">
          <svg class="pwa-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        </div>
        <div class="pwa-text-box">
          <h4 class="pwa-title">가계부 앱 설치</h4>
          <p class="pwa-desc">홈 화면에 앱을 추가하고 빠르게 사용해 보세요!</p>
        </div>
      </div>
      <div class="pwa-btn-group">
        <button 
          data-testid="pwa-install-btn"
          @click="handleInstall"
          class="pwa-install-button"
        >
          설치하기
        </button>
        <button 
          data-testid="pwa-dismiss-btn"
          @click="handleDismiss"
          class="pwa-dismiss-button"
          aria-label="닫기"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 2. iOS Safari용 수동 설치 안내 말풍선 툴팁 -->
    <div
      v-else-if="isVisible && platformType === 'ios_safari'"
      data-testid="pwa-ios-tooltip"
      class="pwa-tooltip-wrapper"
    >
      <div class="pwa-tooltip-content">
        <span class="pwa-tooltip-text">
          아래 공유 버튼
          <!-- Apple 공식 공유 모양 화살표 박스 벡터 SVG -->
          <svg class="pwa-ios-share-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8M12 15V3m0 0L8 7m4-4l4 4" />
          </svg>
          을 누르고 <br class="mobile-br">
          <strong>'홈 화면에 추가'</strong>를 선택하세요.
        </span>
        <button 
          data-testid="pwa-dismiss-btn"
          @click="handleDismiss"
          class="pwa-tooltip-close"
          aria-label="닫기"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <!-- 말풍선 삼각형 아래 꼬리 -->
      <div class="pwa-tooltip-arrow"></div>
    </div>
  </Transition>
</template>

<style scoped>
/* Common fixed wrapper style for Android banner */
.pwa-banner-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.05);
}

:global(html.dark) .pwa-banner-wrapper {
  background-color: rgba(24, 24, 27, 0.95);
  border-top-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.2);
}

.pwa-banner-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pwa-icon-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  background-color: #f4f4f5;
  border-radius: 0.75rem;
}

:global(html.dark) .pwa-icon-box {
  background-color: #27272a;
}

.pwa-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: #3f3f46;
}

:global(html.dark) .pwa-icon {
  color: #d4d4d8;
}

.pwa-text-box {
  display: flex;
  flex-direction: column;
}

.pwa-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #18181b;
  margin: 0;
}

:global(html.dark) .pwa-title {
  color: #f4f4f5;
}

.pwa-desc {
  font-size: 0.8rem;
  color: #71717a;
  margin: 0.15rem 0 0 0;
}

:global(html.dark) .pwa-desc {
  color: #a1a1aa;
}

.pwa-btn-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pwa-install-button {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: #ffffff;
  background-color: #18181b;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.pwa-install-button:hover {
  background-color: #27272a;
}

:global(html.dark) .pwa-install-button {
  background-color: #f4f4f5;
  color: #18181b;
}

:global(html.dark) .pwa-install-button:hover {
  background-color: #e4e4e7;
}

.pwa-dismiss-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  color: #71717a;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.2s;
}

.pwa-dismiss-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

:global(html.dark) .pwa-dismiss-button:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

/* iOS Safari Tooltip layout styles */
.pwa-tooltip-wrapper {
  position: fixed;
  bottom: 5rem;
  left: 50%;
  transform: translateX(-50%);
  width: 90%;
  max-width: 22rem;
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pwa-tooltip-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.85rem 1rem;
  background-color: #ffffff;
  border-radius: 0.75rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.06);
}

:global(html.dark) .pwa-tooltip-content {
  background-color: #18181b;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.pwa-tooltip-text {
  font-size: 0.82rem;
  line-height: 1.45;
  color: #27272a;
}

:global(html.dark) .pwa-tooltip-text {
  color: #e4e4e7;
}

.pwa-ios-share-icon {
  display: inline-block;
  width: 1.15rem;
  height: 1.15rem;
  vertical-align: middle;
  margin: 0 0.2rem;
  color: #007aff;
}

.pwa-tooltip-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  color: #a1a1aa;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.pwa-tooltip-close:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #71717a;
}

:global(html.dark) .pwa-tooltip-close:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: #d4d4d8;
}

.pwa-tooltip-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #ffffff;
  margin-top: -1px;
}

:global(html.dark) .pwa-tooltip-arrow {
  border-top-color: #18181b;
}

/* Transition animations */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s;
}

.slide-up-enter-from {
  transform: translateY(100%);
  opacity: 0;
}

/* Mobile responsive line break */
.mobile-br {
  display: block;
}
@media (min-width: 480px) {
  .mobile-br {
    display: none;
  }
}
</style>

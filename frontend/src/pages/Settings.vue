<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 w-full max-w-lg md:max-w-4xl lg:max-w-5xl mx-auto flex flex-col items-center p-6 sm:p-12 transition-colors duration-300">
    <!-- 공통 네비바 컴포넌트 장착 -->
    <NavBar />

    <!-- 설정 카드 컨테이너 -->
    <div class="w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl transition-all duration-300 mt-4">
      
      <!-- 헤더 영역 -->
      <div class="flex items-center gap-4 mb-8 border-b border-slate-100 dark:border-slate-800 pb-6">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.43l-1.003.828c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.43l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
          </svg>
        </div>
        <div>
          <h1 class="text-xl sm:text-2xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">
            환경 설정
          </h1>
          <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            사용자 개인 환경 및 글로벌 시간대(Timezone) 설정을 정밀하게 조정합니다.
          </p>
        </div>
      </div>

      <!-- 로딩 뷰 스켈레톤 -->
      <div v-if="isLoadingData" class="space-y-6 animate-pulse">
        <div class="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/4"></div>
        <div class="h-12 bg-slate-200 dark:bg-slate-800 rounded-xl w-full"></div>
        <div class="h-10 bg-slate-200 dark:bg-slate-800 rounded-xl w-1/3"></div>
      </div>

      <!-- 실제 폼 영역 -->
      <div v-else class="space-y-8">
        <!-- 시간대 설정 섹션 -->
        <div class="space-y-3">
          <label for="timezone-select" class="block text-sm font-semibold text-slate-700 dark:text-slate-300">
            기본 시간대 (Timezone)
          </label>
          <p class="text-2xs text-slate-400 dark:text-slate-500">
            시간대를 변경하면 과거 작성된 결제 데이터 및 캘린더 요약 지출 일정이 설정된 시간대 오프셋 기준으로 자동 소급 반영되어 표시됩니다.
          </p>
          
          <div class="relative">
            <select
              id="timezone-select"
              v-model="selectedTimezone"
              class="w-full px-4 py-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-800 dark:text-slate-100 font-medium text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all cursor-pointer appearance-none"
            >
              <option v-for="tz in timezoneOptions" :key="tz.value" :value="tz.value">
                {{ tz.label }} ({{ tz.value }})
              </option>
            </select>
            <!-- 커스텀 드롭다운 화살표 -->
            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-slate-500 dark:text-slate-400">
              <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
              </svg>
            </div>
          </div>
        </div>

        <!-- 알림 설정 섹션 (US1) -->
        <div class="space-y-4 border-t border-slate-100 dark:border-slate-800 pt-6">
          <div class="flex items-center justify-between">
            <div>
              <label class="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                실시간 웹 푸시 알림
              </label>
              <p class="text-2xs text-slate-400 dark:text-slate-500 mt-1">
                영수증 분석 완료 및 월별 예산 경보 등 중요 가계부 이벤트를 기기 푸시 알림으로 실시간 전송받습니다.
              </p>
            </div>
            <!-- 리액티브 토글 스위치 -->
            <button
              @click="toggleNotification"
              :class="isNotificationEnabled ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-800'"
              class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
              role="switch"
              :aria-checked="isNotificationEnabled"
              :disabled="isToggling"
            >
              <span
                :class="isNotificationEnabled ? 'translate-x-5' : 'translate-x-0'"
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
              ></span>
            </button>
          </div>
          <!-- 권한 거부 상태 시 경고 알림 -->
          <div v-if="isPermissionDenied" class="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 rounded-xl flex items-center gap-2 text-2xs font-medium text-amber-800 dark:text-amber-400">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 flex-shrink-0">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <span>브라우저 알림 권한이 거부되어 있습니다. 브라우저 설정에서 권한을 허용한 후 토글을 켜주십시오.</span>
          </div>
        </div>

        <!-- 피드백 메시지 -->
        <transition name="fade">
          <div v-if="feedback" :class="feedbackClass" class="flex items-center gap-3 p-4 rounded-xl border text-sm font-medium transition-all duration-300">
            <svg v-if="feedbackType === 'success'" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-5 h-5 flex-shrink-0">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-5 h-5 flex-shrink-0">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
            </svg>
            <span>{{ feedback }}</span>
          </div>
        </transition>

        <!-- 저장 동작 버튼 -->
        <div class="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button
            @click="cancelEdit"
            class="px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 text-sm font-semibold transition-all cursor-pointer"
            :disabled="isSaving"
          >
            취소
          </button>
          <button
            @click="saveTimezone"
            class="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-lg shadow-indigo-600/15 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer flex items-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
            :disabled="isSaving"
          >
            <span v-if="isSaving" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span>설정 저장</span>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import NavBar from '../components/NavBar.vue';
import { fetchUserTimezone, updateUserTimezone } from '../services/accountService';
import {
  fetchVapidPublicKey,
  registerSubscription,
  unregisterSubscription,
  fetchSubscriptions
} from '../services/notificationService';

export default {
  name: 'Settings',
  components: {
    NavBar
  },
  setup() {
    const router = useRouter();
    const selectedTimezone = ref('Asia/Seoul');
    const originalTimezone = ref('Asia/Seoul');
    
    const isLoadingData = ref(true);
    const isSaving = ref(false);
    const feedback = ref('');
    const feedbackType = ref('success'); // 'success' | 'error'

    // 알림 토글 관련 상태 변수 (US1)
    const isNotificationEnabled = ref(false);
    const isToggling = ref(false);
    const isPermissionDenied = ref(false);
    const activeSubscriptionId = ref(null);

    // IANA 표준 타임존 목록 옵션
    const timezoneOptions = [
      { label: '서울 (한국 표준시)', value: 'Asia/Seoul' },
      { label: '도쿄 (일본 표준시)', value: 'Asia/Tokyo' },
      { label: '상하이 (중국 표준시)', value: 'Asia/Shanghai' },
      { label: '싱가포르 Standard Time', value: 'Asia/Singapore' },
      { label: '런던 (그리니치 표준시)', value: 'Europe/London' },
      { label: '파리 (중부 유럽 표준시)', value: 'Europe/Paris' },
      { label: '뉴욕 (동부 표준시)', value: 'America/New_York' },
      { label: '로스앤젤레스 (태평양 표준시)', value: 'America/Los_Angeles' },
      { label: '시드니 (동부 호주 표준시)', value: 'Australia/Sydney' },
      { label: '협정 세계시 (UTC)', value: 'UTC' }
    ];

    // VAPID 키 변환용 헬퍼 함수
    const urlBase64ToUint8Array = (base64String) => {
      const padding = '='.repeat((4 - base64String.length % 4) % 4);
      const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
      const rawData = window.atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
      }
      return outputArray;
    };

    // 알림 초기 허용 상태 로드
    const loadNotificationStatus = async () => {
      if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        return;
      }

      if (Notification.permission === 'denied') {
        isPermissionDenied.value = true;
        return;
      }

      try {
        const registration = await navigator.serviceWorker.ready;
        const currentSub = await registration.pushManager.getSubscription();
        
        if (currentSub) {
          // 백엔드에 등록된 구독 조회
          const backendSubs = await fetchSubscriptions();
          // 현재 브라우저의 endpoint와 매핑되는 것이 활성화되어 있는지 대조
          const matched = backendSubs.find(s => s.is_active && currentSub.endpoint.endsWith(s.id || ''));
          
          // 백엔드 ID 조회가 매핑되지 않는 경우, endpoint 문자열 비교로 보강
          const fallbackMatched = backendSubs.find(s => s.is_active);
          
          if (matched || fallbackMatched) {
            isNotificationEnabled.value = true;
            activeSubscriptionId.value = (matched || fallbackMatched).id;
          }
        }
      } catch (err) {
        console.warn('푸시 알림 상태 로드 실패:', err);
      }
    };

    // 알림 활성화/비활성화 토글 핸들러
    const toggleNotification = async () => {
      if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        showFeedback('이 브라우저는 웹 푸시 알림을 지원하지 않습니다.', 'error');
        return;
      }

      try {
        isToggling.value = true;
        feedback.value = '';

        if (!isNotificationEnabled.value) {
          // 알림 켜기
          const permission = await Notification.requestPermission();
          if (permission !== 'granted') {
            isPermissionDenied.value = true;
            showFeedback('알림 권한이 허용되지 않았습니다.', 'error');
            return;
          }
          
          isPermissionDenied.value = false;
          
          // 백엔드에서 VAPID 공개키 가져오기
          const { public_key } = await fetchVapidPublicKey();
          const registration = await navigator.serviceWorker.ready;
          
          const subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(public_key)
          });

          // 등록 요청 페이로드 조립
          const subJson = subscription.toJSON();
          const payload = {
            endpoint: subJson.endpoint,
            keys: {
              p256dh: subJson.keys.p256dh,
              auth: subJson.keys.auth
            }
          };

          const registeredSub = await registerSubscription(payload);
          isNotificationEnabled.value = true;
          activeSubscriptionId.value = registeredSub.id;
          showFeedback('실시간 웹 푸시 알림 수신이 활성화되었습니다.', 'success');
        } else {
          // 알림 끄기
          const registration = await navigator.serviceWorker.ready;
          const subscription = await registration.pushManager.getSubscription();
          
          if (subscription) {
            await subscription.unsubscribe();
          }

          if (activeSubscriptionId.value) {
            await unregisterSubscription(activeSubscriptionId.value);
          }

          isNotificationEnabled.value = false;
          activeSubscriptionId.value = null;
          showFeedback('실시간 웹 푸시 알림 수신이 해제되었습니다.', 'success');
        }
      } catch (err) {
        showFeedback(err.message || '알림 설정 변경 중 오류가 발생하였습니다.', 'error');
      } finally {
        isToggling.value = false;
      }
    };

    const loadTimezone = async () => {
      try {
        isLoadingData.value = true;
        const response = await fetchUserTimezone();
        if (response && response.data && response.data.timezone) {
          selectedTimezone.value = response.data.timezone;
          originalTimezone.value = response.data.timezone;
        }
      } catch (err) {
        showFeedback(err.message || '시간대 정보를 불러올 수 없습니다.', 'error');
      } finally {
        isLoadingData.value = false;
      }
    };

    const saveTimezone = async () => {
      try {
        isSaving.value = true;
        feedback.value = '';
        
        const response = await updateUserTimezone(selectedTimezone.value);
        if (response && response.status === 'success') {
          originalTimezone.value = selectedTimezone.value;
          showFeedback('타임존 설정이 성공적으로 저장되었습니다. 대시보드로 이동합니다...', 'success');
          
          // 성공 피드백 전달 후 대시보드로 라우팅
          setTimeout(() => {
            router.push({ name: 'Dashboard' });
          }, 1500);
        }
      } catch (err) {
        showFeedback(err.message || '설정 저장 중 오류가 발생했습니다.', 'error');
      } finally {
        isSaving.value = false;
      }
    };

    const cancelEdit = () => {
      selectedTimezone.value = originalTimezone.value;
      router.push({ name: 'Dashboard' });
    };

    const showFeedback = (msg, type) => {
      feedback.value = msg;
      feedbackType.value = type;
      if (type === 'error') {
        // 에러의 경우 잠시 후 사라지게 설정 (성공은 페이지 이동하므로 유지)
        setTimeout(() => {
          if (feedback.value === msg) {
            feedback.value = '';
          }
        }, 5000);
      }
    };

    const feedbackClass = computed(() => {
      if (feedbackType.value === 'success') {
        return 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200/50 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-400';
      }
      return 'bg-rose-50/50 dark:bg-rose-950/20 border-rose-200/50 dark:border-rose-800/40 text-rose-800 dark:text-rose-400';
    });

    onMounted(() => {
      loadTimezone();
      loadNotificationStatus();
    });

    return {
      selectedTimezone,
      timezoneOptions,
      isLoadingData,
      isSaving,
      feedback,
      feedbackType,
      feedbackClass,
      saveTimezone,
      cancelEdit,
      isNotificationEnabled,
      isToggling,
      isPermissionDenied,
      toggleNotification
    };
  }
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<template>
  <main class="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 sm:p-12 selection:bg-indigo-500">
    <!-- 로그아웃 및 사용자 프로필 상단 바 -->
    <div class="w-full max-w-lg flex justify-between items-center mb-6 text-xs text-slate-400">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
        <span class="font-semibold text-slate-200">{{ currentUsername }}</span>님 환영합니다
      </div>
      <button 
        @click="handleLogout"
        class="logout-btn px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all cursor-pointer font-semibold uppercase tracking-wider"
      >
        로그아웃
      </button>
    </div>

    <div class="w-full max-w-lg flex flex-col">
      <!-- 헤더 브랜드 영역 (Aesthetics WOW - Outfit/Inter 모던 타이틀) -->
      <header class="text-center mb-10 select-none">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-4 tracking-wide font-outfit uppercase">
          AI Automations
        </span>
        <h1 class="font-outfit text-4xl sm:text-5xl font-black text-slate-100 tracking-tight leading-none mb-3">
          Smart Ledger <span class="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-500">Receipts</span>
        </h1>
        <p class="text-slate-400 text-sm sm:text-base font-normal tracking-wide max-w-sm mx-auto leading-relaxed">
          영수증 이미지를 올리면 고속 캐시 및 AI가 분석하여 가계부를 자동 작성합니다.
        </p>
      </header>

      <!-- 에러 피드백 알럿 영역 -->
      <div 
        v-if="errorMessage"
        class="w-full max-w-md mx-auto mb-5 p-4 rounded-xl bg-rose-950/30 border border-rose-900/40 text-rose-200 text-sm flex items-start space-x-3 transition-all duration-300 shadow-md animate-fade-in"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 flex-shrink-0 mt-0.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 메인 인터랙티브 작업 공간 -->
      <div class="relative w-full max-w-md mx-auto">
        <!-- 업로드 진행 중 로딩 인디케이터 오버레이 -->
        <div 
          v-if="isUploading"
          class="absolute inset-0 z-50 bg-slate-950/80 backdrop-blur-sm rounded-2xl flex flex-col items-center justify-center text-center p-8 border border-slate-800 shadow-2xl animate-fade-in"
        >
          <!-- 핀테크 감성 그라데이션 회전 링 -->
          <div class="w-14 h-14 rounded-full border-4 border-slate-800 border-t-indigo-500 animate-spin mb-4"></div>
          <h3 class="font-outfit text-slate-100 font-semibold text-lg mb-1">영수증 분석 중...</h3>
          <p class="text-slate-400 text-xs tracking-wide">HTML5 Canvas 압축 및 AI OCR 파이프라인 가동 중</p>
        </div>

        <!-- 드롭존 -->
        <Dropzone 
          v-if="!currentFile"
          @file-detected="onFileDetected"
          @validation-error="onValidationError"
        />

        <!-- 영수증 결과물 목록 및 분석된 가계부 명세 피드백 -->
        <ReceiptList 
          v-else
          :file="currentFile"
          :parsed-data="parsedData"
          :polling-status="pollingStatus"
          @file-removed="onFileRemoved"
        />
      </div>

      <!-- 정보 푸터 -->
      <footer class="text-center text-slate-600 text-xs font-mono tracking-wider mt-12 select-none">
        AI Ledger Automation v1.0.0 &copy; 2026
      </footer>
    </div>
  </main>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import Dropzone from './Dropzone.vue';
import ReceiptList from './ReceiptList.vue';
import { compressImage, uploadReceiptApi } from '../services/uploadService';
import { VirtualPollingManager } from '../services/pollingService';
import { logout } from '../services/authService';

export default {
  name: 'DashboardView',
  components: {
    Dropzone,
    ReceiptList
  },
  setup() {
    const router = useRouter();
    const currentUsername = ref('사용자');
    const currentFile = ref(null);
    const parsedData = ref(null);
    const isUploading = ref(false);
    const errorMessage = ref(null);
    const pollingStatus = ref(null);
    let errorTimeout = null;

    onMounted(() => {
      const sessionData = localStorage.getItem('ai_ledger_auth_session');
      if (sessionData) {
        try {
          const parsed = JSON.parse(sessionData);
          if (parsed && parsed.username) {
            currentUsername.value = parsed.username;
          }
        } catch (e) {
          console.error('Failed to parse session info', e);
        }
      }
    });

    const handleLogout = async () => {
      try {
        await logout();
        if (router) {
          router.push({ name: 'Login' });
        } else {
          window.location.hash = '/login';
        }
      } catch (err) {
        console.error('Logout error', err);
      }
    };

    // 영수증 파일 감지 성공 시 호출 (비동기 업로드 E2E 구동)
    const onFileDetected = async (file) => {
      clearError();
      isUploading.value = true;
      pollingStatus.value = null;

      try {
        // 1. 헌법 V조 수호: 가로 최대 1000px 이미지 1차 압축 처리
        const compressed = await compressImage(file);
        
        // 2. 동기식 Django API 업로드 연동
        const response = await uploadReceiptApi(compressed, file.name);
        
        // 3. UUIDv7 식별자 및 status 하위 호환성 확인
        const jobId = response.job_id;
        const status = response.status;

        // 미리보기 URL 생성
        const previewUrl = URL.createObjectURL(compressed);
        
        currentFile.value = {
          id: jobId,
          name: file.name,
          size: compressed.size,
          type: file.type,
          previewUrl: previewUrl,
          rawFile: file,
          createdAt: new Date().toISOString()
        };

        if (status === 'COMPLETED') {
          // 동기 파싱 성공 즉시 렌더링 바인딩
          parsedData.value = response.data;
          pollingStatus.value = 'COMPLETED';
        } else {
          // 3주차 비동기 호환을 위한 가상 폴링 대기 루프 개시
          pollingStatus.value = status;
          startVirtualPolling(jobId, status);
        }

      } catch (err) {
        onValidationError(err.message);
        currentFile.value = null;
        parsedData.value = null;
      } finally {
        isUploading.value = false;
      }
    };

    // 가상 폴링 모듈 구동 함수
    const startVirtualPolling = (jobId, initialStatus) => {
      VirtualPollingManager.startPolling(
        jobId,
        initialStatus,
        (completedData) => {
          parsedData.value = completedData;
          pollingStatus.value = 'COMPLETED';
        },
        (error) => {
          onValidationError(error.message || '비동기 폴링 상태 조회에 실패했습니다.');
          pollingStatus.value = 'FAILED';
        }
      );
    };

    // 영수증 파일 제거 시 (메모리 안전 해제)
    const onFileRemoved = () => {
      if (currentFile.value) {
        URL.revokeObjectURL(currentFile.value.previewUrl);
      }
      currentFile.value = null;
      parsedData.value = null;
      pollingStatus.value = null;
      clearError();
    };

    // 1차 유효성 검사 실패 수신 시
    const onValidationError = (error) => {
      errorMessage.value = error;
      
      if (errorTimeout) clearTimeout(errorTimeout);
      errorTimeout = setTimeout(() => {
        errorMessage.value = null;
      }, 4000);
    };

    const clearError = () => {
      errorMessage.value = null;
      if (errorTimeout) clearTimeout(errorTimeout);
    };

    return {
      currentUsername,
      currentFile,
      parsedData,
      isUploading,
      errorMessage,
      pollingStatus,
      handleLogout,
      onFileDetected,
      onFileRemoved,
      onValidationError
    };
  }
};
</script>

<style scoped>
/* 부드러운 페이드인 애니메이션 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
</style>

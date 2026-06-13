<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 p-6 sm:p-12 font-sans selection:bg-indigo-500 flex flex-col items-center justify-center">
    <div class="w-full max-w-md md:max-w-3xl lg:max-w-4xl flex flex-col space-y-6">
      
      <!-- 헤더 섹션 (대시보드와 동일한 모던 브랜드 톤) -->
      <header class="text-center select-none">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3 tracking-wide uppercase font-outfit">
          Parser Cache
        </span>
        <h1 class="font-outfit text-3xl font-black text-slate-100 tracking-tight leading-none mb-2">
          내 가맹점 <span class="bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-teal-400 to-indigo-400">템플릿</span>
        </h1>
        <p class="text-slate-400 text-xs leading-relaxed max-w-xs mx-auto">
          결제했던 가맹점의 AI 영수증 분석 템플릿 상태를 확인하고 파싱 에러 시 초기화합니다.
        </p>
      </header>

      <!-- 요약 정보 칩 (가로 3열 콤팩트 레이아웃) -->
      <div class="grid grid-cols-3 gap-2 text-center text-2xs bg-slate-900/60 border border-slate-800/80 rounded-xl p-3 shadow-lg select-none">
        <div class="flex flex-col">
          <span class="text-slate-500 uppercase tracking-wider font-semibold">총 템플릿</span>
          <span class="text-sm font-bold text-slate-200 mt-0.5 font-mono">{{ templates.length }}</span>
        </div>
        <div class="flex flex-col border-x border-slate-800/80">
          <span class="text-slate-500 uppercase tracking-wider font-semibold">우회 가동</span>
          <span class="text-sm font-bold text-emerald-400 mt-0.5 font-mono">{{ verifiedCount }}</span>
        </div>
        <div class="flex flex-col">
          <span class="text-slate-500 uppercase tracking-wider font-semibold">자동 학습</span>
          <span class="text-sm font-bold text-teal-400 mt-0.5 font-mono">{{ learningCount }}</span>
        </div>
      </div>

      <!-- 에러 피드백 알럿 -->
      <div 
        v-if="errorMessage"
        class="p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/40 text-rose-200 text-xs flex items-start space-x-2.5 transition-all duration-300"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 flex-shrink-0 mt-0.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 로딩 인디케이터 -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-16 space-y-3">
        <div class="w-8 h-8 border-3 border-slate-800 border-t-indigo-500 rounded-full animate-spin"></div>
        <p class="text-slate-500 text-xs">템플릿 목록 로드 중...</p>
      </div>

      <!-- 빈 목록 대응 -->
      <div v-else-if="templates.length === 0" class="bg-slate-900 border border-slate-800 rounded-2xl p-10 text-center text-slate-500 text-xs shadow-xl select-none">
        <p class="font-semibold text-slate-400">가맹점 템플릿 내역이 없습니다.</p>
        <p class="mt-1 text-2xs text-slate-600">영수증 분석이 시작되면 자동으로 빌드됩니다.</p>
      </div>

      <!-- 가맹점 콤팩트 리스트 영역 (대시보드 리스트 스타일 계승) -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[32rem] overflow-y-auto pr-1">
        <div 
          v-for="template in templates" 
          :key="template.id"
          class="bg-slate-900 border border-slate-800/80 rounded-xl p-3.5 flex items-center justify-between shadow-md hover:border-slate-700/60 transition duration-200"
        >
          <!-- 좌측: 가맹점 정보 -->
          <div class="flex flex-col min-w-0 pr-2 select-none">
            <span class="text-sm font-bold text-slate-200 truncate leading-snug" :title="template.vendor_name">
              {{ template.vendor_name }}
            </span>
            <span class="text-2xs text-slate-500 font-mono mt-0.5">
              {{ formatRegNumber(template.vendor_registration_number) }}
            </span>
          </div>

          <!-- 우측: 상태 배지 및 초기화 제어 버튼 -->
          <div class="flex items-center space-x-2 flex-shrink-0">
            <!-- 콤팩트 상태 배지 -->
            <span 
              v-if="template.is_blacklisted"
              class="px-2 py-0.5 rounded-md text-3xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"
            >
              차단됨
            </span>
            <span 
              v-else-if="template.is_verified"
              class="px-2 py-0.5 rounded-md text-3xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            >
              우회 중
            </span>
            <span 
              v-else-if="template.self_healing_attempts > 0"
              class="px-2 py-0.5 rounded-md text-3xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse"
            >
              치유 중
            </span>
            <span 
              v-else
              class="px-2 py-0.5 rounded-md text-3xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20"
            >
              학습 중
            </span>

            <!-- 콤팩트 초기화 버튼 -->
            <button
              @click="confirmReset(template)"
              class="px-2.5 py-1 rounded-lg border border-rose-900/50 bg-rose-950/20 text-rose-300 hover:bg-rose-900/40 hover:text-rose-100 transition duration-200 text-2xs font-semibold cursor-pointer select-none"
            >
              초기화
            </button>
          </div>
        </div>
      </div>

      <!-- 푸터 및 돌아가기 -->
      <div class="flex flex-col items-center space-y-4 pt-4 select-none">
        <router-link
          to="/dashboard"
          class="w-full text-center py-2.5 rounded-xl border border-slate-800 text-xs font-semibold text-slate-400 bg-slate-900 hover:text-slate-200 hover:bg-slate-800 transition duration-200 cursor-pointer"
        >
          대시보드로 돌아가기
        </router-link>
        <footer class="text-center text-slate-700 text-2xs font-mono tracking-wider">
          AI Ledger Automation v1.0.0 &copy; 2026
        </footer>
      </div>

    </div>

    <!-- 파서 초기화 경고 모달 -->
    <div 
      v-if="isModalOpen" 
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
    >
      <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-xs w-full p-5 shadow-2xl space-y-5">
        <div class="text-center space-y-2">
          <div class="w-10 h-10 rounded-full bg-rose-950/30 border border-rose-900/50 flex items-center justify-center mx-auto text-rose-400 mb-1">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 class="text-sm font-bold text-slate-100">가맹점 파서 초기화</h3>
          <p class="text-2xs text-slate-400 leading-relaxed">
            <strong class="text-slate-200">[{{ selectedTemplate?.vendor_name }}]</strong> 템플릿을 초기화하시겠습니까?<br>
            초기화 시 다음 업로드 시점부터 AI가 영수증 레이아웃을 다시 처음부터 분석 및 제안하게 됩니다.
          </p>
        </div>

        <div class="flex space-x-2 text-xs">
          <button
            @click="isModalOpen = false"
            class="flex-1 py-2 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-300 font-semibold transition duration-200 cursor-pointer"
          >
            취소
          </button>
          <button
            @click="executeReset"
            :disabled="resetting"
            class="flex-1 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold transition duration-200 cursor-pointer disabled:opacity-50"
          >
            {{ resetting ? '초기화 중...' : '초기화 실행' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, onBeforeMount } from 'vue';
import { fetchMyTemplates, deleteMyTemplate } from '../services/ledgerService';

export default {
  name: 'MyTemplateList',
  setup() {
    const templates = ref([]);
    const loading = ref(false);
    const resetting = ref(false);
    const errorMessage = ref(null);
    const isModalOpen = ref(false);
    const selectedTemplate = ref(null);

    // Outfit 구글 웹 폰트 동적 헤더 로드
    onBeforeMount(() => {
      if (!document.getElementById('outfit-font')) {
        const link = document.createElement('link');
        link.id = 'outfit-font';
        link.rel = 'stylesheet';
        link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;900&display=swap';
        document.head.appendChild(link);
      }
    });

    const loadTemplates = async () => {
      loading.value = true;
      errorMessage.value = null;
      try {
        const data = await fetchMyTemplates();
        templates.value = data || [];
      } catch (err) {
        errorMessage.value = err.message || '템플릿 목록을 불러오는 데 실패했습니다.';
      } finally {
        loading.value = false;
      }
    };

    const confirmReset = (template) => {
      selectedTemplate.value = template;
      isModalOpen.value = true;
    };

    const executeReset = async () => {
      if (!selectedTemplate.value) return;
      resetting.value = true;
      errorMessage.value = null;
      try {
        await deleteMyTemplate(selectedTemplate.value.id);
        isModalOpen.value = false;
        await loadTemplates();
      } catch (err) {
        errorMessage.value = err.message || '가맹점 파서 초기화에 실패했습니다.';
      } finally {
        resetting.value = false;
      }
    };

    const formatRegNumber = (num) => {
      if (!num || num.length !== 10) return num;
      return `${num.substring(0, 3)}-${num.substring(3, 5)}-${num.substring(5)}`;
    };

    // 상태 요약 집계
    const verifiedCount = computed(() => {
      return templates.value.filter(t => t.is_verified && !t.is_blacklisted).length;
    });

    const learningCount = computed(() => {
      return templates.value.filter(t => !t.is_verified && !t.is_blacklisted).length;
    });

    onMounted(() => {
      loadTemplates();
    });

    return {
      templates,
      loading,
      resetting,
      errorMessage,
      isModalOpen,
      selectedTemplate,
      verifiedCount,
      learningCount,
      confirmReset,
      executeReset,
      formatRegNumber
    };
  }
};
</script>

<style scoped>
/* 구글 Outfit 클래스 매핑 */
.font-outfit {
  font-family: 'Outfit', sans-serif;
}
@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}
.animate-fade-in {
  animation: fadeIn 0.15s ease-out forwards;
}
</style>

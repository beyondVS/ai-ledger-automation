<template>
  <div class="min-h-screen bg-slate-950 text-slate-100 p-6 sm:p-12 font-sans selection:bg-indigo-500 flex flex-col items-center justify-center">
    <div class="w-full max-w-md md:max-w-3xl lg:max-w-4xl flex flex-col space-y-6">
      <!-- 상단 내비바 뒤로가기 -->
      <div class="flex items-center justify-between w-full border-b border-slate-800/60 pb-4 select-none">
        <router-link
          to="/dashboard"
          class="inline-flex items-center gap-1 text-xs font-semibold text-slate-400 hover:text-white transition duration-200"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          대시보드
        </router-link>
        <span class="text-xs text-slate-600 font-mono tracking-wider">My Templates</span>
      </div>

      <!-- 헤더 섹션 (대시보드와 동일한 모던 브랜드 톤) -->
      <header class="text-center select-none pt-2">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3 tracking-wide uppercase font-outfit">
          Parser Cache
        </span>
        <h1 class="font-outfit text-3xl font-black text-slate-100 tracking-tight leading-none mb-2">
          내 가맹점 <span class="bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-teal-400 to-indigo-400">템플릿</span>
        </h1>
        <p class="text-slate-400 text-xs leading-relaxed max-w-xs mx-auto word-break-keep-all">
          결제했던 가맹점의 AI 영수증 분석 템플릿 상태를 확인하고 파싱 에러 시 초기화합니다.
        </p>
      </header>

      <!-- 요약 정보 칩 (가로 3열 고속 통계 배너) -->
      <div class="grid grid-cols-3 gap-2 bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-lg select-none">
        <div class="flex items-center justify-center space-x-3">
          <div class="p-2 rounded-lg bg-slate-800/60 text-slate-400">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h18v3.75H3V3Z" />
            </svg>
          </div>
          <div class="flex flex-col text-left">
            <span class="text-3xs text-slate-500 uppercase tracking-wider font-bold">총 템플릿</span>
            <span class="text-base font-extrabold text-white mt-0.5 font-mono leading-none">{{ templates.length }}</span>
          </div>
        </div>
        <div class="flex items-center justify-center space-x-3 border-x border-slate-800/80">
          <div class="p-2 rounded-lg bg-emerald-950/20 text-emerald-400">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
            </svg>
          </div>
          <div class="flex flex-col text-left pl-1">
            <span class="text-3xs text-slate-500 uppercase tracking-wider font-bold">우회 가동</span>
            <span class="text-base font-extrabold text-emerald-400 mt-0.5 font-mono leading-none">{{ verifiedCount }}</span>
          </div>
        </div>
        <div class="flex items-center justify-center space-x-3">
          <div class="p-2 rounded-lg bg-teal-950/20 text-teal-400">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
            </svg>
          </div>
          <div class="flex flex-col text-left pl-1">
            <span class="text-3xs text-slate-500 uppercase tracking-wider font-bold">자동 학습</span>
            <span class="text-base font-extrabold text-teal-400 mt-0.5 font-mono leading-none">{{ learningCount }}</span>
          </div>
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
      <div v-else-if="templates.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-500 border border-dashed border-slate-800 bg-slate-900/20 rounded-2xl shadow-xl select-none">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12 mb-3 text-slate-700">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 13.5h3.86a2.25 2.25 0 0 1 2.008 1.24l.885 1.77a2.25 2.25 0 0 0 2.007 1.24h1.98a2.25 2.25 0 0 0 2.007-1.24l.885-1.77a2.25 2.25 0 0 1 2.007-1.24h3.86m-18 0h18a2.25 2.25 0 0 1 2.25 2.25v4.5A2.25 2.25 0 0 1 18 22.5H6a2.25 2.25 0 0 1-2.25-2.25v-4.5A2.25 2.25 0 0 1 2.25 13.5Z" />
        </svg>
        <p class="font-semibold text-slate-400">학습된 가맹점 템플릿이 없습니다.</p>
        <p class="mt-1.5 text-2xs text-slate-600 font-medium">대시보드에 영수증을 업로드하여 첫 파서 템플릿 캐싱을 시작해 보세요.</p>
      </div>

      <!-- 가맹점 콤팩트 리스트 영역 (타일 형태 그리드 고도화) -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 max-h-[32rem] overflow-y-auto pr-1">
        <div 
          v-for="template in templates" 
          :key="template.id"
          class="bg-slate-900 border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between space-y-4 shadow-xl hover:border-slate-700/60 hover:-translate-y-0.5 transition-all duration-200 group"
        >
          <!-- 상단: 가맹점 정보 -->
          <div class="flex flex-col min-w-0 select-none">
            <span class="text-base font-bold text-slate-200 truncate leading-snug group-hover:text-white" :title="template.vendor_name">
              {{ template.vendor_name }}
            </span>
            <span class="text-xxs text-slate-500 font-mono mt-1 tracking-wider">
              사업자번호: {{ formatRegNumber(template.vendor_registration_number) }}
            </span>
          </div>

          <!-- 하단: 상태 배지 및 초기화 제어 버튼 정렬 분리 -->
          <div class="flex items-center justify-between border-t border-slate-800/60 pt-3 flex-shrink-0">
            <!-- 콤팩트 상태 배지 -->
            <span 
              v-if="template.is_blacklisted"
              class="px-2 py-0.5 rounded-lg text-3xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"
            >
              차단됨
            </span>
            <span 
              v-else-if="template.is_verified"
              class="px-2 py-0.5 rounded-lg text-3xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
            >
              우회 가동
            </span>
            <span 
              v-else-if="template.self_healing_attempts > 0"
              class="px-2 py-0.5 rounded-lg text-3xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse"
            >
              자가 치유
            </span>
            <span 
              v-else
              class="px-2 py-0.5 rounded-lg text-3xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20"
            >
              자동 학습
            </span>

            <!-- 콤팩트 초기화 버튼 (아이콘 결합) -->
            <button
              @click="confirmReset(template)"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-rose-900/30 bg-rose-950/20 text-rose-400 hover:bg-rose-900/30 hover:text-rose-100 transition duration-200 text-2xs font-semibold cursor-pointer select-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3.5 h-3.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              초기화
            </button>
          </div>
        </div>
      </div>

      <!-- 푸터 및 돌아가기 -->
      <div class="flex flex-col items-center space-y-4 pt-6 select-none border-t border-slate-900">
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

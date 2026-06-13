<template>
  <main class="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 sm:p-12 selection:bg-indigo-500">
    <!-- 로그아웃 및 사용자 프로필 상단 바 -->
    <div class="w-full max-w-lg md:max-w-4xl lg:max-w-5xl flex justify-between items-center mb-6 text-xs text-slate-400">
      <div class="flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
        <span class="font-semibold text-slate-200">{{ currentUsername }}</span>님 환영합니다
      </div>
      <div class="flex items-center gap-2">
        <button 
          @click="goToMyTemplates"
          class="px-3 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-900/50 text-indigo-300 hover:text-indigo-100 hover:bg-indigo-900/60 transition-all cursor-pointer font-semibold uppercase tracking-wider"
        >
          내 가맹점 템플릿
        </button>
        <button 
          @click="handleLogout"
          class="logout-btn px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all cursor-pointer font-semibold uppercase tracking-wider"
        >
          로그아웃
        </button>
      </div>
    </div>

    <div class="w-full max-w-lg md:max-w-4xl lg:max-w-5xl flex flex-col">
      <!-- 헤더 브랜드 영역 (Aesthetics WOW - Outfit/Inter 모던 타이틀) -->
        <header class="text-center md:text-left select-none max-w-xl mb-10">
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3 tracking-wide uppercase font-outfit">
            AI Automations
          </span>
          <h1 class="font-outfit text-4xl md:text-5xl font-black text-slate-100 tracking-tight leading-none mb-3">
            Smart Ledger <span class="bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-teal-400 to-indigo-400">Receipts</span>
          </h1>
          <p class="text-slate-400 text-sm leading-relaxed break-keep">
            영수증 이미지를 올리면 고속 캐시 및 AI가 분석하여 가계부를 자동 작성합니다.
          </p>
        </header>

      <!-- 에러 피드백 알럿 영역 -->
      <div 
        v-if="errorMessage"
        class="w-full max-w-md md:max-w-none mx-auto mb-5 p-4 rounded-xl bg-rose-950/30 border border-rose-900/40 text-rose-200 text-sm flex items-start space-x-3 transition-all duration-300 shadow-md animate-fade-in"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 flex-shrink-0 mt-0.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 상단 대시보드 패널 (예산 게이지 및 TOP 3 가맹점) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 w-full items-stretch">
        <BudgetGauge 
          :budget="dashboardData.budget" 
          :current-month-str="currentMonthStr"
          @budget-updated="onBudgetUpdated"
        />
        <TopMerchants 
          :merchants="dashboardData.top_merchants" 
        />
      </div>

      <!-- 반응형 2열 본문 그리드 레이아웃 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch w-full mt-2">
        <!-- 좌측 열: 메인 인터랙티브 작업 공간 -->
        <div class="relative w-full max-w-md mx-auto md:mx-0 md:max-w-none">
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

        <!-- 우측 열: 가계부 리스트 뷰 영역 (US1 MVP) -->
        <section class="w-full max-w-md mx-auto md:mx-0 md:max-w-none p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between h-full">
          <div class="flex justify-between items-center mb-6">
            <div class="flex items-center gap-2 select-none">
              <button 
                @click="changeMonth(-1)"
                class="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
              <span class="text-xs font-semibold text-slate-300 tracking-wider font-mono uppercase">
                {{ selectedYear }}년 {{ selectedMonth }}월 지출
              </span>
              <button 
                @click="changeMonth(1)"
                class="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
            <span class="text-indigo-400 font-bold font-outfit text-sm">{{ formattedMonthlyTotal }} 원</span>
          </div>

          <!-- 빈 화면 대응 -->
          <div v-if="ledgerList.length === 0 && pendingJobs.length === 0" class="text-center py-8 text-slate-500 text-xs">
            선택하신 달의 가계부 지출 내역이 없습니다.
          </div>

          <!-- 가계부 카드 목록 -->
          <div v-else class="space-y-3 max-h-96 overflow-y-auto pr-1">
            <!-- 비동기 분석 대기중인 스켈레톤 로더 -->
            <LedgerShimmer
              v-for="job in pendingJobs"
              :key="job.id"
              :job="job"
              class="mb-3 animate-fade-in"
            />

            <LedgerListItem 
              v-for="ledger in ledgerList" 
              :key="ledger.id"
              :ledger="ledger"
              @edit="openEditModal"
              @delete="openDeleteModal"
            />
          </div>
        </section>
      </div>

      <!-- 하단 소비 시각화 차트 영역 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8 w-full items-stretch">
        <!-- 원형 차트 -->
        <div class="p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl transition-all duration-300 hover:border-slate-700 flex flex-col justify-between">
          <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">카테고리별 지출 비율</h3>
          <div v-if="dashboardData.category_spending && dashboardData.category_spending.length > 0" class="flex items-center justify-center h-[260px]">
            <PieChart :chart-data="pieChartData" :key="pieChartData.datasets[0].data.join(',')" />
          </div>
          <div v-else class="flex flex-col items-center justify-center h-[260px] text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-3 text-slate-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
            </svg>
            <span>이번 달 카테고리별 지출 내역이 없습니다.</span>
          </div>
        </div>

        <!-- 막대 차트 -->
        <div class="p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl transition-all duration-300 hover:border-slate-700 flex flex-col justify-between">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider">월별 지출 추이</h3>
            
            <!-- 기간 필터 버튼 그룹 -->
            <div class="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button 
                v-for="m in [3, 6, 12]" 
                :key="m"
                @click="updateMonthsFilter(m)"
                class="px-3 py-1 rounded-md font-medium transition-all cursor-pointer"
                :class="selectedMonthsFilter === m ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'"
              >
                {{ m }}개월
              </button>
            </div>
          </div>
          <div v-if="dashboardData.monthly_trends && dashboardData.monthly_trends.length > 0" class="h-[260px] flex items-center justify-center">
            <BarChart :chart-data="barChartData" :key="barChartData.datasets[0].data.join(',')" />
          </div>
          <div v-else class="flex flex-col items-center justify-center h-[260px] text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-3 text-slate-600">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v5.25c0 .621-.504 1.125-1.125 1.125h-2.25A1.125 1.125 0 0 1 3 18.375v-5.25ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125v-9.75ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v14.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
            </svg>
            <span>지출 통계 분석 데이터가 없습니다.</span>
          </div>
        </div>
      </div>

      <!-- 정보 푸터 -->
      <footer class="text-center text-slate-600 text-xs font-mono tracking-wider mt-12 select-none">
        AI Ledger Automation v1.0.0 &copy; 2026
      </footer>
    </div>

    <!-- 수정 모달 (T013) -->
    <LedgerEditModal
      :is-open="isEditModalOpen"
      :ledger="selectedLedgerForEdit || {}"
      @close="isEditModalOpen = false"
      @save="handleEditSave"
    />

    <!-- 삭제 경고 모달 (T020) -->
    <LedgerDeleteModal
      :is-open="isDeleteModalOpen"
      :ledger="selectedLedgerForDelete || {}"
      @close="isDeleteModalOpen = false"
      @confirm="handleDeleteConfirm"
    />
  </main>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import Dropzone from './Dropzone.vue';
import ReceiptList from './ReceiptList.vue';
import LedgerListItem from './LedgerListItem.vue';
import LedgerShimmer from './LedgerShimmer.vue';
import PieChart from './PieChart.vue';
import BarChart from './BarChart.vue';
import BudgetGauge from './BudgetGauge.vue';
import TopMerchants from './TopMerchants.vue';
import { compressImage, uploadReceiptApi } from '../services/uploadService';
import { fetchLedgerList } from '../services/ledgerService';
import { fetchDashboardStatistics } from '../services/dashboardService';
import { VirtualPollingManager } from '../services/pollingService';
import { logout } from '../services/authService';
import LedgerEditModal from './LedgerEditModal.vue';
import LedgerDeleteModal from './LedgerDeleteModal.vue';

export default {
  name: 'DashboardView',
  components: {
    Dropzone,
    ReceiptList,
    LedgerListItem,
    LedgerShimmer,
    LedgerEditModal,
    LedgerDeleteModal,
    PieChart,
    BarChart,
    BudgetGauge,
    TopMerchants
  },
  setup() {
    const router = useRouter();
    const currentUsername = ref('사용자');
    const currentFile = ref(null);
    const parsedData = ref(null);
    const isUploading = ref(false);
    const errorMessage = ref(null);
    const ledgerList = ref([]);
    const pendingJobs = ref([]);
    const pollingStatus = ref(null);
    let errorTimeout = null;

    // 선택된 년/월 상태 변수 (US1 MVP)
    const today = new Date();
    const selectedYear = ref(today.getFullYear());
    const selectedMonth = ref(today.getMonth() + 1);

    // 모달 활성화 상태 및 타겟 정보 refs
    const isEditModalOpen = ref(false);
    const selectedLedgerForEdit = ref(null);
    const isDeleteModalOpen = ref(false);
    const selectedLedgerForDelete = ref(null);

    // 대시보드 통계 상태 정보 (US1, US2, US3)
    const dashboardData = ref({
      budget: { amount: 1000000, spent_amount: 0, remaining_amount: 1000000, spent_ratio: 0, status: 'safe' },
      category_spending: [],
      monthly_trends: [],
      top_merchants: []
    });
    const selectedMonthsFilter = ref(3);

    const currentMonthStr = computed(() => {
      return `${selectedYear.value}-${String(selectedMonth.value).padStart(2, '0')}`;
    });

    const openEditModal = (ledger) => {
      selectedLedgerForEdit.value = ledger;
      isEditModalOpen.value = true;
    };

    const openDeleteModal = (ledger) => {
      selectedLedgerForDelete.value = ledger;
      isDeleteModalOpen.value = true;
    };

    const handleEditSave = (updatedLedger) => {
      ledgerList.value = ledgerList.value.map(item => 
        item.id === updatedLedger.id ? updatedLedger : item
      );
      // 대시보드 실시간 지표 갱신
      loadDashboardData();
    };

    const handleDeleteConfirm = () => {
      if (selectedLedgerForDelete.value) {
        ledgerList.value = ledgerList.value.filter(item => 
          item.id !== selectedLedgerForDelete.value.id
        );
      }
      // 대시보드 실시간 지표 갱신
      loadDashboardData();
    };

    const onBudgetUpdated = (updatedBudget) => {
      // 게이지 수정 즉시 화면을 갱신
      dashboardData.value.budget = {
        amount: Number(updatedBudget.amount),
        spent_amount: dashboardData.value.budget.spent_amount,
        remaining_amount: Number(updatedBudget.amount) - dashboardData.value.budget.spent_amount,
        spent_ratio: (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100,
        status: (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100 < 50 ? 'safe' : 
                (dashboardData.value.budget.spent_amount / Number(updatedBudget.amount)) * 100 <= 80 ? 'warning' : 'danger'
      };
      // 백엔드 전체 연동 갱신
      loadDashboardData();
    };

    onMounted(() => {
      loadLedgerList();
      loadDashboardData();
      const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
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

    const loadLedgerList = async () => {
      try {
        const data = await fetchLedgerList(selectedYear.value, selectedMonth.value);
        ledgerList.value = data;
      } catch (err) {
        console.error('Failed to load ledger list', err);
      }
    };

    const loadDashboardData = async () => {
      try {
        const data = await fetchDashboardStatistics(selectedMonthsFilter.value);
        dashboardData.value = data;
      } catch (err) {
        console.error('Failed to load dashboard statistics', err);
      }
    };

    const updateMonthsFilter = (months) => {
      selectedMonthsFilter.value = months;
      loadDashboardData();
    };

    // 월 이동 제어 기능 (US1 MVP)
    const changeMonth = (offset) => {
      let year = selectedYear.value;
      let month = selectedMonth.value + offset;

      if (month > 12) {
        month = 1;
        year += 1;
      } else if (month < 1) {
        month = 12;
        year -= 1;
      }

      selectedYear.value = year;
      selectedMonth.value = month;
      loadLedgerList();
      loadDashboardData();
    };

    // 업로드된 영수증 날짜의 월로 대시보드 포커스 강제 동기화 (US1 MVP)
    const syncDashboardMonthToReceipt = (dateStr) => {
      if (!dateStr) return;
      try {
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
          selectedYear.value = date.getFullYear();
          selectedMonth.value = date.getMonth() + 1;
        }
      } catch (e) {
        console.error('Failed to sync dashboard month to receipt date', e);
      }
    };

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

    const goToMyTemplates = () => {
      if (router) {
        router.push({ name: 'MyTemplateList' });
      } else {
        window.location.hash = '/my/templates';
      }
    };

    // 영수증 파일 감지 성공 시 호출 (비동기 업로드 E2E 구동)
    const onFileDetected = async (file) => {
      clearError();
      isUploading.value = true;
      pollingStatus.value = null;

      try {
        const compressed = await compressImage(file);
        const response = await uploadReceiptApi(compressed, file.name);
        const jobId = response.job_id;
        const status = response.status;
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
          parsedData.value = response.data;
          pollingStatus.value = 'COMPLETED';
          syncDashboardMonthToReceipt(response.data.transaction_date);
          loadLedgerList();
          loadDashboardData();
        } else {
          pollingStatus.value = status;
          pendingJobs.value.push({
            id: jobId,
            status: status,
            raw_file_name: file.name
          });
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
          pendingJobs.value = pendingJobs.value.filter(j => j.id !== jobId);
          syncDashboardMonthToReceipt(completedData.transaction_date);
          loadLedgerList();
          loadDashboardData();
        },
        (error) => {
          onValidationError(error.message || '비동기 폴링 상태 조회에 실패했습니다.');
          pollingStatus.value = 'FAILED';
          pendingJobs.value = pendingJobs.value.filter(j => j.id !== jobId);
        },
        (newStatus) => {
          const job = pendingJobs.value.find(j => j.id === jobId);
          if (job) {
            job.status = newStatus;
          }
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

    const formattedMonthlyTotal = computed(() => {
      const total = ledgerList.value.reduce((acc, item) => acc + Number(item.total_amount), 0);
      return total.toLocaleString();
    });

    const pieChartData = computed(() => {
      const categories = dashboardData.value.category_spending || [];
      const colors = [
        '#10B981', // emerald-500
        '#3B82F6', // blue-500
        '#EC4899', // pink-500
        '#F59E0B', // amber-500
        '#8B5CF6', // violet-500
        '#EF4444', // red-500
        '#6B7280'  // gray-500 (미분류 fallback)
      ];
      return {
        labels: categories.map(c => c.category_name),
        datasets: [{
          backgroundColor: categories.map((_, i) => colors[i % colors.length]),
          borderWidth: 0,
          data: categories.map(c => c.amount)
        }]
      };
    });

    const barChartData = computed(() => {
      const trends = dashboardData.value.monthly_trends || [];
      return {
        labels: trends.map(t => t.month),
        datasets: [{
          label: '월별 지출액',
          backgroundColor: 'rgba(79, 70, 229, 0.85)',
          hoverBackgroundColor: 'rgba(79, 70, 229, 1)',
          borderRadius: 6,
          borderSkipped: false,
          data: trends.map(t => t.amount)
        }]
      };
    });

    return {
      ledgerList,
      pendingJobs,
      formattedMonthlyTotal,
      currentUsername,
      currentFile,
      parsedData,
      isUploading,
      errorMessage,
      pollingStatus,
      isEditModalOpen,
      selectedLedgerForEdit,
      isDeleteModalOpen,
      selectedLedgerForDelete,
      selectedYear,
      selectedMonth,
      dashboardData,
      selectedMonthsFilter,
      currentMonthStr,
      pieChartData,
      barChartData,
      openEditModal,
      openDeleteModal,
      handleEditSave,
      handleDeleteConfirm,
      onBudgetUpdated,
      handleLogout,
      goToMyTemplates,
      onFileDetected,
      onFileRemoved,
      onValidationError,
      changeMonth,
      updateMonthsFilter
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
.word-break-keep-all {
  word-break: keep-all;
}
</style>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100 p-6 md:p-10 font-sans flex flex-col items-center transition-colors duration-300">
    <!-- 공통 네비바 컴포넌트 장착 -->
    <NavBar />

    <div class="w-full max-w-7xl space-y-8">
      
      <!-- 헤더 섹션 (그라데이션 타이틀) -->
      <div class="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
        <div>
          <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-500 dark:from-emerald-400 dark:via-teal-400 dark:to-indigo-400 bg-clip-text text-transparent">
            가맹점 파싱 템플릿 관리
          </h1>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">
            로컬 바이패스 템플릿의 실시간 자동 학습, 강등, 블랙리스트 격리 상태를 모니터링합니다.
          </p>
        </div>
      </div>

      <!-- 필터링 및 검색 카드 -->
      <div class="bg-white dark:bg-slate-900/60 backdrop-blur-md border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-md dark:shadow-xl space-y-4">
        <h2 class="text-lg font-bold text-slate-850 dark:text-slate-200 flex items-center space-x-2">
          <span>🔍 조건 필터링</span>
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          <!-- 사업자번호 검색 -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">사업자등록번호</label>
            <input
              type="text"
              v-model="filters.vendor_registration_number"
              placeholder="예: 1208147526"
              class="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-550 dark:focus:border-emerald-500 focus:ring-1 focus:ring-emerald-550 dark:focus:ring-emerald-500 transition duration-200 font-mono"
              @input="debounceSearch"
            />
          </div>

          <!-- 검증 상태 필터 -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-550 dark:text-slate-400 uppercase tracking-wider">검증 상태</label>
            <select
              v-model="filters.is_verified"
              class="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-550 dark:focus:border-emerald-500 transition duration-200"
              @change="fetchTemplatesList"
            >
              <option value="">전체 보기</option>
              <option value="true">검증 완료 (우회)</option>
              <option value="false">자동 학습 중</option>
            </select>
          </div>

          <!-- 블랙리스트 상태 필터 -->
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-slate-550 dark:text-slate-400 uppercase tracking-wider">블랙리스트 여부</label>
            <select
              v-model="filters.is_blacklisted"
              class="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-550 dark:focus:border-emerald-500 transition duration-200"
              @change="fetchTemplatesList"
            >
              <option value="">전체 보기</option>
              <option value="true">차단됨 (블랙리스트)</option>
              <option value="false">정상 작동</option>
            </select>
          </div>

          <!-- 초기화 버튼 -->
          <div class="flex items-end">
            <button
              @click="resetFilters"
              class="w-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm font-semibold py-2.5 px-4 rounded-xl transition duration-200 border border-slate-300 dark:border-slate-700/50 hover:border-slate-400 dark:hover:border-slate-600"
            >
              필터 초기화
            </button>
          </div>
        </div>
      </div>

      <!-- 템플릿 목록 테이블 카드 -->
      <div class="bg-slate-905 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-md dark:shadow-2xl">
        <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
          <div class="w-10 h-10 border-4 border-slate-200 dark:border-slate-800 border-t-emerald-500 rounded-full animate-spin"></div>
          <p class="text-slate-500 dark:text-slate-400 text-sm">템플릿 목록을 로드하는 중입니다...</p>
        </div>

        <div v-else-if="error" class="p-8 text-center space-y-4">
          <p class="text-rose-650 dark:text-rose-400 font-medium">{{ error }}</p>
          <button @click="fetchTemplatesList" class="px-4 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-350 dark:border-slate-750 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-semibold hover:bg-slate-200 dark:hover:bg-slate-700 transition">
            다시 시도
          </button>
        </div>

        <div v-else-if="templates.length === 0" class="p-16 text-center text-slate-550 dark:text-slate-400">
          <p class="text-lg">조건에 맞는 가맹점 템플릿이 존재하지 않습니다.</p>
          <p class="text-xs text-slate-450 dark:text-slate-500 mt-2">사업자번호나 필터링 조건을 다시 확인해 보세요.</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">가맹점명</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">사업자번호</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">상태</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">일관성 누적</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">자가치유 시도</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">최근 자가치유</th>
                <th class="px-6 py-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-right">관리</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 dark:divide-slate-800/50">
              <TemplateListItem
                v-for="template in templates"
                :key="template.id"
                :template="template"
              />
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script>
import { getTemplates } from '../../services/adminService';
import TemplateListItem from '../../components/admin/TemplateListItem.vue';
import NavBar from '../../components/NavBar.vue';

export default {
  name: 'TemplateList',
  components: {
    TemplateListItem,
    NavBar
  },
  data() {
    return {
      templates: [],
      filters: {
        vendor_registration_number: '',
        is_verified: '',
        is_blacklisted: ''
      },
      loading: false,
      error: null,
      searchTimeout: null
    };
  },
  mounted() {
    this.fetchTemplatesList();
  },
  methods: {
    async fetchTemplatesList() {
      this.loading = true;
      this.error = null;
      try {
        const response = await getTemplates(this.filters);
        this.templates = response.results || [];
      } catch (err) {
        this.error = err.message || '목록을 불러오는 데 실패했습니다.';
      } finally {
        this.loading = false;
      }
    },
    debounceSearch() {
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout);
      }
      this.searchTimeout = setTimeout(() => {
        this.fetchTemplatesList();
      }, 400);
    },
    resetFilters() {
      this.filters.vendor_registration_number = '';
      this.filters.is_verified = '';
      this.filters.is_blacklisted = '';
      this.fetchTemplatesList();
    }
  }
};
</script>

<style scoped>
/* 커스텀 테이블 배경색 지정 */
.bg-slate-905 {
  background-color: white;
}
@media (prefers-color-scheme: dark) {
  .bg-slate-905 {
    background-color: #0b1329;
  }
}
:global(.dark) .bg-slate-905 {
  background-color: #0b1329;
}
</style>

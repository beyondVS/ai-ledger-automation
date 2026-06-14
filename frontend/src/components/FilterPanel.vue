<template>
  <div class="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-lg transition-colors duration-300 mb-8 select-none">
    
    <!-- 필터 타이틀 및 접기/펴기 -->
    <div class="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-800 mb-4 cursor-pointer" @click="isExpanded = !isExpanded">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4 text-indigo-500">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
        </svg>
        <span class="text-xs font-black text-slate-700 dark:text-slate-200 tracking-tight">상세 검색 및 다차원 필터</span>
      </div>
      <button class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
        <svg v-if="isExpanded" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
          <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>
    </div>

    <!-- 필터 본문 (Accordion 형태로 접고 펴기) -->
    <transition name="expand">
      <div v-show="isExpanded" class="space-y-5">
        
        <!-- 그리드 레이아웃: 상호명, 기간, 금액 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          <!-- 1. 상호명 검색 -->
          <div class="space-y-1.5">
            <label class="block text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">상호명</label>
            <input
              type="text"
              v-model="filters.q"
              placeholder="예: 스타벅스"
              class="w-full h-11 px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>

          <!-- 2. 기간 검색 (시작/종료일) -->
          <div class="space-y-1.5">
            <label class="block text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">조회 기간</label>
            <div class="flex items-center gap-1.5">
              <input
                type="date"
                v-model="filters.start_date"
                class="w-full h-11 px-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
              />
              <span class="text-slate-400 font-bold text-xs">~</span>
              <input
                type="date"
                v-model="filters.end_date"
                class="w-full h-11 px-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
              />
            </div>
          </div>

          <!-- 3. 금액 범위 검색 -->
          <div class="space-y-1.5">
            <label class="block text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">결제 금액 대역</label>
            <div class="flex items-center gap-1.5">
              <input
                type="number"
                v-model.number="filters.min_amount"
                placeholder="최소"
                class="w-full h-11 px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
              />
              <span class="text-slate-400 font-bold text-xs">~</span>
              <input
                type="number"
                v-model.number="filters.max_amount"
                placeholder="최대"
                class="w-full h-11 px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
              />
            </div>
          </div>

        </div>

        <!-- 4. 카테고리 다중 선택 (OR 조건) -->
        <div class="space-y-2">
          <label class="block text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">카테고리 다중 선택</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="cat in categoryOptions"
              :key="cat"
              @click="toggleCategory(cat)"
              type="button"
              class="px-3 py-1.5 rounded-full border text-2xs font-semibold hover:scale-[1.03] active:scale-[0.97] transition-all cursor-pointer select-none"
              :class="isCategorySelected(cat)
                ? 'bg-indigo-600 border-indigo-600 text-white shadow-md shadow-indigo-600/10'
                : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-350 dark:hover:border-slate-700'"
            >
              {{ cat }}
            </button>
          </div>
        </div>

        <!-- 액션 버튼 영역 -->
        <div class="flex justify-end gap-2.5 pt-3 border-t border-slate-100 dark:border-slate-800">
          <button
            @click="resetFilters"
            type="button"
            class="px-4 py-2 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900 text-2xs font-bold transition-all cursor-pointer"
          >
            필터 초기화
          </button>
          <button
            @click="applyFilters"
            type="button"
            class="px-5 py-2 bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white rounded-xl text-2xs font-bold shadow-md shadow-indigo-600/10 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
          >
            필터 적용
          </button>
        </div>

      </div>
    </transition>

  </div>
</template>

<script>
import { ref, reactive } from 'vue';

export default {
  name: 'FilterPanel',
  emits: ['filter-change'],
  setup(props, { emit }) {
    const isExpanded = ref(true);

    // 가계부 기본 대표 카테고리 구성 목록
    const categoryOptions = ['식비', '쇼핑', '마트', '주거/통신', '의료/건강', '금융/보험', '문화/여가', '교통/차량', '카페/간식', '교육/육아', '생활/기타', '미분류'];
    
    const selectedCategories = ref([]);

    const filters = reactive({
      q: '',
      start_date: '',
      end_date: '',
      min_amount: '',
      max_amount: ''
    });

    const toggleCategory = (cat) => {
      const idx = selectedCategories.value.indexOf(cat);
      if (idx > -1) {
        selectedCategories.value.splice(idx, 1);
      } else {
        selectedCategories.value.push(cat);
      }
    };

    const isCategorySelected = (cat) => {
      return selectedCategories.value.includes(cat);
    };

    const applyFilters = () => {
      // 카테고리 다중 선택 건은 쉼표 구분 문자열(categories=식비,쇼핑)로 묶어 백엔드 API 계약에 호환
      const payload = {
        q: filters.q,
        categories: selectedCategories.value.join(','),
        start_date: filters.start_date,
        end_date: filters.end_date,
        min_amount: filters.min_amount,
        max_amount: filters.max_amount
      };
      emit('filter-change', payload);
    };

    const resetFilters = () => {
      filters.q = '';
      filters.start_date = '';
      filters.end_date = '';
      filters.min_amount = '';
      filters.max_amount = '';
      selectedCategories.value = [];
      
      applyFilters();
    };

    return {
      isExpanded,
      categoryOptions,
      selectedCategories,
      filters,
      toggleCategory,
      isCategorySelected,
      applyFilters,
      resetFilters
    };
  }
};
</script>

<style scoped>
/* 슬라이딩 높이 애니메이션 */
.expand-enter-active,
.expand-leave-active {
  transition: max-height 0.3s ease-in-out, opacity 0.3s ease-in-out;
  max-height: 500px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>

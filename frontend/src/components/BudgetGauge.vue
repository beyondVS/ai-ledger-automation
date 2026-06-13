<template>
  <div 
    class="budget-gauge-card p-6 bg-white dark:bg-slate-900 border rounded-2xl shadow-xl relative overflow-visible transition-all duration-300"
    :class="budget.spent_ratio >= 100 ? 'border-rose-500 dark:border-rose-500 animate-pulse-glow-red ring-2 ring-rose-500/10' : 'border-slate-200 dark:border-slate-800 hover:border-slate-350 dark:hover:border-slate-700'"
  >
    <div class="flex justify-between items-center mb-4">
      <div>
        <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">당월 지출 예산</h3>
        <p class="text-2xl font-bold text-slate-900 dark:text-white mt-1">
          {{ formatCurrency(budget.amount) }}
        </p>
      </div>
      <button 
        @click.stop="openModal"
        class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors duration-200 cursor-pointer"
        title="예산 수정"
      >
        <!-- Edit Icon -->
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.83 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
        </svg>
      </button>
    </div>
 
    <!-- Gauge Bar -->
    <div class="mt-4">
      <div class="w-full bg-slate-200 dark:bg-slate-800 h-3 rounded-full overflow-visible relative">
        <div 
          class="h-full rounded-full transition-all duration-500 ease-out"
          :class="statusClass"
          :style="{ width: `${clampedRatio}%` }"
        ></div>
        <!-- 시간 경과선 (Time-line Indicator) -->
        <div 
          v-if="timePassedRatio > 0 && timePassedRatio < 100"
          class="absolute top-[-4px] bottom-[-4px] w-0.5 bg-indigo-500 dark:bg-indigo-400 z-10 cursor-help group"
          :style="{ left: `${timePassedRatio}%` }"
        >
          <!-- 세로선 위 마커 점 (라이트 모드 시 회색 테두리 보정) -->
          <span class="absolute -top-1 -left-1 w-2.5 h-2.5 rounded-full bg-indigo-600 dark:bg-indigo-400 border border-slate-200 dark:border-slate-900 shadow-sm"></span>
          <!-- 호버 툴팁 -->
          <span class="absolute bottom-5 left-1/2 -translate-x-1/2 scale-0 group-hover:scale-100 transition-all duration-150 bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-2 py-1 rounded text-3xs font-semibold whitespace-nowrap z-20 shadow-md">
            시간 경과: {{ timePassedRatio.toFixed(0) }}% ({{ new Date().getDate() }}일)
          </span>
        </div>
      </div>
      <div class="flex justify-between items-center mt-2 text-xs font-medium">
        <span class="text-slate-500 dark:text-slate-400">소진율 {{ budget.spent_ratio.toFixed(1) }}%</span>
        <span :class="statusTextClass">
          {{ budget.status === 'danger' ? '예산 초과 주의!' : budget.status === 'warning' ? '주의 단계' : '안정적' }}
        </span>
      </div>
    </div>
 
    <div class="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/60">
      <div>
        <span class="text-xs text-slate-450 dark:text-slate-500">누적 지출</span>
        <p class="text-base font-semibold text-slate-800 dark:text-slate-200 mt-0.5">{{ formatCurrency(budget.spent_amount) }}</p>
      </div>
      <div class="text-right">
        <span class="text-xs text-slate-450 dark:text-slate-500">남은 예산</span>
        <p class="text-base font-semibold mt-0.5" :class="remainingClass">
          {{ formatCurrency(budget.remaining_amount) }}
        </p>
      </div>
    </div>
 
    <!-- Modal Portal / Teleport or Inline -->
    <Transition name="fade-blur">
      <div v-if="isModalOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
        <div 
          v-click-outside="closeModal"
          class="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl transform transition-all text-slate-900 dark:text-white"
        >
          <div class="flex justify-between items-center mb-6">
            <h4 class="text-lg font-bold text-slate-900 dark:text-white">이번 달 예산 편집</h4>
            <button @click="closeModal" class="text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors duration-150 cursor-pointer">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
 
          <form @submit.prevent="submitBudget">
            <div class="mb-5">
              <label class="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">예산 금액 (원)</label>
              <input 
                :value="formattedInputAmount"
                @input="onInputAmountChange"
                type="text" 
                class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                placeholder="예: 1,000,000"
                required
              />
              <p v-if="inputAmount > 0" class="text-xs text-emerald-600 dark:text-emerald-400 mt-2 font-medium">
                한글 표기: {{ koreanAmountText }}
              </p>
              <p v-if="errorMessage" class="text-xs text-rose-500 mt-2">{{ errorMessage }}</p>
            </div>
 
            <div class="flex justify-end gap-3">
              <button 
                type="button" 
                @click="closeModal" 
                class="px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
              >
                취소
              </button>
              <button 
                type="submit" 
                :disabled="isSubmitting"
                class="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-700 text-white font-semibold transition-all shadow-lg shadow-emerald-500/20 cursor-pointer"
              >
                {{ isSubmitting ? '저장 중...' : '예산 저장' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script>
import { upsertMonthlyBudget } from '../services/budgetService';

export default {
  name: 'BudgetGauge',
  props: {
    budget: {
      type: Object,
      required: true
    },
    currentMonthStr: {
      type: String,
      required: true // Format: 'YYYY-MM'
    }
  },
  emits: ['budget-updated'],
  data() {
    return {
      isModalOpen: false,
      inputAmount: 1000000,
      isSubmitting: false,
      errorMessage: ''
    };
  },
  computed: {
    clampedRatio() {
      return Math.min(Math.max(this.budget.spent_ratio, 0), 100);
    },
    statusClass() {
      if (this.budget.status === 'danger') return 'bg-gradient-to-r from-rose-600 to-rose-500';
      if (this.budget.status === 'warning') return 'bg-gradient-to-r from-amber-500 to-yellow-400';
      return 'bg-gradient-to-r from-emerald-500 to-teal-400';
    },
    statusTextClass() {
      if (this.budget.status === 'danger') return 'text-rose-600 dark:text-rose-400 font-semibold';
      if (this.budget.status === 'warning') return 'text-amber-600 dark:text-amber-400 font-semibold';
      return 'text-emerald-600 dark:text-emerald-400 font-semibold';
    },
    remainingClass() {
      return this.budget.remaining_amount < 0 ? 'text-rose-500 font-bold' : 'text-emerald-600 dark:text-emerald-400';
    },
    formattedInputAmount() {
      if (this.inputAmount === null || this.inputAmount === undefined || this.inputAmount === '') return '';
      return this.inputAmount.toLocaleString();
    },
    timePassedRatio() {
      const now = new Date();
      const currentYear = now.getFullYear();
      const currentMonth = now.getMonth(); // 0-indexed
      
      if (!this.currentMonthStr) return 0;
      const [budgetYear, budgetMonth] = this.currentMonthStr.split('-').map(Number);
      
      if (budgetYear < currentYear || (budgetYear === currentYear && budgetMonth < currentMonth + 1)) {
        return 100;
      }
      if (budgetYear > currentYear || (budgetYear === currentYear && budgetMonth > currentMonth + 1)) {
        return 0;
      }
      
      const totalDays = new Date(currentYear, currentMonth + 1, 0).getDate();
      const currentDay = now.getDate();
      return (currentDay / totalDays) * 100;
    },
    koreanAmountText() {
      const num = this.inputAmount;
      if (!num || isNaN(num) || num <= 0) return '0원';
      
      const units = ['', '만', '억', '조'];
      const numChars = ['', '일', '이', '삼', '사', '오', '육', '칠', '팔', '구'];
      let result = [];
      let temp = num;
      let unitIndex = 0;
      
      while (temp > 0) {
        const mod = temp % 10000;
        if (mod > 0) {
          let modStr = '';
          const thousands = Math.floor(mod / 1000);
          const hundreds = Math.floor((mod % 1000) / 100);
          const tens = Math.floor((mod % 100) / 10);
          const ones = mod % 10;
          
          if (thousands > 0) modStr += (thousands === 1 ? '' : numChars[thousands]) + '천';
          if (hundreds > 0) modStr += (hundreds === 1 ? '' : numChars[hundreds]) + '백';
          if (tens > 0) modStr += (tens === 1 ? '' : numChars[tens]) + '십';
          if (ones > 0) modStr += numChars[ones];
          
          const unit = units[unitIndex];
          if (unitIndex === 0) {
            result.unshift(modStr);
          } else {
            if (modStr === '일' || modStr === '') {
              result.unshift(unit);
            } else {
              result.unshift(modStr + unit);
            }
          }
        }
        temp = Math.floor(temp / 10000);
        unitIndex++;
      }
      
      return result.filter(Boolean).join(' ') + ' 원';
    }
  },
  methods: {
    formatCurrency(value) {
      return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(value);
    },
    onInputAmountChange(event) {
      const value = event.target.value;
      const cleanValue = value.replace(/[^0-9]/g, '');
      const num = parseInt(cleanValue, 10);
      this.inputAmount = isNaN(num) ? 0 : num;
      
      event.target.value = this.formattedInputAmount;
    },
    openModal() {
      this.inputAmount = this.budget.amount;
      this.errorMessage = '';
      this.isModalOpen = true;
    },
    closeModal() {
      this.isModalOpen = false;
    },
    async submitBudget() {
      if (this.inputAmount < 0) {
        this.errorMessage = '예산 금액은 0원 이상이어야 합니다.';
        return;
      }
      this.isSubmitting = true;
      this.errorMessage = '';
      try {
        const updatedBudget = await upsertMonthlyBudget(this.currentMonthStr, this.inputAmount);
        this.$emit('budget-updated', updatedBudget);
        this.closeModal();
      } catch (err) {
        this.errorMessage = err.message || '예산 저장 중 오류가 발생했습니다.';
      } finally {
        this.isSubmitting = false;
      }
    }
  },
  directives: {
    'click-outside': {
      beforeMount(el, binding) {
        el.clickOutsideEvent = function(event) {
          if (!(el === event.target || el.contains(event.target))) {
            binding.value(event);
          }
        };
        document.body.addEventListener('click', el.clickOutsideEvent);
      },
      unmounted(el) {
        document.body.removeEventListener('click', el.clickOutsideEvent);
      }
    }
  }
};
</script>

<style scoped>
.fade-blur-enter-active,
.fade-blur-leave-active {
  transition: opacity 0.3s ease, backdrop-filter 0.3s ease;
}
.fade-blur-enter-from,
.fade-blur-leave-to {
  opacity: 0;
  backdrop-filter: blur(0px);
}
</style>

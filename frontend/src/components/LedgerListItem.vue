<template>
  <div class="flex flex-col w-full">
    <!-- 가계부 마스터 카드 클릭 영역 -->
    <div 
      class="p-4 bg-slate-950 border border-slate-900/60 hover:border-slate-800 transition-all flex justify-between items-center cursor-pointer select-none"
      :class="isOpen ? 'rounded-t-xl border-b-0 border-slate-800/60' : 'rounded-xl'"
      @click="isOpen = !isOpen"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-sm font-bold text-slate-200 truncate">{{ ledger.vendor_name }}</span>
          <!-- 카테고리 뱃지 (T024) -->
          <span 
            v-if="ledger.category && ledger.category !== '미분류'"
            class="px-2 py-0.5 text-xxs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
          >
            {{ ledger.category }}
          </span>
          <span 
            v-else
            class="px-2 py-0.5 text-xxs font-semibold rounded-full bg-slate-800 text-slate-400 border border-slate-700/50"
          >
            미분류
          </span>
        </div>
        <span class="text-xxs text-slate-500 font-mono">{{ ledger.transaction_date }}</span>
      </div>
      
      <div class="flex items-center gap-4 flex-shrink-0">
        <div class="flex flex-col items-end gap-1">
          <span class="text-sm font-extrabold text-indigo-400 font-outfit">
            {{ Number(ledger.total_amount).toLocaleString() }}원
          </span>
          <span class="text-xxs text-slate-600 font-mono">
            세액: {{ Number(ledger.vat_amount).toLocaleString() }}원
          </span>
        </div>

        <!-- 수정/삭제 버튼 그룹 (Aesthetics WOW) -->
        <div class="flex items-center gap-1 border-l border-slate-800 pl-3">
          <button 
            type="button" 
            class="p-1.5 text-slate-500 hover:text-indigo-400 hover:bg-slate-900 rounded-lg transition-all"
            title="수정"
            @click.stop="$emit('edit', ledger)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
          <button 
            type="button" 
            class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-slate-900 rounded-lg transition-all"
            title="삭제"
            @click.stop="$emit('delete', ledger)"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
        
        <!-- 셰브론 회전 아이콘 (Aesthetics WOW) -->
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke-width="2.5" 
          stroke="currentColor" 
          class="w-4 h-4 text-slate-500 transition-transform duration-300"
          :class="{ 'rotate-180 text-indigo-400': isOpen }"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
    </div>

    <!-- 상세 아코디언 컴포넌트 -->
    <LedgerAccordion 
      :items="ledger.items" 
      :vendor-registration-number="ledger.vendor_registration_number" 
      :is-open="isOpen" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import LedgerAccordion from './LedgerAccordion.vue';

defineProps({
  ledger: {
    type: Object,
    required: true
  }
});

defineEmits(['edit', 'delete']);

const isOpen = ref(false);
</script>

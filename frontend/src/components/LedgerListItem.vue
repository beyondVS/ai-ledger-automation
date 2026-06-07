<template>
  <div class="flex flex-col w-full">
    <!-- 가계부 마스터 카드 클릭 영역 -->
    <div 
      class="p-4 bg-slate-950 border border-slate-900/60 hover:border-slate-800 transition-all flex justify-between items-center cursor-pointer select-none"
      :class="isOpen ? 'rounded-t-xl border-b-0 border-slate-800/60' : 'rounded-xl'"
      @click="isOpen = !isOpen"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <span class="text-sm font-bold text-slate-200 truncate">{{ ledger.vendor_name }}</span>
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

const isOpen = ref(false);
</script>

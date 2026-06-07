<template>
  <div
    class="accordion-content transition-all duration-300 ease-in-out overflow-hidden bg-slate-900/40 rounded-b-xl border-x border-b border-slate-800/80"
    :class="isOpen ? 'max-h-[1000px] opacity-100 py-4 px-6' : 'max-h-0 opacity-0 py-0 px-6'"
  >
    <!-- 상세 정보 요약 헤더 -->
    <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center pb-4 mb-4 border-b border-slate-800/60 gap-2">
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">사업자등록번호</span>
        <span class="text-sm font-medium text-slate-300 font-mono bg-slate-800/50 px-2.5 py-0.5 rounded border border-slate-700/30">
          {{ formattedBusinessNumber }}
        </span>
      </div>
      <div class="text-xs text-slate-400">
        총 <span class="text-indigo-400 font-bold font-mono">{{ items?.length || 0 }}</span>개 품목
      </div>
    </div>

    <!-- 품목 상세 테이블 -->
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse text-sm">
        <thead>
          <tr class="border-b border-slate-800 text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <th class="pb-2 font-medium">품목명</th>
            <th class="pb-2 text-right font-medium">단가</th>
            <th class="pb-2 text-center font-medium w-16">수량</th>
            <th class="pb-2 text-right font-medium">합계액</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/40 text-slate-300">
          <tr 
            v-for="(item, idx) in items" 
            :key="idx"
            class="hover:bg-slate-800/20 transition-colors duration-150"
          >
            <td class="py-2.5 pr-4 font-medium">{{ item.item_name }}</td>
            <td class="py-2.5 text-right font-mono">{{ formatCurrency(item.unit_price) }}원</td>
            <td class="py-2.5 text-center font-mono text-slate-400">{{ item.quantity }}</td>
            <td class="py-2.5 text-right font-mono text-indigo-300 font-semibold">
              {{ formatCurrency(item.amount || (Number(item.unit_price) * item.quantity)) }}원
            </td>
          </tr>
          <tr v-if="!items || items.length === 0">
            <td colspan="4" class="py-6 text-center text-slate-500 text-xs">
              상세 품목 데이터가 존재하지 않습니다.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  vendorRegistrationNumber: {
    type: String,
    default: ''
  },
  isOpen: {
    type: Boolean,
    default: false
  }
});

// 사업자등록번호 포맷팅 (1208112345 -> 120-81-12345)
const formattedBusinessNumber = computed(() => {
  if (!props.vendorRegistrationNumber) return '000-00-00000';
  const clean = props.vendorRegistrationNumber.replace(/\D/g, '');
  if (clean.length === 10) {
    return `${clean.substring(0, 3)}-${clean.substring(3, 5)}-${clean.substring(5)}`;
  }
  return props.vendorRegistrationNumber;
});

// 화폐 포맷팅 (천단위 콤마)
const formatCurrency = (val) => {
  const num = Number(val);
  if (isNaN(num)) return '0';
  return num.toLocaleString('ko-KR');
};
</script>

<style scoped>
/* 추가 미세 트랜지션/스타일링 */
.accordion-content {
  will-change: max-height, opacity;
}
</style>

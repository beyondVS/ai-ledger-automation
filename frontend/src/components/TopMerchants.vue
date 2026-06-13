<template>
  <div class="top-merchants-card p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl transition-all duration-300 hover:border-slate-700">
    <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6">이번 달 지출 TOP 3 가맹점</h3>

    <div v-if="merchants && merchants.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div 
        v-for="item in merchants" 
        :key="item.rank"
        class="merchant-item p-4 bg-slate-800/40 border border-slate-800/80 rounded-xl relative flex flex-col justify-between transition-transform duration-300 hover:-translate-y-1 hover:bg-slate-800/60"
      >
        <!-- Rank Badge -->
        <div class="absolute top-3 right-3 flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs shadow-md" :class="rankBadgeClass(item.rank)">
          {{ item.rank }}위
        </div>

        <div class="pr-10">
          <span class="text-xs text-slate-500 font-semibold uppercase">가맹점</span>
          <p class="text-base font-bold text-white truncate mt-1" :title="item.merchant_name">
            {{ item.merchant_name }}
          </p>
        </div>

        <div class="mt-4 pt-3 border-t border-slate-700/30 flex justify-between items-baseline">
          <span class="text-xs text-slate-400">누적 결제</span>
          <p class="text-lg font-bold text-slate-200">{{ formatCurrency(item.amount) }}</p>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex flex-col items-center justify-center py-12 text-slate-500 border border-dashed border-slate-800 rounded-xl">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 mb-3 text-slate-600">
        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5h.007m-.008 3h.007M3.75 12h.007m0 5.25h.007m0-6.75H12M3.75 3h16.5a1.5 1.5 0 0 1 1.5 1.5v15a1.5 1.5 0 0 1-1.5 1.5H3.75A1.5 1.5 0 0 1 2.25 19.5v-15A1.5 1.5 0 0 1 3.75 3Z" />
      </svg>
      <p class="text-sm">가맹점 지출 데이터가 아직 없습니다.</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TopMerchants',
  props: {
    merchants: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  methods: {
    formatCurrency(value) {
      return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(value);
    },
    rankBadgeClass(rank) {
      if (rank === 1) return 'bg-gradient-to-br from-yellow-400 to-amber-500 text-slate-900';
      if (rank === 2) return 'bg-gradient-to-br from-slate-300 to-slate-400 text-slate-900';
      return 'bg-gradient-to-br from-amber-700 to-amber-800 text-slate-100';
    }
  }
};
</script>

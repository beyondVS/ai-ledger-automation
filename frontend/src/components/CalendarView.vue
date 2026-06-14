<template>
  <div class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200/60 dark:border-slate-800/80 rounded-2xl p-4 sm:p-6 transition-colors duration-300">
    <!-- 달력 헤더: 요일 목록 -->
    <div class="grid grid-cols-7 gap-1 sm:gap-2 mb-3 text-center text-xs font-bold text-slate-500 dark:text-slate-400 select-none">
      <div class="py-2 text-rose-500">일</div>
      <div class="py-2">월</div>
      <div class="py-2">화</div>
      <div class="py-2">수</div>
      <div class="py-2">목</div>
      <div class="py-2">금</div>
      <div class="py-2 text-indigo-500">토</div>
    </div>

    <!-- 달력 본체: 격자 레이아웃 -->
    <div class="grid grid-cols-7 gap-1.5 sm:gap-3">
      <div
        v-for="(dayObj, index) in calendarDays"
        :key="index"
        :class="[
          'relative min-h-[72px] sm:min-h-[96px] rounded-xl p-1.5 sm:p-2.5 transition-all duration-200 flex flex-col justify-between border select-none',
          dayObj.isCurrentMonth
            ? 'bg-white dark:bg-slate-900 border-slate-200/50 dark:border-slate-800/60 cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-600 hover:scale-[1.02] active:scale-[0.98]'
            : 'bg-slate-100/40 dark:bg-slate-950/20 border-transparent text-slate-300 dark:text-slate-700 pointer-events-none',
          dayObj.isCurrentMonth && isToday(dayObj.dateStr) ? 'ring-2 ring-indigo-500/80 dark:ring-indigo-600/80 border-transparent' : ''
        ]"
        @click="dayObj.isCurrentMonth && handleDayClick(dayObj.dateStr)"
      >
        <!-- 상단 날짜 및 오늘/요일 색상 -->
        <div class="flex justify-between items-center w-full">
          <span
            :class="[
              'text-xs sm:text-sm font-bold',
              dayObj.isCurrentMonth
                ? isSunday(index)
                  ? 'text-rose-500'
                  : isSaturday(index)
                    ? 'text-indigo-500'
                    : 'text-slate-700 dark:text-slate-300'
                : 'text-slate-300 dark:text-slate-700',
              dayObj.isCurrentMonth && isToday(dayObj.dateStr) ? 'bg-indigo-600 text-white dark:text-white px-1.5 py-0.5 rounded-full text-2xs sm:text-xs' : ''
            ]"
          >
            {{ dayObj.day }}
          </span>

          <!-- 오늘 마커 점 -->
          <span v-if="dayObj.isCurrentMonth && isToday(dayObj.dateStr)" class="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
        </div>

        <!-- 하단: 일자별 지출 정보 -->
        <div v-if="dayObj.isCurrentMonth && hasSummary(dayObj.dateStr)" class="flex flex-col items-end gap-0.5 mt-2">
          <!-- 총 지출 금액 -->
          <span class="text-2xs sm:text-xs font-black text-slate-800 dark:text-slate-100 tracking-tight text-right break-all">
            {{ formatAmount(getSummary(dayObj.dateStr).total_amount) }}
          </span>
          <!-- 건수 요약 뱃지 -->
          <span class="text-4xs sm:text-3xs font-semibold px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200/30 dark:border-slate-700/30">
            {{ getSummary(dayObj.dateStr).count }}건
          </span>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'CalendarView',
  props: {
    year: {
      type: Number,
      required: true
    },
    month: {
      type: Number,
      required: true
    },
    // API로부터 전달받은 daily_summaries 맵 데이터
    dailySummaries: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['date-click'],
  setup(props, { emit }) {
    // 7열 달력 날짜 목록 계산
    const calendarDays = computed(() => {
      const days = [];
      const firstDayIndex = new Date(props.year, props.month - 1, 1).getDay(); // 0 = 일요일
      const lastDate = new Date(props.year, props.month, 0).getDate();

      // 이전 달의 빈 공간들
      for (let i = 0; i < firstDayIndex; i++) {
        days.push({ day: null, dateStr: null, isCurrentMonth: false });
      }

      // 이번 달의 일자들 생성
      for (let d = 1; d <= lastDate; d++) {
        const mm = String(props.month).padStart(2, '0');
        const dd = String(d).padStart(2, '0');
        const dateStr = `${props.year}-${mm}-${dd}`;
        days.push({
          day: d,
          dateStr,
          isCurrentMonth: true
        });
      }

      return days;
    });

    const isToday = (dateStr) => {
      const today = new Date();
      const y = today.getFullYear();
      const m = String(today.getMonth() + 1).padStart(2, '0');
      const d = String(today.getDate()).padStart(2, '0');
      return dateStr === `${y}-${m}-${d}`;
    };

    const isSunday = (index) => {
      return index % 7 === 0;
    };

    const isSaturday = (index) => {
      return index % 7 === 6;
    };

    const hasSummary = (dateStr) => {
      return !!props.dailySummaries[dateStr];
    };

    const getSummary = (dateStr) => {
      return props.dailySummaries[dateStr] || { total_amount: 0, count: 0 };
    };

    const formatAmount = (val) => {
      if (val === undefined || val === null) return '';
      // 가독성을 위해 원화 세자리 쉼표 표시 (원 표시 생략하여 공간 절약)
      return new Intl.NumberFormat('ko-KR').format(val) + '원';
    };

    const handleDayClick = (dateStr) => {
      emit('date-click', dateStr);
    };

    return {
      calendarDays,
      isToday,
      isSunday,
      isSaturday,
      hasSummary,
      getSummary,
      formatAmount,
      handleDayClick
    };
  }
};
</script>

<style scoped>
/* 초소형 폰트 추가 지원 (모바일 화면 대응) */
.text-3xs {
  font-size: 0.6rem;
}
.text-4xs {
  font-size: 0.5rem;
}
</style>

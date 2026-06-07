<template>
  <div class="shimmer-card w-full p-4 rounded-xl bg-slate-900/40 border border-indigo-500/20 shadow-md relative overflow-hidden">
    <!-- 빛 흐름 애니메이션 효과 (Aesthetics WOW) -->
    <div class="absolute inset-0 bg-gradient-to-r from-transparent via-slate-800/20 to-transparent -translate-x-full animate-shimmer"></div>

    <div class="flex justify-between items-center relative z-10">
      <!-- 좌측 정보 (파일명 및 상태) -->
      <div class="flex flex-col gap-2 min-w-0 w-2/3">
        <div class="flex items-center gap-2">
          <!-- 비동기 진행 핑 효과 -->
          <span class="h-2 w-2 rounded-full bg-indigo-500 animate-ping"></span>
          <span class="text-sm font-bold text-slate-300 truncate font-outfit">{{ job.raw_file_name }}</span>
        </div>
        
        <div class="flex items-center gap-2">
          <!-- 스켈레톤 바 -->
          <div class="shimmer-bar animate-pulse h-3 bg-slate-800 rounded w-24"></div>
          <span class="text-xxs font-mono text-indigo-400 font-semibold tracking-wider">
            {{ statusText }}
          </span>
        </div>
      </div>

      <!-- 우측 스켈레톤 금액 영역 -->
      <div class="flex flex-col items-end gap-1.5 w-1/3">
        <div class="shimmer-bar animate-pulse h-4 bg-slate-800 rounded w-16"></div>
        <div class="shimmer-bar animate-pulse h-3 bg-slate-800 rounded w-10"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  job: {
    type: Object,
    required: true
  }
});

const statusText = computed(() => {
  if (props.job.status === 'PROCESSING') {
    return 'AI 분석 진행 중';
  }
  return '분석 대기 중';
});
</script>

<style scoped>
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
.animate-shimmer {
  animation: shimmer 2.2s infinite ease-in-out;
}
</style>

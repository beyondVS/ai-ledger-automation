<template>
  <div class="w-full max-w-md mx-auto mt-6 bg-slate-900/60 dark:bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col gap-4 transition-all duration-300 hover:border-slate-700">
    <div class="flex items-center justify-between w-full">
      <div class="flex items-center space-x-4 min-w-0">
        <!-- 영수증 이미지 썸네일 또는 PDF 아이콘 -->
        <div class="relative w-14 h-14 rounded-lg overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center flex-shrink-0">
          <template v-if="file.type && file.type.startsWith('image/')">
            <img
              :src="file.previewUrl"
              alt="영수증 미리보기"
              class="w-full h-full object-cover"
            />
          </template>
          <template v-else>
            <span class="text-indigo-400 font-bold text-xs tracking-wider">PDF</span>
          </template>
        </div>

        <!-- 영수증 파일 메타정보 -->
        <div class="min-w-0">
          <h4 class="font-outfit text-sm font-semibold text-slate-100 truncate tracking-wide">
            {{ file.name }}
          </h4>
          <p class="font-mono text-xs text-slate-500 mt-1">
            {{ formatSize(file.size) }}
          </p>
        </div>
      </div>

      <!-- 삭제용 X 버튼 -->
      <button
        class="delete-btn p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/20 transition-all duration-200"
        aria-label="영수증 삭제"
        @click="$emit('file-removed')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- AI 분석 상태 표시 및 새 업로드 버튼 영역 -->
    <div class="border-t border-slate-800 pt-3 flex flex-col gap-3">
      <!-- 1) PENDING/PROCESSING (분석 진행 중) -->
      <div v-if="pollingStatus === 'PENDING' || pollingStatus === 'PROCESSING' || !pollingStatus" class="flex items-center justify-between text-xs">
        <div class="flex items-center gap-2 text-indigo-400 font-semibold">
          <svg class="animate-spin h-4 w-4 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>AI 영수증 분석 가동 중...</span>
        </div>
        <span class="text-slate-500 font-mono">대기 중</span>
      </div>

      <!-- 2) COMPLETED (분석 및 등록 완료) -->
      <div v-else-if="pollingStatus === 'COMPLETED'" class="flex flex-col gap-3">
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-2 text-emerald-400 font-semibold">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span>분석 및 가계부 자동 등록 완료!</span>
          </div>
          <span class="text-slate-500 font-mono">성공</span>
        </div>

        <!-- 드롭존 복구용 확인 버튼 (WOW UX 최적화) -->
        <button
          @click="$emit('file-removed')"
          class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/10 active:scale-98 transition-all duration-150 cursor-pointer text-center"
        >
          확인 및 새 영수증 등록하기
        </button>
      </div>

      <!-- 3) FAILED (분석 실패) -->
      <div v-else-if="pollingStatus === 'FAILED'" class="flex flex-col gap-3">
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center gap-2 text-rose-400 font-semibold">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
            <span>{{ failureReason || '영수증 분석에 실패했습니다.' }}</span>
          </div>
          <span class="text-slate-500 font-mono">오류</span>
        </div>

        <button
          @click="$emit('file-removed')"
          class="w-full py-2.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-rose-600/10 active:scale-98 transition-all duration-150 cursor-pointer text-center"
        >
          다시 시도하기
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  file: {
    type: Object,
    required: true
  },
  parsedData: {
    type: Object,
    default: null
  },
  pollingStatus: {
    type: String,
    default: null
  },
  failureReason: {
    type: String,
    default: null
  }
})

defineEmits(['file-removed'])

const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const dm = 2
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(dm) + ' ' + sizes[i]
}
</script>

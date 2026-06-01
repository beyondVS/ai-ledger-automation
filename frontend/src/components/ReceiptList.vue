<template>
  <div class="w-full max-w-md mx-auto mt-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-xl flex items-center justify-between transition-all duration-300 hover:border-slate-700">
    <div class="flex items-center space-x-4 min-w-0">
      <!-- 영수증 이미지 썸네일 또는 PDF 아이콘 (Aesthetics WOW 미세 튜닝) -->
      <div class="relative w-14 h-14 rounded-lg overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center flex-shrink-0">
        <template v-if="file.type.startsWith('image/')">
          <img
            :src="file.previewUrl"
            alt="영수증 미리보기"
            class="w-full h-full object-cover"
          />
        </template>
        <template v-else>
          <!-- PDF 파일용 고품격 텍스트 아이콘 -->
          <span class="text-indigo-400 font-bold text-xs tracking-wider">PDF</span>
        </template>
      </div>

      <!-- 영수증 파일 메타정보 (Inter & Outfit 글꼴 가독성) -->
      <div class="min-w-0">
        <h4 class="font-outfit text-sm font-semibold text-slate-100 truncate tracking-wide">
          {{ file.name }}
        </h4>
        <p class="font-mono text-xs text-slate-500 mt-1">
          {{ formatSize(file.size) }}
        </p>
      </div>
    </div>

    <!-- 삭제용 X 버튼 (hover 시 rose 스케일 전환 및 TDD 용 delete-btn 클래스 매핑) -->
    <button
      class="delete-btn p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-950/20 transition-all duration-200"
      aria-label="영수증 삭제"
      @click="$emit('file-removed')"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="2"
        stroke="currentColor"
        class="w-5 h-5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </div>
</template>

<script setup>
defineProps({
  file: {
    type: Object,
    required: true
  }
})

defineEmits(['file-removed'])

// 바이트 단위 크기를 가독성 높은 단위(KB, MB)로 안전하게 변환
const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const dm = 2
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(dm) + ' ' + sizes[i]
}
</script>

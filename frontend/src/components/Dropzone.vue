<template>
  <div
    class="relative overflow-hidden rounded-2xl border-2 border-dashed transition-all duration-300 ease-out p-8 md:p-12 flex flex-col items-center justify-center text-center cursor-pointer will-change-transform"
    :class="[
      isDragOver
        ? 'border-indigo-500 bg-indigo-950/20 shadow-[0_0_20px_rgba(99,102,241,0.15)] scale-[1.01] animate-pulse-glow'
        : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60 shadow-lg'
    ]"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
    @click="triggerFileInput"
  >
    <!-- 인터랙티브 그라데이션 오버레이 효과 -->
    <div class="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent pointer-events-none"></div>

    <!-- 네이티브 파일 인풋 (헌법 제V조 PWA 최적화 및 카메라 다이렉트 직촬영 사양 강력 준수) -->
    <input
      ref="fileInputRef"
      type="file"
      class="hidden"
      accept="image/png, image/jpeg, application/pdf"
      capture="environment"
      @change="onFileChange"
    />

    <!-- 업로드용 아름다운 일러스트레이션 아이콘 -->
    <div
      class="w-16 h-16 rounded-full flex items-center justify-center mb-5 transition-transform duration-500 ease-out"
      :class="isDragOver ? 'bg-indigo-500/20 text-indigo-400 scale-110' : 'bg-slate-800 text-slate-400 group-hover:scale-105'"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
        class="w-8 h-8"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    </div>

    <!-- 메인 타이틀 & 지침 문구 (Outfit 핀테크 글꼴) -->
    <h3 class="font-outfit text-xl font-semibold text-slate-100 mb-2 tracking-wide">
      {{ isDragOver ? '영수증을 여기에 떨어뜨리세요' : '영수증 파일 업로드' }}
    </h3>
    <p class="text-slate-400 text-sm max-w-sm leading-relaxed mb-1">
      여기에 파일을 끌어다 놓거나, 클릭하여 카메라 촬영 또는 파일을 선택해 주세요.
    </p>
    <p class="text-slate-500 text-xs font-mono tracking-tight mt-2">
      지원 형식: PNG, JPG, JPEG, PDF (최대 10MB)
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-detected', 'validation-error'])

const fileInputRef = ref(null)
const isDragOver = ref(false)

// 파일 선택 트리거
const triggerFileInput = () => {
  fileInputRef.value.click()
}

// 드래그 영역 오버 시 스타일 활성화
const onDragOver = () => {
  isDragOver.value = true
}

// 드래그 영역 아웃 시 스타일 원복
const onDragLeave = () => {
  isDragOver.value = false
}

// 드롭존 파일 드롭 핸들링
const onDrop = (event) => {
  isDragOver.value = false
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    processFile(files[0])
  }
}

// 파일 다이얼로그 선택 핸들링
const onFileChange = (event) => {
  const files = event.target.files
  if (files && files.length > 0) {
    processFile(files[0])
    // 동일 파일의 연속적인 재선택 감지를 위해 파일 값 리셋
    event.target.value = ''
  }
}

// 파일 정합성 1차 유효성 검사 및 바인딩 송출
const processFile = (file) => {
  // 1) 파일 크기 유효성 검사 (10MB 제한)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    emit('validation-error', '최대 파일 용량(10MB)을 초과하는 파일은 업로드할 수 없습니다.')
    return
  }

  // 2) 파일 확장자 형식 검사
  const allowedFormats = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf']
  if (!allowedFormats.includes(file.type)) {
    emit('validation-error', '지원하지 않는 파일 형식입니다. 이미지(JPG, PNG) 또는 PDF 파일만 업로드할 수 있습니다.')
    return
  }

  // 유효성 검사를 모두 충족한 정상 영수증 감지 데이터 발송
  emit('file-detected', file)
}
</script>

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

// 클라이언트 단 HTML5 Canvas API 활용 1차 이미지 리사이징 및 압축 (헌법 제V조 강력 준수)
const compressImage = (file) => {
  return new Promise((resolve, reject) => {
    // PDF 등 이미지가 아닌 경우는 압축 우회
    if (file.type === 'application/pdf') {
      resolve(file)
      return
    }

    const reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onload = (event) => {
      const img = new Image()
      img.src = event.target.result
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Canvas 2D context 획득 실패'))
          return
        }

        const MAX_WIDTH = 1000
        let width = img.width
        let height = img.height

        // 가로가 1000px을 초과하는 경우 비례축소 리사이징
        if (width > MAX_WIDTH) {
          height = Math.round((height * MAX_WIDTH) / width)
          width = MAX_WIDTH
        }

        canvas.width = width
        canvas.height = height
        ctx.drawImage(img, 0, 0, width, height)

        // Quality 0.8 JPEG 압축 바이트로 변환
        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error('Canvas blob 변환 실패'))
            return
          }
          const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + ".jpg", {
            type: 'image/jpeg',
            lastModified: Date.now()
          })
          resolve(compressedFile)
        }, 'image/jpeg', 0.8)
      }
      img.onerror = () => reject(new Error('이미지 로드 실패'))
    }
    reader.onerror = () => reject(new Error('파일 리더 오류'))
  })
}

// 파일 정합성 1차 유효성 검사 및 바인딩 송출
const processFile = async (file) => {
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

  try {
    // 1차 이미지 Canvas 압축 가동
    const processedFile = await compressImage(file)
    emit('file-detected', processedFile)
  } catch (err) {
    console.error('Image compression error:', err)
    emit('validation-error', '영수증 이미지 압축 전처리 중 에러가 발생했습니다.')
  }
}
</script>

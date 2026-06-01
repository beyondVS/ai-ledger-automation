<template>
  <main class="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 sm:p-12 selection:bg-indigo-500">
    <div class="w-full max-w-lg flex flex-col">
      <!-- 헤더 브랜드 영역 (Aesthetics WOW - Outfit/Inter 모던 타이틀) -->
      <header class="text-center mb-10 select-none">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-4 tracking-wide font-outfit uppercase">
          AI Automations
        </span>
        <h1 class="font-outfit text-4xl sm:text-5xl font-black text-slate-100 tracking-tight leading-none mb-3">
          Smart Ledger <span class="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-violet-400 to-indigo-500">Receipts</span>
        </h1>
        <p class="text-slate-400 text-sm sm:text-base font-normal tracking-wide max-w-sm mx-auto leading-relaxed">
          영수증 이미지를 올리면 고속 캐시 및 AI가 분석하여 가계부를 자동 작성합니다.
        </p>
      </header>

      <!-- 에러 피드백 알럿 영역 (Phase 5 겸용) -->
      <div 
        v-if="errorMessage"
        class="w-full max-w-md mx-auto mb-5 p-4 rounded-xl bg-rose-950/30 border border-rose-900/40 text-rose-200 text-sm flex items-start space-x-3 transition-all duration-300 shadow-md animate-fade-in"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5 flex-shrink-0 mt-0.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMessage }}</span>
      </div>

      <!-- 메인 인터랙티브 작업 공간 -->
      <div class="relative w-full max-w-md mx-auto">
        <!-- 드롭존 (수량 제약 및 1차 검사 바이패스) -->
        <Dropzone 
          v-if="!currentFile"
          @file-detected="onFileDetected"
          @validation-error="onValidationError"
        />

        <!-- 영수증 결과물 목록 피드백 (US2) -->
        <ReceiptList 
          v-else
          :file="currentFile"
          @file-removed="onFileRemoved"
        />
      </div>

      <!-- 정보 푸터 -->
      <footer class="text-center text-slate-600 text-xs font-mono tracking-wider mt-12 select-none">
        AI Ledger Automation v1.0.0 &copy; 2026
      </footer>
    </div>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import Dropzone from './components/Dropzone.vue'
import ReceiptList from './components/ReceiptList.vue'

const currentFile = ref(null)
const errorMessage = ref(null)
let errorTimeout = null

// 영수증 파일 감지 성공 시 호출 (reactive 모델 매핑)
const onFileDetected = (file) => {
  // 에러 상태 초기화
  clearError()

  // 브라우저 썸네일 미리보기를 위해 blob Object URL 생성 및 할당
  const previewUrl = URL.createObjectURL(file)

  // currentFile 상태 구조 매핑 (data-model 규격 강력 준수)
  currentFile.value = {
    id: typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : '018fe670-8b1d-7a6c-94eb-f072bbab4567',
    name: file.name,
    size: file.size,
    type: file.type,
    previewUrl: previewUrl,
    rawFile: file,
    createdAt: new Date().toISOString()
  }
}

// 영수증 파일 제거 시 (메모리 안전 해제)
const onFileRemoved = () => {
  if (currentFile.value) {
    // 메모리 누수 원천 차단을 위한 blob 주소 해제 실행
    URL.revokeObjectURL(currentFile.value.previewUrl)
  }
  currentFile.value = null
  clearError()
}

// 1차 유효성 검사 실패 수신 시 (Phase 5)
const onValidationError = (error) => {
  errorMessage.value = error
  
  // 기존 타이머 클리어 후 3초 간 노출 후 자동 소멸
  if (errorTimeout) clearTimeout(errorTimeout)
  errorTimeout = setTimeout(() => {
    errorMessage.value = null
  }, 3000)
}

const clearError = () => {
  errorMessage.value = null
  if (errorTimeout) clearTimeout(errorTimeout)
}
</script>

<style>
/* 부드러운 페이드인 애니메이션 */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}
</style>

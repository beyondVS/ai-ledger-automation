<template>
  <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
    <!-- Backdrop with blur -->
    <div class="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity delete-modal-backdrop" @click="$emit('close')"></div>

    <!-- Modal Card (Red Border Warning Design) -->
    <div class="relative w-full max-w-sm transform overflow-hidden rounded-2xl border border-rose-500/30 bg-slate-900/95 p-6 shadow-2xl backdrop-blur-md transition-all duration-300">
      
      <!-- Icon Indicator -->
      <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/10 mb-4 border border-rose-500/20">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </div>

      <!-- Content -->
      <div class="text-center mb-6">
        <h3 class="text-lg font-bold text-slate-100 mb-2">지출 내역 영구 삭제</h3>
        <p class="text-xs text-slate-400 leading-relaxed">
          <span class="font-bold text-indigo-400">{{ ledger.vendor_name }}</span> 내역을 정말 삭제하시겠습니까?<br>
          이 작업은 되돌릴 수 없으며 상세 품목도 함께 영구 삭제됩니다.
        </p>
      </div>

      <!-- Alert Message -->
      <div v-if="errorMessage" class="mb-4 rounded-lg bg-red-950/40 p-3 text-xs text-red-200 border border-red-900/30">
        {{ errorMessage }}
      </div>

      <!-- Buttons -->
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="flex-1 px-4 py-2.5 text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-xl transition-all border border-slate-700/50 btn-cancel"
          @click="$emit('close')"
          :disabled="isDeleting"
        >
          취소
        </button>
        <button
          type="button"
          class="flex-1 px-4 py-2.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-rose-500/50 transition-all flex items-center justify-center gap-1.5 btn-confirm"
          @click="handleDelete"
          :disabled="isDeleting"
        >
          <svg v-if="isDeleting" class="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isDeleting ? '삭제 중...' : '확정 및 삭제' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { deleteLedgerEntry } from '../services/ledgerService';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  ledger: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['close', 'confirm']);

const isDeleting = ref(false);
const errorMessage = ref('');

async function handleDelete() {
  isDeleting.value = true;
  errorMessage.value = '';
  
  try {
    await deleteLedgerEntry(props.ledger.id);
    emit('confirm');
    emit('close');
  } catch (error) {
    errorMessage.value = error.message || '삭제하는 동안 에러가 발생했습니다.';
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
    <!-- Backdrop with blur -->
    <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity modal-backdrop" @click="$emit('close')"></div>

    <!-- Modal Card (Glassmorphism design) -->
    <div class="relative w-full max-w-md transform overflow-hidden rounded-2xl border border-white/20 bg-white/70 p-6 shadow-2xl backdrop-blur-md transition-all duration-300">
      
      <!-- Close Button -->
      <button 
        type="button" 
        class="absolute right-4 top-4 rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
        @click="$emit('close')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <!-- Title -->
      <h3 class="text-xl font-bold text-slate-800 mb-6 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        지출 내역 수동 수정
      </h3>

      <!-- Alert Message -->
      <div v-if="errorMessage" class="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600 border border-red-200">
        {{ errorMessage }}
      </div>

      <!-- Edit Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Vendor Name -->
        <div>
          <label for="vendor_name" class="block text-sm font-semibold text-slate-700 mb-1">가맹점명</label>
          <input
            id="vendor_name"
            type="text"
            v-model="form.vendor_name"
            class="w-full rounded-xl border border-slate-200 bg-white/50 px-4 py-2.5 text-slate-800 placeholder-slate-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200/50 transition-all"
            placeholder="가맹점명을 입력하세요"
          />
          <p v-if="validationErrors.vendor_name" class="mt-1 text-xs font-medium text-red-500">
            {{ validationErrors.vendor_name }}
          </p>
        </div>

        <!-- Transaction Date -->
        <div>
          <label for="transaction_date" class="block text-sm font-semibold text-slate-700 mb-1">결제일자</label>
          <input
            id="transaction_date"
            type="datetime-local"
            v-model="form.transaction_date"
            class="w-full rounded-xl border border-slate-200 bg-white/50 px-4 py-2.5 text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200/50 transition-all"
          />
          <p v-if="validationErrors.transaction_date" class="mt-1 text-xs font-medium text-red-500">
            {{ validationErrors.transaction_date }}
          </p>
        </div>

        <!-- Total Amount -->
        <div>
          <label for="total_amount" class="block text-sm font-semibold text-slate-700 mb-1">결제금액 (원)</label>
          <input
            id="total_amount"
            type="number"
            v-model.number="form.total_amount"
            class="w-full rounded-xl border border-slate-200 bg-white/50 px-4 py-2.5 text-slate-800 placeholder-slate-400 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200/50 transition-all"
            placeholder="0"
            min="0"
          />
          <p v-if="validationErrors.total_amount" class="mt-1 text-xs font-medium text-red-500">
            {{ validationErrors.total_amount }}
          </p>
        </div>

        <!-- Category -->
        <div>
          <label for="category" class="block text-sm font-semibold text-slate-700 mb-1">카테고리</label>
          <select
            id="category"
            v-model="form.category"
            class="w-full rounded-xl border border-slate-200 bg-white/50 px-4 py-2.5 text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200/50 transition-all"
          >
            <option value="미분류">미분류</option>
            <option value="식비">식비</option>
            <option value="생활용품">생활용품</option>
            <option value="쇼핑">쇼핑</option>
            <option value="교통">교통</option>
            <option value="문화/여가">문화/여가</option>
            <option value="주거/통신">주거/통신</option>
            <option value="의료/건강">의료/건강</option>
            <option value="교육">교육</option>
            <option value="기타">기타</option>
          </select>
        </div>

        <!-- Receipt Camera Capture (T016, T017) -->
        <div>
          <label class="block text-sm font-semibold text-slate-700 mb-1">영수증 촬영 및 첨부</label>
          <div class="flex items-center gap-3">
            <label
              class="flex items-center gap-2 px-4 py-2.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-950 text-slate-700 dark:text-slate-300 rounded-xl cursor-pointer text-xs font-semibold transition-all select-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              영수증 촬영 (카메라)
              <input
                data-testid="receipt-input"
                type="file"
                accept="image/*"
                capture="environment"
                class="hidden"
                @change="handleReceiptFileChange"
              />
            </label>
            <span class="text-3xs text-slate-400 dark:text-slate-500">카메라가 작동하지 않으면 파일 보관함에서 선택하세요.</span>
          </div>

          <!-- 썸네일 미리보기 (T017) -->
          <div v-if="receiptPreviewUrl" class="mt-3 flex items-center gap-3 p-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-xl relative group">
            <img :src="receiptPreviewUrl" class="w-12 h-12 rounded-lg object-cover border border-slate-200 dark:border-slate-800" alt="영수증 썸네일" />
            <div class="text-3xs leading-normal overflow-hidden flex-1">
              <p class="font-semibold text-slate-700 dark:text-slate-300 truncate">{{ receiptFileName }}</p>
              <p class="text-slate-400 dark:text-slate-500">{{ receiptFileSizeText }}</p>
              <p v-if="isCompressing" class="text-indigo-500 dark:text-indigo-400 font-semibold animate-pulse">이미지 압축 가공 중...</p>
            </div>
            <button
              type="button"
              class="p-1 rounded-full text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-900 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              @click="clearReceipt"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
          <button
            type="button"
            class="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-xl transition-all"
            @click="$emit('close')"
            :disabled="isSubmitting"
          >
            취소
          </button>
          <button
            type="submit"
            class="px-5 py-2 text-sm font-semibold text-white bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 rounded-xl shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all flex items-center gap-1.5"
            :disabled="isSubmitting"
          >
            <svg v-if="isSubmitting" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ isSubmitting ? '저장 중...' : '변경사항 저장' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, reactive } from 'vue';
import { updateLedgerEntry } from '../services/ledgerService';
import { compressImage } from '../utils/imageCompressor';
import { uploadReceiptApi } from '../services/uploadService';

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

const emit = defineEmits(['close', 'save']);

const isSubmitting = ref(false);
const errorMessage = ref('');

const form = reactive({
  vendor_name: '',
  transaction_date: '',
  total_amount: 0,
  category: '미분류'
});

const validationErrors = reactive({
  vendor_name: '',
  transaction_date: '',
  total_amount: ''
});

// 영수증 카메라 촬영 및 압축 임시 버퍼 상태 변수들 (T017)
const receiptPreviewUrl = ref('');
const receiptFileName = ref('');
const receiptFileSizeText = ref('');
const isCompressing = ref(false);
const compressedReceiptBlob = ref(null); // 최종 전송할 압축 Blob 바인딩

const handleReceiptFileChange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  receiptFileName.value = file.name;
  receiptFileSizeText.value = `${(file.size / (1024 * 1024)).toFixed(2)} MB (원본)`;
  receiptPreviewUrl.value = URL.createObjectURL(file);
  isCompressing.value = true;
  compressedReceiptBlob.value = null;

  try {
    // T015 이미지 압축 연동
    const compressedBlob = await compressImage(file);
    compressedReceiptBlob.value = compressedBlob;
    receiptFileSizeText.value = `${(compressedBlob.size / (1024 * 1024)).toFixed(2)} MB (압축 완료)`;
  } catch (err) {
    console.error("영수증 압축 중 오류 발생:", err);
    // 압축 실패 시 에러 폴백 처리: 원본 이미지 유지
    compressedReceiptBlob.value = file;
  } finally {
    isCompressing.value = false;
  }
};

const clearReceipt = () => {
  if (receiptPreviewUrl.value) {
    URL.revokeObjectURL(receiptPreviewUrl.value);
  }
  receiptPreviewUrl.value = '';
  receiptFileName.value = '';
  receiptFileSizeText.value = '';
  compressedReceiptBlob.value = null;
};

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal && props.ledger) {
      form.vendor_name = props.ledger.vendor_name || '';
      if (props.ledger.transaction_date) {
        let dateVal = props.ledger.transaction_date;
        if (dateVal.length <= 10) {
          dateVal += 'T00:00';
        }
        form.transaction_date = dateVal.substring(0, 16);
      } else {
        form.transaction_date = '';
      }
      form.total_amount = props.ledger.total_amount || 0;
      
      // 카테고리 바인딩 누수 방지 방어 코드 (T013)
      const allowedCategories = ['미분류', '식비', '생활용품', '쇼핑', '교통', '문화/여가', '주거/통신', '의료/건강', '교육', '기타'];
      const currentCategory = props.ledger.category;
      form.category = allowedCategories.includes(currentCategory) ? currentCategory : '미분류';
      
      errorMessage.value = '';
      validationErrors.vendor_name = '';
      validationErrors.transaction_date = '';
      validationErrors.total_amount = '';
      
      // 모달 활성화 시 이전 업로드 버퍼 정리
      clearReceipt();
    }
  },
  { immediate: true }
);

function validateForm() {
  let isValid = true;
  validationErrors.vendor_name = '';
  validationErrors.transaction_date = '';
  validationErrors.total_amount = '';

  if (!form.vendor_name || form.vendor_name.trim() === '') {
    validationErrors.vendor_name = '가맹점명을 입력해주세요.';
    isValid = false;
  }
  if (!form.transaction_date) {
    validationErrors.transaction_date = '결제일자를 지정해주세요.';
    isValid = false;
  }
  if (form.total_amount === undefined || form.total_amount === null || form.total_amount === '') {
    validationErrors.total_amount = '결제금액을 입력해주세요.';
    isValid = false;
  } else if (Number(form.total_amount) < 0) {
    validationErrors.total_amount = '결제금액은 0원 이상이어야 합니다.';
    isValid = false;
  }

  return isValid;
}

async function handleSubmit() {
  if (!validateForm()) return;

  isSubmitting.value = true;
  errorMessage.value = '';

  try {
    // 촬영/첨부된 영수증이 존재하면 API 서버로 전송 기동 (T018)
    if (compressedReceiptBlob.value) {
      await uploadReceiptApi(compressedReceiptBlob.value, receiptFileName.value);
    }

    // 카테고리 전송 누수 방지 (T014)
    const allowedCategories = ['미분류', '식비', '생활용품', '쇼핑', '교통', '문화/여가', '주거/통신', '의료/건강', '교육', '기타'];
    const finalCategory = allowedCategories.includes(form.category) ? form.category : '미분류';

    const payload = {
      vendor_name: form.vendor_name,
      transaction_date: form.transaction_date ? `${form.transaction_date}:00Z` : '',
      total_amount: String(form.total_amount),
      category: finalCategory
    };

    const updated = await updateLedgerEntry(props.ledger.id, payload);
    emit('save', updated);
    emit('close');
  } catch (error) {
    errorMessage.value = error.message || '저장하는 동안 에러가 발생했습니다.';
  } finally {
    isSubmitting.value = false;
  }
}
</script>

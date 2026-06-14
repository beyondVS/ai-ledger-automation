<template>
  <div class="auth-container flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950 px-4 py-8 transition-colors duration-300">
    <div class="auth-card w-full max-w-md backdrop-blur-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl p-8 shadow-xl dark:shadow-2xl transition-all duration-300 hover:shadow-purple-500/5 dark:hover:shadow-purple-500/10 hover:border-purple-500/30 dark:hover:border-purple-500/20">
      
      <!-- 헤더 -->
      <div class="text-center mb-8">
        <h1 class="text-3xl font-extrabold bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-400 bg-clip-text text-transparent tracking-tight">
          AI Ledger Automation
        </h1>
        <p class="text-slate-500 dark:text-slate-400 mt-2 text-sm">
          금융 장부를 똑똑하게 기록하고 관리하세요
        </p>
      </div>

      <!-- 에러 알림 -->
      <div v-if="errorMsg" class="error-msg bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-xs mb-6 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>{{ errorMsg }}</span>
      </div>

      <!-- 로그인 폼 -->
      <form @submit.prevent="handleSubmit" class="space-y-6">
        <!-- 사용자 아이디 입력 -->
        <div>
          <label for="username" class="block text-slate-600 dark:text-slate-300 text-xs font-semibold uppercase tracking-wider mb-2">사용자명 (닉네임)</label>
          <div class="relative">
            <input 
              type="text" 
              id="username" 
              v-model="username" 
              placeholder="username"
              class="w-full bg-slate-50/50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-slate-800 dark:text-slate-200 text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all"
            />
          </div>
        </div>

        <!-- 비밀번호 입력 -->
        <div>
          <label for="password" class="block text-slate-600 dark:text-slate-300 text-xs font-semibold uppercase tracking-wider mb-2">비밀번호</label>
          <div class="relative">
            <input 
              type="password" 
              id="password" 
              v-model="password" 
              placeholder="••••••••"
              class="w-full bg-slate-50/50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3 text-slate-800 dark:text-slate-200 text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 transition-all"
            />
          </div>
        </div>

        <!-- 제출 버튼 -->
        <button 
          type="submit" 
          :disabled="isLoading"
          class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:scale-[0.98] text-white font-semibold text-sm rounded-xl py-3.5 shadow-lg shadow-purple-900/20 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100"
        >
          <span v-if="isLoading" class="spinner border-2 border-white/20 border-t-white rounded-full h-4 w-4 animate-spin"></span>
          <span>{{ isLoading ? '인증 진행 중...' : '로그인하기' }}</span>
        </button>
      </form>

      <!-- 하단 가입 링크 -->
      <div class="mt-8 text-center text-xs text-slate-500 dark:text-slate-400">
        아직 계정이 없으신가요? 
        <span @click="navigateToRegister" class="text-purple-600 dark:text-purple-400 hover:text-purple-500 dark:hover:text-purple-300 font-semibold cursor-pointer underline transition-all ml-1">
          무료로 계정 만들기
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { login } from '../../services/authService';

export default {
  name: 'LoginView',
  setup() {
    const router = useRouter();
    const username = ref('');
    const password = ref('');
    const errorMsg = ref('');
    const isLoading = ref(false);

    onMounted(() => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        document.documentElement.classList.remove('dark');
      } else {
        document.documentElement.classList.add('dark');
      }
    });

    const handleSubmit = async () => {
      errorMsg.value = '';

      if (!username.value || !username.value.trim()) {
        errorMsg.value = '사용자명을 입력해 주세요.';
        return;
      }

      if (!password.value) {
        errorMsg.value = '비밀번호를 입력해 주세요.';
        return;
      }

      isLoading.value = true;
      try {
        await login({
          username: username.value,
          password: password.value
        });
        
        // 로그인 성공 시 대시보드로 이동
        if (router) {
          router.push({ name: 'Dashboard' });
        } else {
          window.location.hash = '/dashboard';
        }
      } catch (err) {
        // 에러 알림 문구 화면 표시 (T007 테스트 만족)
        errorMsg.value = err.message || '인증에 실패했습니다. 아이디와 비밀번호를 확인해 주세요.';
      } finally {
        isLoading.value = false;
      }
    };

    const navigateToRegister = () => {
      if (router) {
        router.push({ name: 'Register' });
      } else {
        window.location.hash = '/register';
      }
    };

    return {
      username,
      password,
      errorMsg,
      isLoading,
      handleSubmit,
      navigateToRegister
    };
  }
};
</script>

<style scoped>
.auth-container {
  background-image: radial-gradient(circle at top right, rgba(139, 92, 246, 0.04), transparent 40%),
                    radial-gradient(circle at bottom left, rgba(79, 70, 229, 0.03), transparent 45%);
}
:global(.dark) .auth-container {
  background-image: radial-gradient(circle at top right, rgba(139, 92, 246, 0.08), transparent 40%),
                    radial-gradient(circle at bottom left, rgba(79, 70, 229, 0.05), transparent 45%);
}
</style>

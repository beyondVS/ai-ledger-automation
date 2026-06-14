<template>
  <nav class="w-full max-w-lg md:max-w-4xl lg:max-w-5xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-4 shadow-lg flex flex-col sm:flex-row justify-between items-center gap-4 mb-8 select-none transition-colors duration-300">
    <!-- 좌측: 브랜드 로고 및 페이지 명 -->
    <div class="flex items-center gap-3">
      <router-link to="/dashboard" class="flex items-center gap-2 group cursor-pointer">
        <!-- Logo Icon -->
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-500 to-indigo-500 flex items-center justify-center text-white font-black text-sm shadow-md shadow-emerald-500/10 group-hover:scale-105 transition-transform duration-200">
          S
        </div>
        <span class="font-outfit font-black text-lg text-slate-800 dark:text-slate-100 tracking-tight">
          Smart <span class="bg-clip-text text-transparent bg-gradient-to-r from-emerald-500 to-indigo-500 dark:from-emerald-400 dark:to-indigo-400">Ledger</span>
        </span>
      </router-link>

      <span class="hidden sm:inline h-4 w-px bg-slate-300 dark:bg-slate-800"></span>
      
      <!-- 현재 접속 유저 뱃지 -->
      <div class="flex items-center gap-1.5 text-2xs text-slate-500 dark:text-slate-400 bg-slate-200/50 dark:bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-300/40 dark:border-slate-800/60">
        <span class="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></span>
        <span class="font-semibold text-slate-700 dark:text-slate-200">{{ currentUsername }}</span>
      </div>
    </div>

    <!-- 우측: 내비게이션 및 제어 도구 -->
    <div class="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
      <!-- 탭 내비게이션 링크 -->
      <div class="flex items-center gap-1.5 p-1 rounded-xl bg-slate-200/60 dark:bg-slate-950 border border-slate-300/30 dark:border-slate-800/50 text-2xs font-semibold">
        <router-link
          to="/dashboard"
          class="px-3 py-1.5 rounded-lg transition-all duration-200 cursor-pointer"
          :class="isActiveRoute('/dashboard') 
            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/15' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
        >
          대시보드
        </router-link>
        <router-link
          to="/my/templates"
          class="px-3 py-1.5 rounded-lg transition-all duration-200 cursor-pointer"
          :class="isActiveRoute('/my/templates') 
            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/15' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
        >
          템플릿 관리
        </router-link>
        <router-link
          to="/settings"
          class="px-3 py-1.5 rounded-lg transition-all duration-200 cursor-pointer"
          :class="isActiveRoute('/settings') 
            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/15' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
        >
          설정
        </router-link>
        <router-link
          v-if="isStaff"
          to="/admin/templates"
          class="px-3 py-1.5 rounded-lg transition-all duration-200 cursor-pointer"
          :class="isActiveRoute('/admin/templates') 
            ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/15' 
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
        >
          어드민 템플릿
        </router-link>
      </div>

      <!-- 우측 끝: 테마 및 로그아웃 액션 버튼 그룹 -->
      <div class="flex items-center gap-2">
        <!-- 테마 토글 버튼 -->
        <button 
          @click="toggleTheme" 
          class="p-2 rounded-xl bg-slate-200 dark:bg-slate-950 border border-slate-300/60 dark:border-slate-800/60 text-slate-700 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-900 transition-all cursor-pointer"
          title="테마 전환"
        >
          <svg v-if="isDarkMode" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25c0 5.385 4.365 9.75 9.75 9.75 4.542 0 8.368-3.109 9.502-7.248Z" />
          </svg>
        </button>

        <!-- 로그아웃 버튼 -->
        <button 
          @click="handleLogout"
          class="p-2 rounded-xl bg-slate-200 dark:bg-slate-950 border border-slate-300/60 dark:border-slate-800/60 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-all cursor-pointer"
          title="로그아웃"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" class="w-4 h-4">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15M12 9l-3 3m0 0 3 3m-3-3h12.75" />
          </svg>
        </button>
      </div>
    </div>
  </nav>
</template>

<script>
import { ref, onMounted, onBeforeMount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { logout } from '../services/authService';

export default {
  name: 'NavBar',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const currentUsername = ref('사용자');
    const isDarkMode = ref(true);
    const isStaff = ref(false);

    // JWT payload base64 디코딩 헬퍼 함수
    const parseJwt = (token) => {
      try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
          atob(base64)
            .split('')
            .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join('')
        );
        return JSON.parse(jsonPayload);
      } catch (e) {
        return null;
      }
    };

    // Outfit 구글 웹 폰트 동적 헤더 로드
    onBeforeMount(() => {
      if (!document.getElementById('outfit-font')) {
        const link = document.createElement('link');
        link.id = 'outfit-font';
        link.rel = 'stylesheet';
        link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;900&display=swap';
        document.head.appendChild(link);
      }
    });

    onMounted(() => {
      // 1. 세션 사용자명 및 staff 여부 복원
      const sessionData = sessionStorage.getItem('ai_ledger_auth_session');
      if (sessionData) {
        try {
          const parsed = JSON.parse(sessionData);
          if (parsed && parsed.username) {
            currentUsername.value = parsed.username;
          }
          if (parsed && parsed.accessToken) {
            const payload = parseJwt(parsed.accessToken);
            if (payload && payload.is_staff) {
              isStaff.value = true;
            }
          }
        } catch (e) {
          console.error('Failed to parse session info in NavBar', e);
        }
      }

      // 2. 테마 초기 복원
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'light') {
        isDarkMode.value = false;
        document.documentElement.classList.remove('dark');
      } else {
        isDarkMode.value = true;
        document.documentElement.classList.add('dark');
      }
    });

    const toggleTheme = () => {
      isDarkMode.value = !isDarkMode.value;
      document.documentElement.classList.toggle('dark', isDarkMode.value);
      localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light');
    };

    const handleLogout = async () => {
      try {
        await logout();
        if (router) {
          router.push({ name: 'Login' });
        } else {
          window.location.hash = '/login';
        }
      } catch (err) {
        console.error('Logout error in NavBar', err);
      }
    };

    const isActiveRoute = (path) => {
      if (!route) return false;
      if (path === '/admin/templates') {
        return route.path.startsWith('/admin/templates');
      }
      return route.path === path;
    };

    return {
      currentUsername,
      isDarkMode,
      isStaff,
      toggleTheme,
      handleLogout,
      isActiveRoute
    };
  }
};
</script>

<style scoped>
.font-outfit {
  font-family: 'Outfit', sans-serif;
}
</style>

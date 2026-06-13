import { createRouter, createWebHistory } from 'vue-router';

// 컴포넌트 동적 로드 또는 직접 임포트
import LoginView from '../components/auth/LoginView.vue';
import RegisterView from '../components/auth/RegisterView.vue';
import DashboardView from '../components/DashboardView.vue';
import TemplateList from '../pages/admin/TemplateList.vue';
import TemplateDetail from '../pages/admin/TemplateDetail.vue';
import MyTemplateList from '../pages/MyTemplateList.vue';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresGuest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterView,
    meta: { requiresGuest: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: { requiresAuth: true }
  },
  {
    path: '/my/templates',
    name: 'MyTemplateList',
    component: MyTemplateList,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/templates',
    name: 'AdminTemplateList',
    component: TemplateList,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/templates/:id',
    name: 'AdminTemplateDetail',
    component: TemplateDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 라우터 가드 (Navigation Guard)
router.beforeEach((to, from, next) => {
  const sessionData = localStorage.getItem('ai_ledger_auth_session');
  let isAuthenticated = false;

  if (sessionData) {
    try {
      const parsed = JSON.parse(sessionData);
      // LocalStorage 내에 유효한 엑세스 토큰 존재 여부 체크
      if (parsed && parsed.accessToken) {
        isAuthenticated = true;
      }
    } catch (e) {
      localStorage.removeItem('ai_ledger_auth_session');
    }
  }

  // 로그인되지 않은 사용자가 보호된 페이지 접근 시 -> 로그인으로 리다이렉트
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login' });
  }
  // 이미 로그인된 사용자가 로그인/회원가입 진입 시 -> 대시보드로 리다이렉트
  else if (to.meta.requiresGuest && isAuthenticated) {
    next({ name: 'Dashboard' });
  } 
  else {
    next();
  }
});

export default router;

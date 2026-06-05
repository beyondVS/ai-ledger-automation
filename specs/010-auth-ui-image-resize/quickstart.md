# Quickstart: Frontend Authentication & Image Resizing

본 가이드는 `vue-router` 인증 가드 및 HTML5 Canvas 기반의 이미지 리사이징/압축 모듈을 프론트엔드에 빠르게 탑재하기 위한 개발 시작 서술서입니다.

---

## 1. 프론트엔드 라우팅 의존성 추가

라우터 가드 동작을 위해 `vue-router` 패키지를 프론트엔드 프로젝트 디렉토리에 설치해야 합니다.

```bash
cd frontend
npm install vue-router@4
```

---

## 2. 라우터 및 인증 가드 구현 예시 (`router/index.js`)

`frontend/src/router/index.js`를 생성하고, 아래와 같이 로그인 상태 검증 및 보호 구역 진입 통제 흐름을 구현합니다.

```javascript
import { createRouter, createWebHistory } from 'vue-router';

// 뷰 컴포넌트 임포트 (향후 작성 예정)
import LoginView from '../components/auth/LoginView.vue';
import RegisterView from '../components/auth/RegisterView.vue';
import DashboardView from '../components/DashboardView.vue'; // 보호된 구역 예시

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
      // 단순 토큰 존재 여부 체크 (실제로는 만료시간 비교 추가 권장)
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
```

---

## 3. 클라이언트 사이드 Canvas 이미지 리사이징 유틸리티 (`utils/imageResizer.js`)

업로드 실행 직전에 HTML5 Canvas API를 거쳐 가로/세로 중 긴 축을 1000px로 축소하고 JPEG 80%로 압축을 수행하는 핵심 모듈 코드 구조입니다.

```javascript
/**
 * HTML5 Canvas API를 이용하여 이미지를 리사이징하고 압축합니다.
 * @param {File} file - 원본 File 객체
 * @param {number} maxDimension - 최대 긴 축 해상도 (기본값: 1000px)
 * @param {number} quality - 압축 품질 (0.0 ~ 1.0, 기본값: 0.8)
 * @returns {Promise<File>} - 압축/리사이징이 완료된 새로운 File 객체
 */
export function resizeAndCompressImage(file, maxDimension = 1000, quality = 0.8) {
  return new Promise((resolve, reject) => {
    // 이미지 파일이 아니면 원본 그대로 즉시 승인 반환
    if (!file.type.startsWith('image/')) {
      return resolve(file);
    }

    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        // 1000px 이하 저해상도 이미지는 업사이징 방지를 위해 바로 원본 리턴
        if (width <= maxDimension && height <= maxDimension) {
          return resolve(file);
        }

        // 비율 유지 다운사이징 계산
        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // Canvas 버퍼를 JPEG 80% 압축 Blob으로 추출
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              return reject(new Error('Canvas to Blob conversion failed'));
            }
            // 기존 파일명 확장자를 .jpg로 보정 및 새로운 File 객체 래핑
            const compressedFile = new File([blob], file.name.replace(/\.[^/.]+$/, "") + ".jpg", {
              type: 'image/jpeg',
              lastModified: Date.now()
            });
            resolve(compressedFile);
          },
          'image/jpeg',
          quality
        );
      };
      img.onerror = (err) => reject(err);
    };
    reader.onerror = (err) => reject(err);
  });
}
```

---

## 4. 로컬 구동 및 유효성 테스트

의존성 설치와 라우터 등록을 마친 후 프론트엔드를 로컬에서 기동합니다:

```bash
cd frontend
npm run dev
```

브라우저 개발자 도구의 **Network** 탭을 활성화한 후 5MB 이상의 이미지를 업로드 창에 드롭하여, API 페이로드에 실려 나가는 바이너리 파일 용량이 극적으로 500KB 이하로 감소 및 확장자가 `.jpg`로 변환되어 전달되는지 모니터링하여 성공 기준을 확인하십시오.

/**
 * PWA 설치 및 환경 감지 헬퍼 유틸리티
 */

export const PWA_STORAGE_KEY = 'pwa-install-banner-state';
const COOLDOWN_DAYS = 7;
const COOLDOWN_MS = COOLDOWN_DAYS * 24 * 60 * 60 * 1000; // 7일 (밀리초)

/**
 * iOS 기기 여부 판별 (iPhone, iPad, iPod)
 */
export function isIOS() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
}

/**
 * iOS 기기 환경에서 순정 Safari 브라우저 여부 판별
 * (CriOS, FxiOS, OPiOS, KAKAOTALK, Instagram, Line 등 인앱 및 타사 브라우저 제외)
 */
export function isSafari() {
  if (!isIOS()) return false;
  const ua = navigator.userAgent;
  // Safari가 포함되어 있고 Chrome, Firefox, Opera, Kakao, Instagram 등 타사 키워드가 없는지 검사
  return /Safari/.test(ua) && !/(CriOS|FxiOS|OPiOS|mercury|KAKAOTALK|Instagram|FBAN|FBAV|Line)/i.test(ua);
}

/**
 * 이미 PWA 독립 실행형 모드(Standalone)로 실행 중인지 판별
 */
export function isStandalone() {
  if (typeof window === 'undefined') return false;
  const isNavStandalone = window.navigator.standalone === true;
  const isMediaStandalone = (typeof window.matchMedia === 'function')
    ? window.matchMedia('(display-mode: standalone)').matches
    : false;
  return isNavStandalone || isMediaStandalone;
}

/**
 * 닫기 쿨다운(7일 차단) 상태 여부 검사
 * @returns {boolean} true 면 아직 쿨다운 기간 중 (노출하면 안 됨), false 면 노출 가능
 */
export function checkCooldown() {
  if (typeof localStorage === 'undefined') return false;
  try {
    const stateStr = localStorage.getItem(PWA_STORAGE_KEY);
    if (!stateStr) return false;
    
    const state = JSON.parse(stateStr);
    if (!state || !state.dismissedAt) return false;
    
    const dismissedTime = new Date(state.dismissedAt).getTime();
    const currentTime = Date.now();
    
    // 마지막 닫은 시각으로부터 7일이 경과하지 않았으면 쿨다운 활성 (차단)
    return (currentTime - dismissedTime) < COOLDOWN_MS;
  } catch (e) {
    console.error('Failed to parse PWA install banner cooldown state', e);
    return false;
  }
}

/**
 * LocalStorage에 차단 쿨다운 기록 (현재 시각 저장)
 * @param {string} platform 감지된 플랫폼 정보
 */
export function setCooldown(platform = 'unknown') {
  if (typeof localStorage === 'undefined') return;
  try {
    const state = {
      dismissedAt: new Date().toISOString(),
      platform,
      standalone: isStandalone()
    };
    localStorage.setItem(PWA_STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error('Failed to save PWA install banner cooldown state', e);
  }
}

/**
 * LocalStorage 디버깅/재설정용 쿨다운 해제
 */
export function clearCooldown() {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(PWA_STORAGE_KEY);
}

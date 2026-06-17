# UI Interface Contract: PWA Install Banner Component

이 문서는 모바일 PWA 설치 제어 배너 및 iOS Safari 전용 툴팁 컴포넌트의 프론트엔드 인터페이스 규격을 정의합니다.

## 1. 컴포넌트 계약 (Vue.js Component Props & Events)

### Component Name: `PwaInstallBanner.vue`

이 컴포넌트는 전역 레이아웃 또는 최상위 앱 컨테이너에서 마운트되어 가동됩니다.

### Props (속성 입력)
*이 컴포넌트는 외부 파라미터 유입 없이 브라우저 자체 API 및 로컬 스토리지를 바탕으로 자율 제어되므로 Props는 없습니다.*

### Custom Events (이벤트 출력)

| 이벤트명 | 페이로드 | 발생 시점 |
| :--- | :--- | :--- |
| `status-change` | `{ visible: Boolean, platform: String }` | 배너가 화면에 완전히 나타나거나(visible: true) 닫기/설치 등으로 완전히 숨겨질 때(visible: false) 상태 변화를 부모 컴포넌트에 알립니다. |

---

## 2. 브라우저 API 연동 계약 (Native Browser Events Interface)

### A. beforeinstallprompt Event (Chrome / Android / Chromium)
- **수신 인터페이스 (Window Event Listener)**: `window.addEventListener('beforeinstallprompt', handler)`
- **동작**:
  1. 이벤트 발생 시 `e.preventDefault()`를 즉시 호출하여 브라우저의 디폴트 미니 정보창(Mini-infobar) 노출을 차단합니다.
  2. 수신된 이벤트 객체(`BeforeInstallPromptEvent`)를 컴포넌트 로컬의 `deferredPrompt` 참조 변수에 할당 보관합니다.
- **BeforeInstallPromptEvent 속성 활용**:
  - `prompt()`: 비동기 메서드로 사용자가 "설치하기" 버튼을 클릭할 때 실행하여 설치 동의 창을 사용자에게 노출시킵니다.
  - `userChoice`: 사용자의 동의 결과를 나타내는 Promise 객체입니다. 리턴 규격: `{ outcome: 'accepted' | 'dismissed', platform: String }`.

### B. Standalone Media Query & Native Check (iOS / Chrome / Safari)
- **Standalone 모드 대조**:
  ```javascript
  const isStandalone = window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches;
  ```

---

## 3. UI 렌더링 계약 (CSS & Tailwind 레이아웃 규격)

### A. Android 커스텀 설치 안내 배너
- **위치**: 모바일 화면 하단 고정 (`fixed bottom-0 left-0 w-full z-50`).
- **레이아웃**: 가로형 바 또는 슬림한 카드 디자인. 좌측에는 앱 브랜드 로고(또는 대표 아이콘)와 설치 유도 문구("가계부를 홈 화면에 추가하고 빠르게 사용해 보세요!"), 우측에는 "설치" 버튼과 X 버튼(닫기)을 한 행으로 배치.
- **디자인 스타일**: 프리미엄 다크 모드/라이트 모드 대응, 그림자 및 흐림 효과(`backdrop-blur-md bg-white/90 dark:bg-zinc-900/90 shadow-[0_-4px_24px_rgba(0,0,0,0.06)]`).

### B. iOS Safari 수동 가이드 툴팁 말풍선
- **위치**: 모바일 화면 최하단 공유 버튼 지향 고정 (`fixed bottom-6 left-1/2 -translate-x-1/2 w-[90%] max-w-sm z-50`).
- **레이아웃**: 말풍선 모양 디자인. 하단 정중앙에 아래 방향을 가리키는 삼각형 꼬리(`after:content-[''] after:absolute after:top-full after:left-1/2 after:-translate-x-1/2 after:border-8 after:border-t-white dark:after:border-t-zinc-900 after:border-transparent`)가 존재하여 브라우저의 공유 버튼 위치를 명확히 포인팅함.
- **콘텐츠**:
  1. 텍스트: "Safari 공유 버튼 [공유 아이콘] 을 누르고 **'홈 화면에 추가'**를 클릭하세요."
  2. Apple 순정 공유 아이콘 모양(네모 안에서 밖으로 뻗어나가는 화살표)을 이미지 또는 CSS 벡터로 렌더링하여 안내.
  3. 우측에 깔끔한 "닫기" 또는 아이콘 버튼 배치.
- **애니메이션**: 최초 3초 경과 후 `translate-y-4 opacity-0`에서 `translate-y-0 opacity-100`으로 부드럽게 slide-up transition 적용.

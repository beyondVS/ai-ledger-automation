# Research Notes: PWA Install Banner & iOS A2HS Tooltip

## 1. beforeinstallprompt API 제어

Android/Chrome 등 PWA 설치를 기본 지원하는 브라우저에서는 웹 앱의 설치 조건이 충족되면 `beforeinstallprompt` 이벤트가 트리거됩니다.

### 결정사항 (Decision)
- 브라우저 진입 후 발생하는 `beforeinstallprompt` 이벤트를 캡처하여 기본 브라우저 팝업을 즉시 억제(`e.preventDefault()`)합니다.
- 캡처한 이벤트 객체를 전역(또는 공통 상태 관리 오브젝트)에 보관해 둔 뒤, 진입 3초 후 띄워진 커스텀 하단 배너에서 사용자가 "설치하기" 버튼을 클릭할 때 해당 이벤트의 `.prompt()` 메서드를 트리거하여 설치 동의 창을 사용자에게 제시합니다.

### 타사 영향 및 고려된 대안
- **대안 1 (기본 팝업 방치)**: 브라우저가 제공하는 시점에 무작위로 기본 설치 팝업을 띄우는 방안.
  - *기각 사유*: 사용자의 흐름을 방해하고 설치 전환율의 통제가 불가능합니다.
- **대안 2 (자체 커스텀 모달 개발)**: 브라우저 API를 전혀 띄우지 않고 가짜 다운로드 UI를 만들어 앱스토어인 것처럼 행동하는 방법.
  - *기각 사유*: 보안 위반이며 실제 웹 앱 설치가 불가능합니다.

---

## 2. iOS/Safari 디바이스 판별 및 Standalone 모드 감지

iOS Safari는 `beforeinstallprompt`를 지원하지 않기 때문에, 사용자가 직접 Safari의 하단 도구 모음 내 공유 버튼을 누르고 '홈 화면에 추가'를 클릭해야만 앱으로 설치가 가능합니다.

### 결정사항 (Decision)
- **플랫폼 판별**: UserAgent 상에서 iOS 디바이스(iPhone, iPad, iPod)이면서 타사 브라우저(크롬, 파이어폭스, 인앱 브라우저 등)가 아닌 순정 **Safari 브라우저**인지 정밀 판별합니다.
  - 감지 로직:
    ```javascript
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    // CriOS = iOS Chrome, FxiOS = iOS Firefox, KAKAOTALK = 카카오톡 인앱
    const isSafari = isIOS && /Safari/.test(navigator.userAgent) && !/(CriOS|FxiOS|OPiOS|mercury|KAKAOTALK|Instagram)/.test(navigator.userAgent);
    ```
- **독립 실행 모드 감지**: 이미 홈 화면에 추가되어 독립 모드로 실행 중인 경우 배너를 노출하지 않아야 하므로 다음 검사들을 조합하여 PWA 가동 여부를 판단합니다.
  - 감지 로직:
    ```javascript
    const isStandalone = window.navigator.standalone || window.matchMedia('(display-mode: standalone)').matches;
    ```

### 고려된 대안
- **대안 1 (iOS 크롬 등 타 브라우저에서도 툴팁 안내)**:
  - *기각 사유*: iOS 타 브라우저는 시스템 제약으로 홈 화면 추가(A2HS) 버튼이 없거나 작동하지 않으므로 사용자의 혼란만 가중시킵니다. 사용자 의사에 따라 타사 브라우저는 완전 제외 처리로 결론지었습니다.

---

## 3. LocalStorage 기반 7일 쿨다운 제어

사용자가 커스텀 설치 배너나 Safari 가이드 툴팁을 수동으로 닫았을 때, 일주일간 배너가 다시 뜨지 않도록 제어해야 합니다.

### 결정사항 (Decision)
- 사용자가 "닫기" 버튼을 누르면 LocalStorage에 `pwa-install-banner-dismissed-at` 키로 현재 타임스탬프 밀리초 값을 기록합니다.
- 페이지 로드 후 3초 지연 로직이 돌기 전, LocalStorage 값을 검사하여 현재 시간과 마지막 닫은 시간의 차이가 `7일` (즉, `7 * 24 * 60 * 60 * 1000 = 604,800,000` 밀리초) 미만인 경우 배너 표출 타이머 작동을 원천 차단합니다.

---

## 4. UI 3초 지연 노출 및 Tailwind CSS 트랜지션

### 결정사항 (Decision)
- 페이지 진입 및 로드가 완료된 후 3초 지연 처리를 위해 Vue.js 3 컴포넌트의 `onMounted` 생명주기 훅 내에서 `setTimeout` 타이머를 기동시킵니다.
- 툴팁 및 배너는 Tailwind CSS의 `transition`, `duration-500`, `opacity` 클래스 및 슬라이드 효과(`translate-y` 변형)를 활용하여 부드럽고 프리미엄하게 화면 아래에서 위로(slide-up/fade-in) 솟아오르도록 micro-animation 스타일링을 구현합니다.
- 이로 인해 초기 화면 렌더링 부하를 극적으로 피하고 사용자가 대시보드 화면에 완전히 안착하여 집중한 직후 설치 안내 가이드를 우아하게 전달할 수 있습니다.

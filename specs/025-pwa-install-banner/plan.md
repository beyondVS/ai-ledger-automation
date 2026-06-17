# Implementation Plan: PWA Install Banner & iOS A2HS Tooltip

**Branch**: `025-pwa-install-banner` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/025-pwa-install-banner/spec.md`

## Summary

모바일 기기로 진입한 미설치 사용자들에게 PWA 설치(홈 화면에 추가)를 세련되게 유도하는 자동화 가이드를 설계하고 구현합니다.
- **Android/Chromium**: `beforeinstallprompt` 이벤트를 인터셉트하여 기본 UI를 억제한 뒤, 페이지 진입 3초 후에 가로형/카드형 커스텀 안내 배너를 서서히 팝업합니다. 사용자가 배너에서 "설치"를 누르면 억제해 둔 이벤트를 가동시켜 브라우저 공식 설치 확인 다이얼로그를 트리거합니다.
- **iOS Safari**: `beforeinstallprompt`가 미지원되는 제약을 극복하기 위해, iOS Safari 브라우저 사용자를 판별하여 하단 도구 모음(공유 버튼 영역)을 조준하는 말풍선 가이드 툴팁을 3초 지연 노출합니다.
- **예외 통제 및 쿨다운**: 이미 독립 모드(`standalone`)로 가동 중이거나, 설치가 불가능한 iOS 내 타사 브라우저(크롬, 파이어폭스, 인앱 브라우저 등) 환경인 경우 UI를 전면 숨김 처리합니다. 사용자가 UI를 닫으면 `LocalStorage`에 타임스탬프를 보존해 최소 7일간 노출을 완전 차단합니다.

---

## Technical Context

**Language/Version**: Python 3.13 (Backend), Vue.js 3 / JavaScript (Frontend)

**Primary Dependencies**: Vue.js 3, Tailwind CSS, LocalStorage

**Storage**: LocalStorage (브라우저 로컬 저장소 클라이언트 상태 관리)

**Testing**: Vitest & Vue Test Utils (컴포넌트 단위 테스트 및 LocalStorage 쿨다운 로직 검증)

**Target Platform**: Mobile Browsers (Android Chrome, iOS Safari)

**Project Type**: Web application (Frontend + Backend monorepo)

**Performance Goals**: 
- 사용자 웹 페이지 진입 3초 후 애니메이션 노출 (CPU 및 렌더링 부하 최소화)
- Android 커스텀 배너 내 "설치" 버튼 클릭 시 0.5초 이내 브라우저 순정 설치 창 노출

**Constraints**:
- **7일 쿨다운**: 사용자가 닫기 버튼 클릭 시 `pwa-install-banner-state` 키로 로컬 저장소에 시간 기록 및 7일간 재노출 방지.
- **독립 실행 감지**: 독립 실행형 모드(`display-mode: standalone` 또는 `window.navigator.standalone`) 검출 시 모든 가이드를 숨김 처리.
- **iOS 타 브라우저 제외**: Apple 공식 Safari 외의 타 브라우저(Chrome, KakaoTalk/Instagram 웹뷰 등) 진입 시 가이드를 전면 차단/생략.
- **보안 규칙 준수**: localhost 이외의 프로덕션 실환경에서는 HTTPS SSL 환경 하에서만 서비스 워커 및 PWA 매니페스트가 인지되므로 개발 시 `localhost:5173` 포트를 활용해 비-HTTPS로 편리하게 테스트 수행.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Gate Evaluation
- **Gate 1 (PWA & A2HS 웹 표준 수호)**: HTML5 Capture 및 PWA 매니페스트(`manifest.webmanifest`) 표준 명세를 수호하고 있는가?
  - *평가*: **통과(Pass)**. 이 설계는 브라우저의 표준 설치성 자격을 전제로 하며, iOS의 독립 실행성 감지와 Safari 순정 가이드라인을 분기 설계함으로써 모바일-first 표준 경험을 위배하지 않습니다.
- **Gate 2 (서비스 워커 캐시 오동작 방지)**: `sw.js` 상에서 크롬 확장 프로그램 스키마 간섭 오류를 우회하는 프로토콜 필터링이 수립되어 있는가?
  - *평가*: **통과(Pass)**. 기존 서비스 워커 내의 비-HTTP 스키마 요청 사전 우회 로직을 오염시키지 않고 순수 클라이언트 뷰 레이어에서 UI 연동만을 제어하므로 보안 및 인프라의 파괴를 유발하지 않습니다.
- **Gate 3 (인증 체계 수호)**: 가이드 배너 추가 시 sessionStorage에 있는 accessToken 및 httpOnly 쿠키 refresh_token 흐름에 간섭이 없는가?
  - *평가*: **통과(Pass)**. 본 UI 컴포넌트는 LocalStorage의 별도 전용 키(`pwa-install-banner-state`)만을 독립적으로 사용하며 인증 토큰 및 쿠키 통신 레이어를 일절 침범하거나 오염시키지 않습니다.

*결과: 어떠한 헌법 위배 위반 사항도 식별되지 않았습니다 (No Violations).*

---

## Project Structure

### Documentation (this feature)

```text
specs/025-pwa-install-banner/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── ui-contracts.md  # Phase 1 output
```

### Source Code (repository root)

```text
frontend/
├── public/
│   ├── manifest.webmanifest   # PWA 설정 명세
│   └── sw.js                  # 서비스 워커 파일 (캐시 방어 로직 내장)
└── src/
    ├── components/
    │   └── PwaInstallBanner.vue # [신규] 스마트 단말기 설치 제어 배너 및 iOS Safari 수동 가이드 컴포넌트
    ├── App.vue                # 최상위 앱 진입점 (PwaInstallBanner 컴포넌트 이식 대상)
    ├── registerServiceWorker.js # 서비스 워커 등록 스크립트
    └── index.css              # 전역 Tailwind 및 CSS 애니메이션 효과 정의
```

**Structure Decision**: PWA UI 요소 제어 기능이므로 순수 프론트엔드(`frontend/`) 디렉토리 하위의 컴포넌트 영역(`src/components/`)에 `PwaInstallBanner.vue` 단일 컴포넌트를 설계하여 모듈성을 극대화합니다. 최상위 레이아웃 컴포넌트인 `App.vue`에 이를 심어 가용 페이지 전반에 지연 노출 효과가 안정적으로 파이프라이닝되도록 통합합니다.

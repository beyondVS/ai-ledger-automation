# Research Report: frontend-dropzone-layout

**Created**: 2026-06-02

## 1. Vite + Vue 3 비대화형 초기화 방안

* **결정사항 (Decision)**: `npm create vite@latest frontend -- --template vue` 스크립트를 사용하여 `frontend` 디렉토리 내에 비대화형(Non-interactive)으로 Vue 3 + Vite 프로젝트를 초기 구축한다.
* **타당성 (Rationale)**: `npm create vite`는 대화형 프롬프트를 띄우지만, `-- --template vue` 아규먼트를 추가 바인딩하면 완전 비대화형으로 즉시 프론트엔드 보일러플레이트 구조를 구축할 수 있어 AI 오토메이션 환경에 완벽히 부합한다.
* **고려된 대안 (Alternatives considered)**:
  - `npx -y create-vue@latest`: 비대화형 기동 시 다양한 ESLint/Router/Pinia 등 체크 옵션 플래그가 매우 복잡하며, 가벼운 MVP 개발에는 과도한 아키텍처 오버헤드가 발생하므로 기각함.

## 2. Tailwind CSS 연동 및 Slate 다크 모드 구성 방안

* **결정사항 (Decision)**: Tailwind CSS v3(또는 프로젝트 호환 최신 에디션)를 설치하고 `postcss.config.js` 및 `tailwind.config.js`를 구성하며, `index.css`를 슬레이트 다크 모드(`bg-slate-900 text-slate-100`) 기반으로 뼈대 디자인 시스템을 적용한다.
* **타당성 (Rationale)**: 테일윈드의 유틸리티 클래스는 반응형 모바일 브레이크포인트(`sm:`, `md:`, `lg:`)를 간결하게 바인딩할 수 있으며, `slate` 색상군은 핀테크 가계부 서비스에 가장 알맞은 하이엔드 다크 미학(Aesthetics WOW)을 선사한다.
* **고려된 대안 (Alternatives considered)**:
  - Vanilla CSS 직접 코딩: 프로젝트 헌법 제VI조(크로스 플랫폼 대칭성 및 생산성)와 신속한 컴포넌트 퍼블리싱 수호 관점에서 개발 속도가 저하되므로 배제함.

## 3. 영수증 드롭존 컴포넌트 설계 및 Canvas 압축 바이패스 연계

* **결정사항 (Decision)**: HTML5 Drag and Drop API (`dragover`, `dragleave`, `drop`)를 감지하여 상태 변화를 렌더링하고, 단일 업로드 제한(최대 1개) 및 10MB 크기 유효성 검사를 거친 후, 헌법 제V조에 명시된 HTML5 Canvas 압축(가로 최대 1000px 리사이징) 호환 인터페이스를 선제 준비한다.
* **타당성 (Rationale)**: 헌법 제V조(Vision-First PWA)에서 요구하는 모바일 카메라 연동 및 Canvas 압축 규격을 충족하여 프론트엔드 단의 성능 및 트래픽 부하 경감 시너지를 사전에 방어할 수 있다.
* **고려된 대안 (Alternatives considered)**:
  - 써드파티 드롭존 라이브러리(vue-dropzone 등) 도입: 뷰 3 컴포지션 API와의 호환성 충돌 위험이 있고 단순 MVP 퍼블리싱 단계를 고려할 때 수동 감지 컴포넌트 작성이 훨씬 유연하고 가벼우므로 기각함.

# Implementation Plan: frontend-dropzone-layout

**Branch**: `007-frontend-dropzone-layout` | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-frontend-dropzone-layout/spec.md`

## Summary

본 구현 계획서는 가계부 및 영수증 자동화 서비스의 사용자 진입점인 프론트엔드 모듈의 초기 구조를 구축하는 개발 계획을 명세합니다. Vue 3 및 Vite 도구를 활용해 신규 프론트엔드 프로젝트를 격리 생성하고, 하이엔드 미학을 구현하기 위해 테일윈드 CSS의 슬레이트 다크 모드(`bg-slate-900`) 테마 환경을 세팅합니다. 1차 검증(용량 10MB 이하, PNG/JPEG/PDF 포맷)을 프론트엔드 단에서 엄격히 차단 처리하고, MVP 규격(최대 1개 업로드 및 덮어쓰기)을 충족하며 모바일 PWA 환경의 카메라 직촬영을 선제 지원하는 아름다운 영수증 업로드 드롭존(Dropzone) 레이아웃 컴포넌트의 퍼블리싱을 안전하게 수행합니다.

## Technical Context

**Language/Version**: JavaScript (ES6+), Node.js LTS, Vue 3 (Composition API)

**Primary Dependencies**: Vue 3, Vite, Tailwind CSS, PostCSS, Autoprefixer, Lucide Icons (`lucide-vue-next`)

**Storage**: Browser memory reactive state (UUIDv7, blob: Object URL)

**Testing**: 브라우저 로컬 디버깅 및 콘솔 진단 검증, 모바일 뷰포트 시뮬레이션

**Target Platform**: Desktop and Mobile Responsive Viewports (375px ~ 1920px), PWA standalone 호환 환경

**Project Type**: Web Application (Single Page Vue 3 SPA)

**Performance Goals**: 파일 투하 즉시 0.5초 이내 이미지 썸네일 렌더링 (SC-002)

**Constraints**: 최대 10MB 파일 크기 제한, 단일 파일 업로드(초과 시 기존 Object URL 명시적 해제 후 덮어쓰기), 슬레이트 다크 모드 기본 테마 강제

**Scale/Scope**: 1 screen (Receipt Upload Dashboard page layout)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

* **제V조 (Vision-First PWA & HTTPS 보안 환경 강제)**:
  - 검증: 모바일 PWA 접속 시 네이티브 카메라 셔터를 최우선 연동하도록 `input` 엘리먼트에 `accept="image/png, image/jpeg, application/pdf" capture="environment"` 속성을 명시적으로 설계 및 반영함. -> **PASS (준수 완료)**
  - 검증: HTML5 Canvas 기반 가로 최대 1000px 1차 압축 파이프라인과 통합이 즉시 가능한 업로드 파일 이벤트 모델 설계. -> **PASS (준수 완료)**
* **제VI조 (크로스 플랫폼 대칭 툴링 및 문서 동기화 수호)**:
  - 검증: 로컬 실행 환경 기동을 돕는 빌드 및 린트 가이드는 Windows/macOS 개발 장비 모두에 멱등성을 지니는 `npm run dev` 표준 CLI 인터페이스를 채택함. -> **PASS (준수 완료)**
* **제VII조 (선언적 의존성 및 패키지 격리 수호)**:
  - 검증: 신규 구축되는 프론트엔드 모듈의 모든 의존 라이브러리는 `package.json` 선언적 파일에 온전히 명세하고 락 파일을 통해 일관성 있게 관리함. -> **PASS (준수 완료)**
* **제VIII조 (하이브리드 테스트)**:
  - 검증: 프론트엔드 1차 퍼블리싱 단계로 백엔드 테스트 결합과 무관하여 패스함. -> **PASS (준수 완료)**

## Project Structure

### Documentation (this feature)

```text
specs/007-frontend-dropzone-layout/
├── spec.md              # 기획 사양서 (Specify 단계 완료)
├── plan.md              # 본 구현 계획서 (Plan 단계 완료)
├── research.md          # 기술 조사 보고서 (Phase 0 완료)
├── data-model.md        # 프론트엔드 데이터 검증 및 상태 라이프사이클 (Phase 1 완료)
├── quickstart.md        # 개발자 초기 셋업 및 로컬 기동 가이드 (Phase 1 완료)
├── checklists/
│   └── requirements.md  # 명세 품질 체크리스트 (검증 합격 완료)
└── contracts/
    └── ui-contracts.md  # 드롭존 컴포넌트 Props, Event, HTML 마크업 규격 (Phase 1 완료)
```

### Source Code (repository root)

이전 백엔드(Django) 환경에 추가하여, 프론트엔드 독립 프로젝트 모듈을 `frontend/` 디렉토리 하위에 신규 격리 생성합니다 (프로젝트 헌법 제VI조 웹 애플리케이션 양대 물리 폴더 구조 준수).

```text
ai-ledger-automation/ (Repository Root)
├── backend/                  # 기존 장고 백엔드 프로젝트
│   ├── pyproject.toml
│   └── ...
├── frontend/                 # 🆕 신규 뷰 3 프론트엔드 프로젝트
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── index.css
│       ├── App.vue
│       └── components/
│           └── Dropzone.vue
└── specs/                    # Spec-Kit 문서 저장소
```

**Structure Decision**: 기존 backend 디렉토리와 대칭을 이루는 단일 모노레포 구조 하의 `frontend` 디렉토리를 신규 생성하여 독립적으로 패키지 잠금을 유지하고 상호 간의 소스 간섭을 최소화하는 Option 2(Web Application) 구조로 의사결정함.

## Complexity Tracking

> **수립된 프로젝트 헌법의 모든 설계 제약 조건 및 게이트 심사를 우수하게 통과하였으므로 기재할 위반 내역이 없습니다.**

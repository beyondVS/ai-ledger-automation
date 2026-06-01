# AI 스마트 가계부 - 프론트엔드 PWA 모듈 (Vue 3 + Vite)

본 디렉토리는 AI 영수증 분석 자동화 서비스의 PWA 프론트엔드 애플리케이션 프로젝트입니다.

---

## 🛠️ 기술 사양 (Tech Stack)

* **프레임워크**: Vue 3 (Composition API, `<script setup>`)
* **빌드 시스템**: Vite v6
* **스타일 엔진**: Tailwind CSS v4 (Slate-950 다크 테마 기본 장착)
* **아이콘 팩**: Lucide Icons (`lucide-vue-next`)
* **테스트 러너**: Vitest + jsdom (TDD 빌트인)

---

## ⚡ 실행 및 빌드 명령어 (Commands)

의존 라이브러리 설치 및 개발 서버 구동은 반드시 `frontend` 폴더 내부에서 기동합니다.

### 1) 의존 라이브러리 설치
```bash
npm install
```

### 2) 로컬 개발 서버 구동 (Hot-Reloading)
```bash
# http://localhost:5173 대역으로 고속 기동
npm run dev
```

### 3) 프로덕션 정적 자산 빌드 및 번들링
```bash
npm run build
```

### 4) TDD 단위 테스트 일회성 실행
```bash
npm run test
# 또는
npx vitest run
```

---

## ⚖️ 최상위 프로젝트 헌법 준수 사항 (Governance Rules)

* **제V조 (Vision-First PWA)**: 모바일 PWA 환경에서 네이티브 후면 카메라를 최우선으로 즉시 가동하도록 파일 인풋 영역에 `accept="image/png, image/jpeg, application/pdf" capture="environment"` 속성을 완벽히 고정 설계 및 수립했습니다.
* **제VI조 (크로스 플랫폼 대칭성)**: Windows 및 macOS 대칭적 멱등성을 지닌 npm CLI 표준 커맨드를 채택하여 고품격 크로스 개발 혜택을 보장합니다.
* **제VII조 (선언적 의존성 수호)**: 모든 프론트엔드 의존 모듈은 `package.json` 선언 파일 및 잠금 정책을 강력히 통제합니다.

# Developer Quickstart Guide: frontend-dropzone-layout

**Created**: 2026-06-02

본 가이드는 `007-frontend-dropzone-layout` 피처 개발자가 프론트엔드 환경을 구축하고 개발 서버 기동 및 컴포넌트 동작 테스트를 실행하기 위한 퀵스타트 문서입니다.

---

## 1. 초기 개발 환경 설치 및 기동 (Setup & Run)

모든 명령은 저장소 루트 아래의 `frontend` 디렉토리 하위에서 작동합니다.

### 1) 의존성 라이브러리 설치
```bash
# frontend 디렉토리로 진입
cd frontend

# 프로젝트에 정의된 npm 의존성 라이브러리 설치
npm install
```

### 2) 개발용 로컬 웹 서버 기동 (Hot-Reloading)
```bash
# Vite 로컬 개발 서버 기동 (기본 포트: http://localhost:5173)
npm run dev
```

### 3) 프로덕션 정적 자산 빌드 및 번들링
```bash
# dist/ 디렉토리에 최적화된 HTML/CSS/JS 빌드 파일 추출
npm run build
```

---

## 2. 핵심 소스코드 구조 및 배치 안내 (Source Layout)

본 피처가 퍼블리싱되는 프론트엔드 소스코드 파일의 구조적 배치 규칙입니다:

```text
frontend/
├── index.html                   # 프론트엔드 메인 엔트리 HTML 파일
├── tailwind.config.js           # Tailwind CSS 테마 구성 파일 (Slate 다크 모드 설정)
├── postcss.config.js            # PostCSS 설정 파일 (Autoprefixer 연동)
├── vite.config.js               # Vite 컴파일러 및 포트 설정 파일
├── package.json                 # npm 의존성 및 스크립트 잠금 파일
└── src/
    ├── main.js                  # Vue 3 애플리케이션 진입점 JS
    ├── index.css                # 테일윈드 디렉티브 수용 CSS 뼈대 파일
    ├── App.vue                  # 메인 페이지 반응형 전체 뼈대 레이아웃
    └── components/
        └── Dropzone.vue         # 영수증 드래그앤드롭 수동 감지 컴포넌트
```

---

## 3. 기계적 검증 및 테스트 가이드 (Validation)

프론트엔드 퍼블리싱 상태 및 1차 기능 동작 무결성을 로컬에서 기계적으로 검증하는 가이드라인입니다.

### 1) CSS 테일윈드 스타일 린트 검토
- 브라우저 개발자 도구(F12)의 콘솔창에 스타일 유실 에러(`404` CSS)가 검출되지 않아야 하며, `slate-900` 배경이 깨짐 없이 화면 전체를 커버해야 합니다.

### 2) 드롭존 이벤트 로깅 검증 (Mocking Test)
- `App.vue`에 아래의 디버그용 콘솔 코드를 임시 배치하여 드롭 및 삭제 이벤트 라이프사이클을 실시간 모니터링합니다:
  ```javascript
  const onFileDetected = (file) => {
    console.log('[DEBUG] 파일 감지 성공:', file.name, file.size, 'bytes');
  };
  const onFileRemoved = () => {
    console.log('[DEBUG] 파일 선택 취소 완료');
  };
  const onValidationError = (error) => {
    console.warn('[DEBUG] 유효성 검사 실패:', error);
  };
  ```

# Implementation Plan: PWA Integration & Mobile Camera Capture

**Branch**: `024-pwa-camera-integration` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/024-pwa-camera-integration/spec.md`

## Summary

본 피처는 Smart Ledger 애플리케이션의 모바일 기기 사용자 경험(UX) 강화를 목적으로 PWA(Progressive Web App) 규격을 이식하고 오프라인 가용성을 확보하며, HTML5 Capture API 및 Canvas 리사이징 모듈을 적용하여 고화질 모바일 기기 카메라로 영수증을 즉시 촬영하고 전송 성능 저하 없이 최적화된 파일 크기로 첨부할 수 있는 전반적인 프론트엔드 클라이언트 인프라를 구축하는 작업입니다.

## Technical Context

**Language/Version**: JavaScript (ES6+), Vue.js 3, Python 3.13

**Primary Dependencies**: Vite 5+, Tailwind CSS, `@vite-pwa/assets-generator` (선택 사항, 아이콘셋용) 및 Vite 기본 빌드 시스템

**Storage**: CacheStorage (Service Worker 캐시 보존), sessionStorage (인증 토큰 브라우저 영속성 관리)

**Testing**: Vue Test Utils & Vitest (프론트엔드 로컬 렌더링 검증), Cypress 또는 Chrome DevTools 원격 모바일 디버깅 검증

**Target Platform**: Mobile Web Browser (Safari 13+ on iOS, Chrome 80+ on Android, Samsung Internet 등)

**Project Type**: Web Application Frontend integration with Backend API Web Service

**Performance Goals**:
- 오프라인 단독 구동 시 홈화면 설치 웹 앱의 초기 정적 자산 로딩 및 UI 완성 렌더링 3초 이내 완료.
- 모바일 카메라 촬영 후 미리보기 노출 및 Canvas 80% 화질 압축(최대 해상도 1920px 스케일링) 연산 2초 이내 완수.

**Constraints**:
- 브라우저 보안 제약 정책상 로컬 localhost 환경 또는 프로덕션 HTTPS SSL 환경에서만 서비스 워커 및 디바이스 카메라 연동 보장.
- 오프라인 상태 시 백엔드 API 전송을 제어하여 즉시 에러 발생을 예방하고 임시 촬영 버퍼에서 온라인 복구 대기를 유지함.

**Scale/Scope**:
- PWA Manifest 설정 추가, 서비스 워커 등록 스크립트 작성.
- iOS Safari 전용 홈화면 설치 유도(A2HS) 수동 툴팁 컴포넌트 1개 제작.
- 모바일 카메라 캡처 전용 `<input type="file" capture="environment">` 제어 로직 구현.
- Canvas 이미지 리사이징 압축 유틸리티 1개 이식.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 헌법 제약 사항 검증
1. **기술 스택 일치성**: 헌법의 프론트엔드 규격인 `Vue.js 3 (Vite + Vue 3) + PWA Manifest & Service Worker Cache (iOS Safari용 A2HS 수동 유도 툴팁 포함) + Tailwind CSS + sessionStorage 기반 Access Token 세션 관리` 요건에 100% 부합하게 설계됨.
2. **iOS Safari A2HS 툴팁**: 헌법에 수동 유도 툴팁이 필수 명시되어 있으므로, iOS UserAgent 식별 및 Standalone 여부 검사에 기초한 동적 툴팁 컴포넌트를 설계에 포함함.
3. **보안/HTTP**: 로컬 개발과 HTTPS 온리 구동 가정을 헌법 규정과 일치시킴.
4. **푸시 알림 범위 유예**: 헌법에 Web Push 및 VAPID v2 허브 규격이 명세되어 있으나, 사용자 요구사항 기획 단계에서 푸시 알림은 이번 스프린트 범위 제외로 최종 합의(Deferred)되었으므로 헌법 게이트 위반이 아닌 계획적 Scope 축소로 판단함.

## Project Structure

### Documentation (this feature)

```text
specs/024-pwa-camera-integration/
├── spec.md              # Feature Specification (작성 완료)
├── plan.md              # This file (지금 작성 중)
├── research.md          # Phase 0 output (기술 조사 및 Rationale)
├── data-model.md        # Phase 1 output (PWA 설정 및 클라이언트 버퍼 정의)
├── quickstart.md        # Phase 1 output (로컬 HTTPS 디버깅 셋업 가이드)
└── contracts/           # Phase 1 output (FormData 이미지 업로드 API 구조)
    └── receipt-upload-payload.md
```

### Source Code (repository root Layout)

```text
backend/
├── src/
│   └── (기존 Django 모델, DRF 뷰, API 엔드포인트 - 이번 피처에서 미수정 또는 연동 확인)
└── tests/

frontend/
├── public/
│   ├── manifest.webmanifest # PWA 매니페스트 파일 배치
│   └── robots.txt
├── src/
│   ├── assets/              # 아이콘 및 로고 자산 배치 (192, 512px)
│   ├── components/
│   │   ├── NavBar.vue       # 공통 내비바
│   │   └── iOSInstallTooltip.vue # iOS용 A2HS 수동 유도 툴팁
│   ├── utils/
│   │   └── imageCompressor.js # Canvas 이미지 압축 유틸리티
│   ├── registerServiceWorker.js # SW 등록 로직
│   ├── App.vue              # PWA 업데이트 감지 UI 바인딩
│   └── (기존 대시보드 및 가계부 작성 뷰 카메라 연동)
```

**Structure Decision**: 기존 `frontend/` 및 `backend/` 폴더를 그대로 사용하여, Vite 빌드 환경 아래 PWA 자산을 등록하고 프론트엔드 클라이언트 중심의 소스 코드를 생성합니다.

## Complexity Tracking

*(헌법 게이트 위반 사항이 없으므로 빈 상태로 유지합니다)*

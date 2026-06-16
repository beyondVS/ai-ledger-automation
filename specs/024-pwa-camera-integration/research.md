# Technical Research: PWA and Camera Capture Integration

**Feature Branch**: `024-pwa-camera-integration`

## 1. PWA 설정 및 서비스 워커 관리 기술 분석

### [연구 대상] Vite 환경에서의 PWA Manifest 및 Service Worker 빌드 통합
PWA의 캐싱 정책과 앱 매니페스트를 Vite 빌드 환경에 이식하기 위해 다음 두 가지 방안을 검토했습니다.

- **결정사항**: Vite 플러그인 빌트인 방식 (`vite-plugin-pwa`) 대신, 프로젝트 환경의 투명성과 통제성을 극대화하기 위해 **표준 정적 파일 서빙(`manifest.webmanifest`)과 커스텀 서비스 워커(`sw.js`) 수동 등록 방식**을 적용합니다.
- **타당성**: 플러그인을 도입하면 설정이 복잡해지고 자동 생성되는 난해한 웹팩/롤업 코드로 인해 디버깅이 어려워집니다. 반면, 공통 정적 자산이 비교적 소수(Vite 빌드 자산, 폰트, 아이콘)이므로 수동으로 작성된 서비스 워커(`sw.js`) 내에서 `Cache Storage API`를 활용하는 "Stale-While-Revalidate" 전략을 정밀하게 제어하는 것이 유지보수성 및 트러블슈팅에 크게 유리합니다.
- **고려된 대안**:
  - `vite-plugin-pwa` 사용: 설정 파일 구성만으로 Manifest 및 Service Worker가 자동 빌드되지만, Workbox의 복잡한 추상화 레이어로 인해 빌드 자산 캐싱 오류 발생 시 모바일 사후 추적이 난해함.

---

## 2. 모바일 카메라 연동 API 기술 분석

### [연구 대상] HTML5 Capture API vs WebRTC MediaDevices API (getUserMedia)
모바일 기기 카메라 하드웨어에 접근하여 사진을 캡처하는 웹 API들의 구현 편의성과 안정성을 대조 평가했습니다.

- **결정사항**: **HTML5 Capture API** (`<input type="file" accept="image/*" capture="environment">`) 적용.
- **타당성**: Capture API는 브라우저 내부에서 모바일 OS(Android, iOS)의 네이티브 카메라 앱을 직접 기동합니다. 이는 다음과 같은 극명한 장점이 있습니다:
  1. 기기 제조사별 네이티브 카메라 UI, 초점 정렬, 화질 보정 기능을 100% 그대로 활용할 수 있음.
  2. 브라우저 내부 웹RTC 비디오 렌더링에 따른 성능 부하가 없음.
  3. iOS Safari와 Android Chrome 모두에서 HTML 표준으로 균일하게 작동하므로 크로스 브라우저 정합성이 절대적으로 보증됨.
- **고려된 대안**:
  - `navigator.mediaDevices.getUserMedia`를 활용한 실시간 카메라 캔버스 스트리밍: 브라우저 내부 모달 영역에 카메라 스트림을 비디오 객체로 렌더링하고 스냅샷을 캡처하는 방식. 이는 화면 레이아웃 깨짐, 브라우저 백그라운드 전환 시 카메라 세션 락(Lock) 해제 처리 등 구현의 엣지 케이스가 매우 많고 권한 허용 실패 대응이 까다로워 기각함.

---

## 3. 클라이언트 사이드 이미지 압축 분석

### [연구 대상] Canvas API 기반 크기 스케일링 및 JPEG 인코딩 압축
모바일 카메라로 영수증을 촬영하면 원본 해상도(예: 4000x3000px, 8MB~12MB)가 지나치게 커서 서버 전송 및 OCR/LLM 인식 부하가 발생합니다.

- **결정사항**: **HTML5 Canvas API** 기반의 2단계 클라이언트 이미지 전처리 구현.
  1. 이미지 로드 후 가로/세로 중 긴 축의 크기가 `1920px`을 초과할 경우 비율을 유지하며 스케일 다운 리사이징.
  2. `canvas.toBlob(..., 'image/jpeg', 0.8)`을 통해 JPEG 포맷 및 화질 80%로 압축하여 1.5MB 이하로 경량화.
- **타당성**: 모바일 브라우저의 샌드박스 메모리 한계 내에서 외부 라이브러리 없이 빠르게 실행 가능한 네이티브 API입니다. 1920px 크기와 80% 화질은 OCR/LLM이 영수증 텍스트를 고정밀로 읽어낼 수 있는 최적의 해상도/품질 한계선이며, 동시에 전송 네트워크 부하를 80% 이상 혁신적으로 줄여줍니다.
- **고려된 대안**:
  - 외부 라이브러리(browser-image-compression 등) 도입: NPM 의존성을 추가해야 하며 로딩 속도 저하 우려가 있고 내부적으로 결국 Canvas API를 래핑한 도구이므로 불필요한 빌드 크기를 줄이기 위해 순수 자바스크립트 Canvas 유틸리티로 내재화함.

---

## 4. iOS Safari A2HS(Add to Home Screen) 대응 분석

- **결정사항**: **UserAgent 탐색 및 커스텀 툴팁 안내 팝업** 적용.
- **타당성**: iOS Safari는 PWA 규격을 지원하나 Android Chrome처럼 브라우저 주도로 "설치 안내 팝업(beforeinstallprompt)"을 발생시키지 않습니다. 오직 사용자가 하단 공유 버튼을 눌러 수동으로 홈 화면에 추가해야 합니다.
  따라서 `navigator.userAgent`로 iOS 환경을 감지하고 `window.navigator.standalone`이 `false`인 비설치 브라우저 구동 시에만, 네비게이션 영역 근처에 "공유 아이콘을 탭한 후 '홈 화면에 추가'를 누르십시오"라는 안내 유도 툴팁을 시각적으로 표출해야 합니다.

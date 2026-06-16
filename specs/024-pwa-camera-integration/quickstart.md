# Local Development & Debugging Quickstart: PWA & Camera

**Feature Branch**: `024-pwa-camera-integration`

브라우저의 보안 정책상 **PWA 서비스 워커 등록** 및 **카메라 접근 API(HTML5 Capture)**는 오직 **localhost 개발 세션**이거나 유효한 **HTTPS 암호화 세션** 환경에서만 권한 팝업을 승인합니다. 

이 문서에서는 로컬 개발 환경에서 모바일 실물 기기를 연결하여 PWA 및 카메라 기능을 고속 디버깅하기 위한 셋업 가이드를 설명합니다.

---

## 1. Vite 로컬 HTTPS 개발 서버 구성

로컬 IP(예: `192.168.x.x`)로 모바일 기기가 접속하여 테스트할 수 있도록 로컬 Vite 개발 서버에 임시 SSL 인증서를 적용합니다.

### 1.1 SSL 개발용 플러그인 추가 (Vite)
`frontend/vite.config.js` 파일에 `@vitejs/plugin-basic-ssl` 플러그인을 임시 연결하여 로컬 서버를 https 프로토콜로 기동합니다.

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [
    vue(),
    basicSsl() // 로컬 HTTPS 강제 활성화
  ],
  server: {
    host: true, // 로컬 IP(0.0.0.0)로 모든 인터페이스 바인딩
    port: 5173,
    https: true // HTTPS 모드 활성화
  }
})
```

---

## 2. 모바일 실기기 원격 디버깅 (Remote Debugging)

서비스 워커의 동작 상황 및 콘솔 로그를 확인하기 위해 PC 크롬/사파리와 모바일 실기기를 연동합니다.

### 2.1 Android 기기 (Chrome DevTools)
1. Android 기기의 **설정 > 개발자 옵션**에서 **USB 디버깅**을 활성화합니다.
2. 기기를 PC와 USB 케이블로 연결합니다.
3. PC 크롬 브라우저 주소창에 `chrome://inspect/#devices`를 입력합니다.
4. 기기가 인식되면, 모바일 브라우저에 표시된 `https://192.168.x.x:5173` 탭 하단의 **Inspect** 버튼을 눌러 개발자 도구를 실행합니다.

### 2.2 iOS 기기 (Safari Web Inspector)
1. iPhone 기기의 **설정 > Safari > 고급**에서 **웹 검사기(Web Inspector)**를 활성화합니다.
2. 기기를 Mac/PC(Mac 환경 권장)와 USB 케이블로 연결합니다.
3. Mac Safari 브라우저의 메뉴에서 **개발자용 > [연결된 기기 이름] > [디버깅할 페이지 주소]**를 선택해 검사기 창을 띄웁니다.

---

## 3. 오프라인 시뮬레이션 및 테스트

1. **서비스 워커 캐싱 확인**: 
   - 앱에 접속한 후, 크롬 개발자 도구의 **Application > Service Workers** 탭에서 SW가 정상 작동(Activated and running) 중인지 확인합니다.
2. **오프라인 구동 테스트**:
   - PC DevTools의 **Network** 탭 또는 **Application > Service Workers** 탭 상단의 **Offline** 체크박스를 켭니다.
   - 브라우저를 새로고침(`F5`)했을 때 화면 프레임(NavBar, 대시보드 뼈대)이 로드되고, 상단 알림 영역에 "오프라인 상태입니다" 피드백 배너가 정상 출력되는지 검증합니다.

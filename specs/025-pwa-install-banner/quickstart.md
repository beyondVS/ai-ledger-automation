# Quickstart Guide: Testing PWA Install Banner & iOS A2HS Tooltip

본 가이드는 개발자 및 테스터가 로컬 개발 환경에서 PWA 설치 배너 및 iOS Safari 툴팁 기능을 원활하게 검증하고 디버깅할 수 있는 E2E 테스트 방법을 제공합니다.

## 1. 개발 서버 구동 및 접속

1. 프론트엔드 Vite 서버를 구동합니다:
   ```bash
   npm run dev
   ```
2. 웹 브라우저를 열고 `http://localhost:5173`으로 접속합니다.
   *주의: `localhost` 도메인은 브라우저가 안전한 보안 컨텍스트(Secure Context)로 신뢰하므로, 로컬 개발 시에는 HTTPS SSL 인증서 세팅 없이도 PWA 서비스 워커 및 A2HS 테스트가 정상 동작합니다.*

---

## 2. Android / Chrome 설치 배너 디버깅 E2E 검증

### A. 설치 조건 강제 충족
브라우저의 PWA 진단 결과 설치성(Installability)이 충족되는 순간 `beforeinstallprompt` 이벤트가 발생합니다.
1. Chrome DevTools(F12)의 **Application** 탭으로 이동합니다.
2. 좌측 메뉴의 **Manifest**를 클릭하여 매니페스트 속성이 정상적으로 해석되고 있는지 검증합니다.
3. 서비스 워커 등록을 확인하려면 **Service Workers** 탭으로 이동하여 현재 구동 상태가 `Active and running`인지 확인합니다.
4. **Manifest** 화면 우측 상단의 `Add to home screen` 링크를 클릭하여 설치를 강제로 모의 작동시킬 수 있습니다.

### B. 커스텀 배너 동작 E2E
1. 브라우저에서 사이트를 새로고침합니다.
2. 3초간 기다리면 화면 하단에 커스텀 설치 유도 배너가 아래에서 위로 나타납니다.
3. 배너 내 "설치" 버튼을 클릭합니다.
4. 크롬 브라우저 기본 설치 팝업("앱을 설치하시겠습니까?")이 정상 노출되는지 확인합니다.
5. "설치"를 승인하면 PWA 독립 모드로 전환되며, 배너는 UI 상에서 즉시 사라집니다.

---

## 3. iOS Safari 수동 가이드 툴팁 디버깅 검증

iOS 기기가 없더라도 데스크톱 PC의 개발자 도구를 통해 iOS Safari 환경을 모의하여 툴팁 가이드의 레이아웃과 동작을 검사할 수 있습니다.

### A. Chrome DevTools에서 iOS 모바일 에뮬레이션
1. Chrome DevTools(F12)를 열고 기기 툴바 아이콘(Device Mode, `Ctrl+Shift+M`)을 클릭하여 모바일 뷰로 전환합니다.
2. 기기 목록 드롭다운에서 **iPhone 12/13/14 Pro** 등을 선택합니다.
3. UserAgent를 iOS Safari로 모의하기 위해, DevTools 우측 상단 점 3개 메뉴 ➔ **More tools** ➔ **Network conditions**로 이동합니다.
4. **User agent** 항목에서 "Use browser default" 체크를 해제하고, **Safari - iPhone**을 선택합니다.
5. 페이지를 새로고침한 뒤 3초를 대기합니다.
6. 화면 최하단에 아래 방향 꼬리를 가진 iOS 수동 가이드 말풍선 툴팁이 렌더링되는지 확인합니다.

---

## 4. LocalStorage 쿨다운(7일 차단) 상태 조작법

1. 배너 또는 툴팁의 "닫기"를 클릭하여 UI를 완전히 숨깁니다.
2. 사이트를 다시 새로고침하여 3초가 지나도 배너가 노출되지 않음을 확인합니다 (쿨다운 작동 검증).
3. **디버깅을 위해 재노출 상태로 강제 복구하는 방법**:
   - DevTools **Console** 탭을 열고 아래 명령어로 로컬 스토리지를 초기화합니다:
     ```javascript
     localStorage.removeItem('pwa-install-banner-state');
     ```
   - 또는 쿨다운 만료 시점을 테스트하기 위해 시간을 과거(8일 전)로 조작할 수 있습니다:
     ```javascript
     const pastDate = new Date();
     pastDate.setDate(pastDate.getDate() - 8);
     localStorage.setItem('pwa-install-banner-state', JSON.stringify({
       dismissedAt: pastDate.toISOString(),
       platform: 'android',
       standalone: false
     }));
     ```
   - 설정 완료 후 페이지를 새로고침하면 3초 후 배너가 정상적으로 다시 노출됩니다.

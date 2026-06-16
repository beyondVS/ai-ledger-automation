# Client-Side Data & Configuration Model: PWA & Camera Buffer

**Feature Branch**: `024-pwa-camera-integration`

## 1. PWA Web App Manifest Specification (`manifest.webmanifest`)

PWA의 모바일 OS 설치성(A2HS) 확보를 위해 `frontend/public/manifest.webmanifest` 파일에 정의할 구조 모델입니다.

```json
{
  "name": "Smart Ledger 자동 가계부",
  "short_name": "SmartLedger",
  "description": "영수증 촬영 자동 분석 및 가계부 자산 제어 서비스",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#020617",
  "theme_color": "#020617",
  "orientation": "portrait-primary",
  "categories": ["finance", "productivity"],
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icons/icon-192x192-maskable.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    },
    {
      "src": "/icons/icon-512x512-maskable.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}
```

---

## 2. Service Worker Caching Model (`sw.js`)

정적 자산 캐싱을 담당할 서비스 워커의 데이터 라이프사이클 및 오프라인 범위 스펙입니다.

### 2.1 캐시 스토어 (Cache Storage) 명세
- **정적 캐시 이름**: `smart-ledger-static-v1`
- **캐싱 대상 자산 목록 (Static Assets)**:
  - `index.html` (엔트리 포인트)
  - `/assets/*.js`, `/assets/*.css` (Vite 빌드 번들 파일)
  - `/icons/*.png` (앱 아이콘셋)
  - `/favicon.ico`
  - Google Fonts 등 사용되는 웹 폰트 정적 URL

### 2.2 라우팅 캐시 전략 (Routing Cache Strategies)
- **정적 자산 (Static Assets)**: **Stale-While-Revalidate** 전략
  - 캐시 스토어에 파일이 존재하면 즉시 화면에 서빙하여 렌더링 속도를 극대화합니다.
  - 동시에 백그라운드로 네트워크 요청을 보내 서버 상에 변경된 최신 파일이 있는지 대조하고, 변경 시 로컬 캐시를 갱신합니다.
- **API 및 실시간 데이터 (`/api/*`)**: **Network Only** 전략
  - 가계부 내역 조회, 추가 등 비즈니스 금융 데이터는 정합성이 최우선이므로 캐싱하지 않고 무조건 네트워크를 탑니다.
  - 네트워크 단절 시(오프라인) API 요청은 실패하며, 프론트엔드가 이를 감지하여 사용자에게 알맞은 오류 토스트 피드백을 제공합니다.

---

## 3. 영수증 캡처 버퍼 엔티티 (`ReceiptBuffer`)

영수증 촬영 완료 후 클라이언트 메모리에 보존되는 임시 데이터 구조입니다. 가계부 최종 등록이 완료되거나 업로드가 취소되면 버퍼 메모리에서 해제됩니다.

| 속성명 (Attribute) | 데이터 타입 | 설명 |
| :--- | :--- | :--- |
| `rawFile` | `File` | Input[type=file]에서 발생한 원본 OS 이미지 파일 객체 |
| `previewUrl` | `String` | `URL.createObjectURL(rawFile)`로 생성된 화면 렌더링용 임시 Blob 주소 |
| `compressedBlob` | `Blob` | Canvas API를 거쳐 용량이 압축된 바이너리 데이터 |
| `compressedSize` | `Number` | 압축된 이미지의 바이트 크기 (성공 지표 비교 및 검증용) |
| `status` | `String` | 버퍼 상태: `idle` (대기), `compressing` (압축 중), `ready` (압축 완 및 전송 대기), `error` (실패) |

---

## 4. 네트워크 상태 모니터러 상태 모델 (`NetworkStatus`)

브라우저의 인터넷 활성 여부를 실시간으로 바인딩하여 프론트엔드 전역에서 참조하는 상태 값입니다.

- `isOnline`: `Boolean` (`navigator.onLine` 바인딩)
- `lastChanged`: `DateTime` (네트워크 상태가 온라인/오프라인으로 변경된 마지막 시점)
- `showToast`: `Boolean` (네트워크 끊김 또는 복구 알림 팝업 노출 플래그)

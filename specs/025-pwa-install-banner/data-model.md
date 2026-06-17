# Data Model: PWA Install Banner State

본 피처는 데이터베이스 서버를 활용하지 않으며, 클라이언트 브라우저의 `LocalStorage`에 상태를 보존하여 기기 수준의 개인 설정을 유지합니다.

## 1. InstallBannerState (로컬 브라우저 상태 엔티티)

사용자 모바일 기기 브라우저의 로컬 스토리지에 JSON 직렬화하여 저장되거나, 애플리케이션의 반응형 메모리 상태(State) 내에서 관리되는 구조입니다.

### 속성 (Attributes)

| 필드명 | 데이터 타입 | 설명 | 유효성 검사 규칙 |
| :--- | :--- | :--- | :--- |
| `dismissedAt` | `String` (ISO 8601) \| `null` | 사용자가 설치 안내 배너/툴팁의 "닫기"를 누른 마지막 일시입니다. | 유효한 날짜 규격이어야 하며, 닫은 적이 없다면 `null`입니다. |
| `platform` | `String` | 사용자가 접속한 단말 기기 환경 정보입니다. | `android`, `ios_safari`, `unknown` 중 하나의 문자열이어야 합니다. |
| `standalone` | `Boolean` | 현재 앱이 홈 화면 독립 바로가기 모드로 실행 중인지 여부입니다. | Boolean 데이터여야 합니다. |

---

## 2. 상태 전이 모델 (State Transition Model)

설치 배너 및 가이드 UI 상태는 사용자의 상호작용 및 시간 경과에 따라 다음과 같이 순환 전이됩니다.

```mermaid
state-chart
[*] --> Initializing : 페이지 로드 (onMounted)
Initializing --> DetectPlatform : 플랫폼 감지 및 Standalone 검사
DetectPlatform --> StandaloneActive : standalone === true (독립 실행 모드)
DetectPlatform --> CheckCooldown : standalone === false (웹 브라우저 모드)

StandaloneActive --> [*] : 배너/툴팁 미노출 (완전 숨김)

CheckCooldown --> CooldownActive : 현재시간 - dismissedAt < 7일
CheckCooldown --> TriggerTimer : 현재시간 - dismissedAt >= 7일 또는 null

CooldownActive --> [*] : 배너/툴팁 미노출 (차단 활성화)

TriggerTimer --> Visible : 3초 지연 시간 경과 (Timer Fired)

Visible --> InstallInitiated : 사용자가 "설치하기" 클릭 (Android)
Visible --> Dismissed : 사용자가 "닫기" 클릭
Visible --> [*] : 사용자가 반응 없이 서비스 이탈

InstallInitiated --> Installed : 브라우저 기본 설치 승인
InstallInitiated --> Visible : 브라우저 기본 설치 거부 (재노출 상태 유지)

Dismissed --> [*] : LocalStorage에 dismissedAt 기록 및 UI 즉시 숨김
Installed --> StandaloneActive : 독립 모드 진입으로 변경 및 UI 자동 제외
```

---

## 3. 데이터 저장 형식 (Serialization)

LocalStorage에 저장되는 원시 데이터 포맷 예시:

- **Key**: `pwa-install-banner-state`
- **Value** (JSON String):
  ```json
  {
    "dismissedAt": "2026-06-17T11:40:00.000Z",
    "platform": "ios_safari",
    "standalone": false
  }
  ```

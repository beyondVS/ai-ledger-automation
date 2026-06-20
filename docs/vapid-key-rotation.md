# VAPID Key Rotation & Environment Configurations Guide

본 문서는 **ai-ledger-automation** 서비스의 웹 푸시 알림 인프라에 필요한 VAPID(Voluntary Application Server Identification) 키 쌍을 안전하게 갱신(Rotation)하고 관리하는 프로세스를 기술합니다.

---

## 🔒 1. VAPID 키 쌍 표준 규격
W3C Web Push 및 RFC 8292 표준 규격을 준수하기 위해 VAPID 키는 **ECDSA NIST P-256 (secp256r1)** 곡선 기반의 키 쌍이어야 합니다.
- **공개키 (Public Key)**: 비압축 (Uncompressed) 바이트 배열 (총 65바이트: 접두사 `0x04` + 32바이트 X좌표 + 32바이트 Y좌표)을 **base64url (패딩 생략)** 형식으로 인코딩한 문자열.
- **개인키 (Private Key)**: 32바이트 개인키 원시 값을 **base64url (패딩 생략)** 형식으로 인코딩한 문자열.

---

## 🛠️ 2. 신규 VAPID 키 쌍 생성 방법 (CLI & Python)

### 방법 A: `pywebpush` CLI 활용 (가장 간단함)
로컬 가상환경 내에 설치된 `pywebpush` 라이브러리의 빌트인 도구를 활용하여 생성할 수 있습니다.
```bash
# 가상환경 내에서 실행
uv run pywebpush --generate-vapid-keys
```
**출력 예시:**
```text
VAPID Private Key: MHgxM...[base64url]...
VAPID Public Key: MHgwN...[base64url]...
```

### 방법 B: Python 스크립트 직접 실행 (NIST P-256 검증 보장)
`py-vapid` 라이브러리를 이용하여 규격에 완벽히 들어맞는 ECDSA 키를 추출하여 직렬화하는 방법입니다.
```python
# scripts/generate_vapid_keys.py (예시)
from py_vapid import Vapid

vapid = Vapid()
# NIST P-256 키 쌍 생성 및 원시 바이트 무손실 인코딩
private_key_b64url, public_key_b64url = vapid.generate_keys()

print(f"VAPID_PRIVATE_KEY={private_key_b64url}")
print(f"VAPID_PUBLIC_KEY={public_key_b64url}")
```

---

## ⚙️ 3. 환경 변수 설정 반영 (.env & .env.docker)
새로 생성한 VAPID 키를 로컬 및 도커 가동 환경 변수 파일에 반영합니다.

### 3.1 로컬 테스트 환경 (`backend/.env` 및 `backend/.env.docker`)
```ini
# --- VAPID Push Notification Configuration ---
VAPID_PRIVATE_KEY=your_generated_private_key_base64url
VAPID_PUBLIC_KEY=your_generated_public_key_base64url
VAPID_CLAIMS_EMAIL=admin@ai-ledger-automation.com
```

### 3.2 로테이션 시 주의 사항 (Fail-Safe)
1. **클라이언트 동기화**: VAPID 공개키가 변경되면, PWA 프론트엔드가 서비스 워커를 재등록하고 브라우저 푸시 서버에 신규 키로 재구독(`subscribe()`) 신청을 넣어야 합니다.
2. **이중 키 과도기 지원 (Grace Period)**:
   - 프로덕션 배포 시에는 구형 키로 구독된 단말들에 대한 전송 실패를 방지하기 위해, 한 주기 동안 구형 VAPID 키 서명 전송도 점진적 폴백이 되도록 임시 허용하거나 무중단 가동 윈도우 내에 모든 단말의 구독 갱신을 순차 유도하는 것이 권장됩니다.
3. **410 Gone 자동 자가 치유**:
   - 키 로테이션 이후 브라우저 푸시 서버(APNs/FCM)가 만료(410 Gone) 응답을 주면, Celery 워커가 해당 단말의 구독 정보(`UserPushSubscription.is_active`)를 자동으로 `False` 처리(자가 치유)하여 시스템 리소스 유실을 완벽히 차단합니다.

---

## 🔍 4. 동작 및 정합성 무결성 검증
로테이션이 정상적으로 되었는지 백엔드 테스트를 수행하여 입증할 수 있습니다.
```bash
# 백엔드 테스트 실행
uv run pytest tests/apps/notifications/
```
모든 VAPID 전송 모의 테스트 및 페이로드 상한 검증 테스트가 `Passed` 상태를 유지해야 로테이션이 완료됩니다.

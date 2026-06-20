# Implementation Plan: VAPID V2 웹 푸시 발송 큐 파이프라인

**Branch**: `026-vapid-push-queue` | **Date**: 2026-06-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-vapid-push-queue/spec.md`

---

## Summary

VAPID V2 표준 규격(RFC 8292, RFC 8291)을 준수하는 웹 푸시 알림 시스템을 Django 백엔드 + Vue.js PWA 스택 위에 구축한다.

핵심 설계: 기존 Celery/Redis 인프라 위에 `notifications` 전용 큐와 독립 워커 컨테이너를 추가하고, `apps/notifications/` 신규 Django 앱에 NotificationTask/NotificationLog 모델을 구축한다. 발송 모듈은 `pywebpush`로 VAPID 암호화+서명을 수행하며, Chrome/Firefox(FCM), Safari iOS PWA(Apple Web Push) 모두 VAPID 표준으로 통일 처리한다. 이벤트 트리거는 영수증 처리 완료 + 월별 예산 80% 초과 2종으로 시작하며, 멱등성은 Redis 락(5분 TTL) + DB 60초 윈도우 이중 방어로 보장한다.

---

## Technical Context

**Language/Version**: Python 3.13 (Django 6.0 / DRF) + Vue.js 3 (Vite PWA)

**Primary Dependencies**:
- 신규: `pywebpush>=2.0`, `py-vapid>=1.9`, `httpx[http2]>=0.27`
- 기존 활용: `celery>=5.3.6`, `redis>=5.0.1`, `google-auth` (google-genai 체인)

**Storage**: PostgreSQL v18+ — 기존 DB 위에 `notification_tasks`, `notification_logs` 테이블 추가

**Testing**: pytest + Django TestCase (헌법 VIII조 하이브리드 전략 준수)

**Target Platform**: Linux 서버 (Docker Compose) + PWA Chrome(Android)/Safari(iOS 16.4+)

**Project Type**: Web Service (Django REST API + Vue.js SPA)

**Performance Goals**:
- 이벤트 발생 → 기기 알림 도달: ≤ 30초 (SC-001)
- 큐 적재 지연: ≤ 50ms (SC-005)
- 발송 성공률: ≥ 99% (SC-002)

**Constraints**:
- 알림 페이로드: ≤ 4,096 bytes
- HTTPS 강제 (프로덕션) / localhost HTTP 허용 (개발)

**Scale/Scope**: 기존 사용자 기반, 다중 기기(평균 2~3기기/사용자) 병렬 발송

---

## Constitution Check

| 헌법 조항 | 적용 내용 | 판정 |
|----------|----------|------|
| I. 데이터 무결성 | NotificationTask/Log 생성 시 `transaction.atomic()` 적용 | ✅ PASS |
| II. 비동기 큐 격리 | 알림 발송 = `notifications` 전용 Celery 큐 + 독립 컨테이너. notification_worker concurrency=2로 풀 상한 준수 | ✅ PASS |
| III. 3단계 하이브리드 | 영수증 파싱 완료 시 알림 트리거만 추가, 파이프라인 자체 무변경 | ✅ PASS |
| V. VAPID + 서비스 워커 | RFC 8292/8291 준수. sw.js에 `push`/`notificationclick` 핸들러 추가. Chrome-extension 스킴 우회 방어 코드 유지 | ✅ PASS |
| VI. 크로스플랫폼 툴링 | notification_worker 기동 명령 PS1/SH 양쪽 스크립트 업데이트 | ✅ PASS |
| VII. 선언적 의존성 | pywebpush, py-vapid, httpx[http2] → pyproject.toml 추가 후 `uv sync` | ✅ PASS |
| VIII. 하이브리드 테스트 | DB 결합=Django TestCase, 순수 로직=unittest.TestCase | ✅ PASS |
| IX. ruff + pre-commit | 신규 코드 전체 ruff check/format 통과 필수 | ✅ PASS |

**게이트 판정**: 헌법 위반 없음 ✅

---

## Project Structure

### Documentation (this feature)

```text
specs/026-vapid-push-queue/
├── plan.md              # This file (/speckit-plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api-contracts.md # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── apps/
│   │   ├── accounts/
│   │   │   ├── models.py          # UserPushSubscription: is_active, device_hint 필드 추가
│   │   │   ├── migrations/
│   │   │   │   └── 00XX_add_push_subscription_fields.py
│   │   │   └── (기존 파일 유지)
│   │   │
│   │   ├── ledgers/
│   │   │   ├── tasks.py           # extract_receipt_task 완료 후 알림 트리거 추가
│   │   │   ├── views.py           # 월별 예산 임계 초과 체크 후 알림 트리거 추가
│   │   │   └── (기존 파일 유지)
│   │   │
│   │   └── notifications/         # 신규 Django 앱
│   │       ├── __init__.py
│   │       ├── admin.py           # NotificationTask, NotificationLog 어드민 등록
│   │       ├── apps.py
│   │       ├── migrations/
│   │       │   └── 0001_initial.py
│   │       ├── models.py          # NotificationTask, NotificationLog
│   │       ├── serializers.py     # API 직렬화
│   │       ├── services.py        # 큐 적재 서비스 (enqueue_* 함수)
│   │       ├── sender.py          # VAPID/FCM/Apple 발송 모듈 (pywebpush 래퍼)
│   │       ├── tasks.py           # Celery 태스크 (send, dispatch, cleanup)
│   │       ├── urls.py
│   │       └── views.py
│   │
│   └── config/
│       ├── settings/
│       │   └── base.py            # CELERY_TASK_ROUTES, CELERY_BEAT_SCHEDULE, VAPID 설정 추가
│       └── urls.py                # /api/v1/notifications/ 라우팅 추가
│
├── .env                           # VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, FCM 자격증명 추가
├── .env.example                   # 신규 환경 변수 템플릿 추가
└── pyproject.toml                 # pywebpush, py-vapid, httpx[http2] 추가

frontend/
├── public/
│   └── sw.js                      # push, notificationclick 이벤트 핸들러 추가
├── src/
│   ├── pages/
│   │   └── Settings.vue           # 알림 On/Off 토글 섹션 추가
│   └── services/
│       └── notificationService.js # 신규: 구독 등록/해제 API 연동

docker-compose.yml                 # notification_worker 서비스 추가

scripts/
├── start-notification-worker.ps1  # 신규: 알림 워커 독립 기동 스크립트 (Windows)
└── start-notification-worker.sh   # 신규: 알림 워커 독립 기동 스크립트 (Unix)
```

**Structure Decision**: 기존 Backend + Frontend 모노레포 구조를 유지하며, `apps/notifications/` 신규 앱만 추가. 프론트엔드는 기존 파일 수정 방식으로 최소 변경.

---

## Complexity Tracking

> 헌법 위반 없음 — 이 섹션에 기록할 위반 사항 없음.

---

## 설계 노트 (Design Notes)

### 채널 라우팅 전략

```
브라우저 구독 endpoint URL
    │
    ├── "fcm.googleapis.com" → FCM 채널 (google-auth OAuth2 + FCM v1 REST)
    │                           └── pywebpush로 VAPID 암호화 후 전송
    │
    ├── "web.push.apple.com" → Apple Web Push 채널
    │                           └── pywebpush로 VAPID 암호화 후 전송 (동일!)
    │
    └── 기타              → Generic VAPID 채널
                            └── pywebpush로 VAPID 암호화 후 전송 (동일!)
```

모든 채널이 `pywebpush`로 통일 처리 가능하며, 채널 구분은 로깅 및 감사 목적.

### 멱등성 이중 방어

```
이벤트 발생
    │
    ▼
① Redis 락 체크 (5분 TTL)
    ├── 락 획득 실패 → 중복 발송 차단 (즉시 종료)
    └── 락 획득 성공
            │
            ▼
        Celery 태스크 큐 적재
            │
            ▼
② DB 60초 윈도우 체크 (NotificationLog)
    ├── 60초 내 동일 이벤트 존재 → 스킵
    └── 신규 이벤트 → 발송 진행
```

### 커넥션 풀 할당

로컬 Docker 개발 환경 및 가동 사양 편의성을 위해 DB 커넥션 풀에 강제적인 개수 제약은 없으며, 서비스별 안정적인 트랜잭션과 비동기 작업을 처리할 수 있는 합리적인 기본값으로 가동합니다.
* `api_server`: max_size=5 (기본)
* `async_worker`: max_size=3 (기본)
* `notification_worker`: max_size=2 (기본)


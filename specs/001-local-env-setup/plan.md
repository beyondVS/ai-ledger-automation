# Implementation Plan: 로컬 통합 개발 환경 및 PostgreSQL v18+ 컨테이너 셋업

**Branch**: `001-local-env-setup` | **Date**: 2026-05-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-local-env-setup/spec.md`

## Summary

본 1일차 계획(001-local-env-setup)의 목표는 로컬 PC 개발 환경에 수동으로 DB를 개별 설치하지 않고, 격리된 가상화 환경에서 PostgreSQL v18+ 독립 데이터베이스 서버 인스턴스를 도커로 원클릭 기동하는 통합 환경을 구축하는 것입니다.
로컬 환경의 OS(Windows/WSL 2) 권한 충돌 에러를 원천 차단하고 50ms 이내 초고속 쿼리 성능(SC-002)을 달성하기 위해 **도커 네임드 볼륨(Named Volume) `postgres_data`**를 도입하는 기술적 의사결정을 적용하였습니다.

## Technical Context

**Language/Version**: `Docker / Docker Compose` & `PostgreSQL v18.x` (Alpine Linux 기반)

**Primary Dependencies**: `postgres:18-alpine` (경량 격리 컨테이너 배포판)

**Storage**: `PostgreSQL v18+` (Docker Named Volume: `postgres_data` 영속 볼륨 마운트)

**Testing**: `Docker Healthcheck` & `psql`을 통한 환경 변수 쿼리 검증 (`client_encoding=UTF8`, `timezone=Asia/Seoul`)

**Target Platform**: `Docker Desktop (WSL 2 on Windows 10/11)`

**Project Type**: `infrastructure` (로컬 인프라 격리 가동)

**Performance Goals**: 데이터베이스 서버 컨테이너 초기 부팅 및 네트워크 리스닝 개시까지 15초 이내, 로컬 쿼리 응답 50ms 이내

**Constraints**: 로컬 5432 포트 점유 충돌 방어, 컨테이너 외부 볼륨 쓰기 권한 보장, 환경 변수 `.env.local`을 이용한 자격 증명 격리 주입

**Scale/Scope**: 1 DB Instance, 1 Named Volume, 1 Environment Configuration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **데이터 무결성 최우선 (ACID 정합성)**: 
  * 문자셋 인코딩을 `UTF-8`로 강제 초기화하여 세금계산서/영수증 PDF 파싱 텍스트의 깨짐을 원천 방지하고, 시간대(`Asia/Seoul`)를 주입하여 거래 내역의 타임스탬프 왜곡을 차단함.
  * 최신 PostgreSQL 18 버전의 정렬형 UUIDv7 내장 함수(`uuidv7()`) 및 AIO(비동기 I/O) 성능 설계를 고려하여 기초 인프라를 최적 셋업함.
- **자원 점유 최적화**: 
  * Supabase 등 외부 무료 DB 커넥션 풀 고갈 한계를 극복하기 위해 향후 연동 시 최대 가용 풀 크기를 안전하게 제약하는 환경을 대비함.
- **비용 절감용 바이패스**: 
  * 가맹점 템플릿 레이아웃 캐시 테이블 등 로컬 복합 인덱싱을 매끄럽게 처리할 수 있는 PostgreSQL의 성능적 안정성을 뒷받침함.

## Project Structure

### Documentation (this feature)

```text
specs/001-local-env-setup/
├── plan.md              # This file (Implementation Plan)
├── research.md          # Phase 0 output (Docker Volume & PG18 Version Decision)
├── data-model.md        # Phase 1 output (DB Config & volume entity specification)
├── quickstart.md        # Phase 1 output (One-click execution & DoD check manual)
└── checklists/
    └── requirements.md  # Quality gate checklist
```

### Source Code (repository root)

1일차 인프라 독립 환경 셋업 단계에서는 비즈니스 백엔드/프론트엔드 코드 작성을 배제하고 순수 RDBMS 인프라 부팅에 초점을 맞추며, 4일차 보일러플레이트 및 5일차 통합 docker-compose 수립 전까지 격리 운영됩니다.

```text
.specify/
├── feature.json         # Current feature path metadata
.env.local.example       # Local environment template (to be created in Phase 2)
specs/
└── 001-local-env-setup/ # 1일차 명세 및 계획 산출물 일체
```

**Structure Decision**: 1일차 인프라 빌드를 위해 프로젝트 루트에 환경 변수 템플릿과 명세 산출물 구조를 적용하고 단일 컨테이너 방식으로 구동하도록 수립하였습니다.

## Complexity Tracking

> **GATE: Passed (No constitution violations identified)**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

# Implementation Plan: PDF Text Lossless Extraction Utility

**Branch**: `005-extract-pdf-text` | **Date**: 2026-05-31 | **Spec**: [spec.md](file:///D:/Projects/Private/ai-ledger-automation/specs/005-extract-pdf-text/spec.md)

**Input**: Feature specification from `/specs/005-extract-pdf-text/spec.md`

## Summary

본 계획서는 세금계산서 및 영수증 PDF 파일 내에 물리적으로 내장된 텍스트 레이어를 단 하나의 글자 누락이나 인코딩 깨짐 없이 완전히 추출하기 위한 Python 유틸리티 모듈 설계서입니다.
속도가 압도적으로 빠른 **PyMuPDF(fitz)**를 1차 엔진으로 기동하고, 분석 예외 또는 한글 자모 깨짐 감지 시 자동으로 **pdfplumber**로 상호 보완하는 **하이브리드 자동 Fallback 구조**를 채택합니다. 
또한 탭과 공백을 유지해 표 구조를 보존하는 **레이아웃 보존 모드**와 **단순 텍스트 추출 모드**를 파라미터로 개방하며, 비정상 PDF 유입 시 크래시 없는 **구조화된 DTO(`ExtractionResult`)** 반환을 보장합니다.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: PyMuPDF (fitz) (v1.23+), pdfplumber (v0.10+) -> `backend/pyproject.toml`에 선언적 명세 및 uv 잠금 통제

**Storage**: N/A (순수 메모리/파일 처리 유틸리티 클래스)

**Testing**: Django test runner (또는 unittest / pytest) -> `backend/tests/unit/test_pdf_extractor.py`

**Target Platform**: Dockerized Linux Server (Debian/Alpine-based) 및 Windows 개발 머신

**Project Type**: Python backend library / utility service module

**Performance Goals**: 2페이지 분량의 영수증 PDF 파일에 대해 0.3초 미만의 응답 지연 방어

**Constraints**:
- 메모리 누수 방지 (BytesIO 객체 소멸자 즉시 호출 및 PDF 문서 핸들 안전 해제)
- Mac OS 등에서 생성된 PDF의 자모 낱개 분리 현상을 방어하기 위한 NFC 유니코드 강제 표준 정규화 적용
- 50페이지 초과 초대형 PDF 처리 시 OOM 방지를 위한 제네레이터(Generator) 방식의 안전한 로드 지원

**Scale/Scope**: 영수증/세금계산서 무손실 텍스트 추출 정확도 100% (물리 텍스트 레이어 내장 PDF에 한함)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. 데이터 무결성 및 원자성 최우선**:
  - *검증*: 유틸리티 내부 예외가 전역 전파되는 것을 전면 차단하고 `ExtractionResult` DTO에 `success=False` 및 사유를 감싸 반환함으로써, 상위 호출자(Celery/DB 트랜잭션 등)의 트랜잭션 원자적 롤백 및 Dirty State 방지에 강력히 협력합니다.
- [x] **II. 비동기 큐 전환 및 자원 점유 최적화**:
  - *검증*: CPU 부하가 집중될 수 있는 PDF 분석을 지원하기 위해 파일 경로뿐만 아니라 BytesIO 스트림 로딩을 함께 구현하여, 향후 Celery 비동기 작업 큐 내부에서 비차단식(Non-blocking) 메모리 버퍼 처리가 완벽히 가능하도록 설계했습니다.
- [x] **III. 하이브리드 비용 최적화 파이프라인**:
  - *검증*: 추출된 무손실 레이아웃 텍스트는 10자리 사업자번호 식별을 기반으로 하는 로컬 정규식 bypass 캐시 매칭(`merchant_templates`) 엔진의 핵심 입력 소스로 공급되어 LLM API 호출 비용 절감(0원 수렴)의 원천 기반을 제공합니다.
- [x] **VI. 크로스 플랫폼 대칭 툴링**:
  - *검증*: 테스트 스크립트나 로컬 빌드 검증 도구 추가 시 scripts/ 폴더 아래에 Windows(PowerShell, `*.ps1`)와 Linux/macOS(Bash, `*.sh`) 대칭형 환경 검증 툴링 배포 원칙을 영구 수호합니다.
- [x] **VII. 선언적 의존성 및 uv 패키지 격리 수호**:
  - *검증*: `PyMuPDF`와 `pdfplumber` 라이브러리는 `backend/pyproject.toml`에 선언되며 `uv lock` 및 `uv sync`를 통해서만 가상환경 `.venv` 내에 안전하게 격리 공급됩니다.

## Project Structure

### Documentation (this feature)

```text
specs/005-extract-pdf-text/
├── spec.md              # 기능 요구사항 명세서 (Approved)
├── plan.md              # 본 구현 계획 설계서 (This file)
├── research.md          # Phase 0 연구 결과 (PyMuPDF vs. pdfplumber 비교)
├── data-model.md        # Phase 1 데이터 모델 및 DTO 명세
├── quickstart.md        # Phase 1 개발자 연동 퀵스타트
├── contracts/
│   └── contracts.md     # Phase 1 공개 API 및 예외 처리 시퀀스 계약 문서
└── checklists/
    └── requirements.md  # 명세서 품질 체크리스트 (100% Checked)
```

### Source Code (repository root)

이 프로젝트는 `backend` 모노레포 폴더가 독립적으로 분리된 형태이므로, **Option 2**의 형태로 소스 구조를 배치하고 정적 모듈화합니다.

```text
backend/
├── src/
│   ├── utils/
│   │   ├── __init__.py
│   │   └── pdf_extractor.py       # 핵심 PDFTextExtractor 유틸리티 클래스 코드
│   └── services/
│       # 향후 텍스트 추출 결과를 주입받아 LLM이나 정규식 bypass를 태우는 비즈니스 서비스 레이어
└── tests/
    └── unit/
        └── test_pdf_extractor.py  # 단위 테스트 케이스 코드 파일
```

**Structure Decision**: 
- 최종적으로 **Option 2 (Web application)** 구조에 맞추어 `backend/src/utils/pdf_extractor.py`에 유틸리티 어댑터를 구현하고, `backend/tests/unit/test_pdf_extractor.py`에 Django 및 unittest 기반의 단위 테스트를 대칭 배치하여 린트 및 품질 검증을 엄수하기로 결정하였습니다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*위반 사항 없음. 헌법적 코어 제약 조건 및 UV 선언적 락 관리 규정을 100% 준수합니다.*

# Research: PDF Text Lossless Extraction Technology

**Feature**: PDF Text Extraction Utility | **Date**: 2026-05-31
**Status**: Completed

본 연구는 PDF 내장 텍스트 레이어를 깨짐 없이 정확하게 추출하기 위해 Python 생태계 내 대표 라이브러리인 PyMuPDF(fitz)와 pdfplumber의 기능적 특성을 비교 연구하고, 최종 하이브리드 아키텍처 설계를 도출하기 위해 수행되었습니다.

---

## 1. 핵심 의사결정 사항 (Decisions & Rationale)

### 결정 1: 하이브리드 엔진 선택 및 자동 Fallback 구조 채택
- **결정 (Decision)**: 기본 엔진으로 `PyMuPDF`를 작동시키며, 텍스트 레이아웃 손상이나 특정 한글 인코딩 예외 발생 시 `pdfplumber` 엔진으로 즉각 **자동 Fallback**을 실행합니다.
- **타당성 (Rationale)**: 
  - **PyMuPDF**는 C 기반(MuPDF) 래퍼로 성능이 압도적으로 빠르며(타 라이브러리 대비 10x~50x), 일반적인 상용 PDF에서 높은 인코딩 정합성을 보입니다.
  - **pdfplumber**는 순수 Python 기반(pdfminer.six)으로 다소 무겁지만, 개별 문자의 기하학적 좌표(Bounding Box) 분석 및 테이블 격자 구조 파싱력이 극도로 정교합니다.
  - 따라서, 높은 처리속도(PyMuPDF)를 기본 취득하면서, 인코딩 문제나 복잡한 테이블 분석 결함이 발생할 때 최상의 복구 정밀도(pdfplumber)를 차선책으로 작동시킴으로써 무손실 신뢰 한계선 100%를 달성합니다.
- **고려된 대안 (Alternatives)**: 
  - *대안 1: pdfplumber 단일 구성* — 테이블 구조 인식이 매우 명확하나, 다량의 이메일 및 PDF 유입 시 서버 CPU와 메모리 오버헤드가 급증하여 Celery 비동기 자원 병목을 유발할 위험이 있어 배제함.

### 결정 2: 매개변수 기반 레이아웃 보존 옵션 제공
- **결정 (Decision)**: 단순 텍스트 나열(Raw Mode)과 탭/공백 문자를 보존하는 시각적 격자 구조 유지(Layout-Preserved Mode)를 메서드 매개변수 플래그(`layout: bool`, 기본값: `True`)를 통해 유연하게 제어 및 전환할 수 있도록 설계합니다.
- **타당성 (Rationale)**: 
  - 세금계산서와 가계부 영수증은 가로 방향으로 `품목명 | 단가 | 수량 | 공급가액` 등의 논리적 관계가 나열되므로, 단순 연속 텍스트 추출 시 이 관계가 붕괴하여 LLM이 데이터를 엉뚱하게 결합(Hallucination)할 수 있습니다. 
  - 따라서 탭과 공백을 유지하는 레이아웃 보존이 최선이며, 특수한 대량 분석 패턴 매칭의 경우 속도 최적화를 위해 단순 텍스트 모드도 함께 선택할 수 있도록 개방합니다.
- **고려된 대안 (Alternatives)**:
  - *대안 2: Layout-Preserved 강제 통일* — 성능 우선이 필요한 대량 텍스트 파싱 파이프라인에서 불필요한 공백 계산 비용이 상시 지출되는 단점이 있어 유연화 옵션으로 대체함.

### 결정 3: DTO 기반의 복원력 있는(Graceful) 에러 핸들링
- **결정 (Decision)**: 암호화 PDF, 텍스트 레이어가 전무한 스캔 이미지 PDF 등의 유입 시 상위 호출부의 중단을 막기 위해 `success: False` 플래그와 `error_message`를 포함한 **구조화된 DTO(`ExtractionResult`)**를 안전하게 반환합니다.
- **타당성 (Rationale)**: 
  - 백그라운드 Celery Worker 환경에서 원시 예외(Segmentation Fault, CryptographyError 등)가 전역 전파되어 워커 데몬이 크래시되거나 재부팅되는 치명적 사고를 완벽히 격리 방어합니다.
  - 반환된 에러 상태를 토대로 상위 라우터가 안전하게 OCR 전처리 파이프라인으로 전환(Route Bypass)할 수 있는 조기 의사결정의 기반이 됩니다.

---

## 2. 세부 기술 프로토타이핑 조사

### A. PyMuPDF (fitz) 핵심 API 조사
```python
import fitz

# 파일 또는 바이트 스트림 로드
doc = fitz.open(stream=pdf_bytes, filetype="pdf")

# 텍스트 추출 모드 비교
# 1. 단순 텍스트 나열 (Raw Mode)
text_raw = page.get_text("text")

# 2. 레이아웃 보존 (Layout-Preserved Mode)
# "blocks"는 텍스트를 기하학적 블록 단위로 나누어 탭/공백과 구조를 보존하여 정렬
blocks = page.get_text("blocks") 
# blocks 내부의 개별 텍스트 세그먼트를 좌표 기준 좌->우, 상->하 정렬하여 병합
```

### B. pdfplumber 핵심 API 조사
```python
import pdfplumber

with pdfplumber.open(pdf_bytes_io) as pdf:
    page = pdf.pages[0]
    # layout=True 플래그는 PDF 내부의 공백 및 탭을 기하학적 위치와 유사하게 유지하여 추출
    text_layout = page.extract_text(layout=True)
    text_raw = page.extract_text(layout=False)
```

### C. 한글 유니코드 깨짐 및 자모 분리 방어 (NFC 정규화)
일부 PDF 생성 엔진이나 macOS 환경의 PDF에서는 한글 낱자가 'ㄱ-ㅏ-ㅇ' 형태로 조합되지 않고 분리되어 추출됩니다. 이를 해결하기 위해 파이썬 내장 `unicodedata` 모듈의 NFC 표준화 방식을 사용합니다:
```python
import unicodedata

# macOS의 NFD 방식을 표준 NFC 완성형 한글 방식으로 변환
normalized_text = unicodedata.normalize('NFC', raw_extracted_text)
```
NFD 텍스트는 글자 누락 판독이나 LLM의 토큰 인식 오류를 극대화하므로, 추출 직후 무조건 유니코드 정규화를 통과시키는 헌법적 무결성을 엄수합니다.

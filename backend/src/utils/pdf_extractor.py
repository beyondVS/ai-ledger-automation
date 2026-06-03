import unicodedata
from collections.abc import Generator
from io import BytesIO

import fitz
import pdfplumber


class ExtractionResult:
    """
    PDF 텍스트 추출 결과를 보관하는 데이터 전송 객체 (DTO).
    절대 Exception을 호출부로 전파하지 않으며, 안전하게 상태 정보를 구조화해 제공합니다.
    """

    def __init__(
        self,
        success: bool,
        raw_text: str,
        page_texts: dict[int, str],
        extracted_pages: int,
        used_engine: str,
        is_encrypted: bool,
        has_text_layer: bool,
        error_message: str | None = None,
    ) -> None:
        self.success = success
        self.raw_text = raw_text
        self.page_texts = page_texts
        self.extracted_pages = extracted_pages
        self.used_engine = used_engine
        self.is_encrypted = is_encrypted
        self.has_text_layer = has_text_layer
        self.error_message = error_message

    def __repr__(self) -> str:
        return (
            f"<ExtractionResult success={self.success} engine={self.used_engine} "
            f"pages={self.extracted_pages} encrypted={self.is_encrypted} "
            f"has_text={self.has_text_layer}>"
        )


class PDFTextExtractor:
    """
    PDF 내장 텍스트 레이어를 무손실 추출하기 위한 Python 기반 유틸리티 클래스.
    PyMuPDF(fitz)와 pdfplumber를 활용한 하이브리드 자동 Fallback 구조를 채택합니다.
    """

    def __init__(
        self,
        file_source: str | bytes | BytesIO,
        engine_preference: str | None = "pymupdf",
        normalize_unicode: bool = True,
    ) -> None:
        """
        PDFTextExtractor 인스턴스를 초기화합니다.

        Args:
            file_source: PDF 파일 경로(str), 원시 바이트(bytes), 혹은 BytesIO 스트림
            engine_preference: 최선순위 선호 엔진 ("pymupdf" 또는 "pdfplumber")
            normalize_unicode: 한글 자모 분리 방지를 위한 NFC 정규화 강제 적용 여부
        """
        if not file_source:
            raise ValueError("file_source가 제공되지 않았거나 비어있습니다.")

        self.file_source = file_source
        self.engine_preference = engine_preference.lower() if engine_preference else "pymupdf"
        self.normalize_unicode = normalize_unicode

    def _normalize(self, text: str) -> str:
        """한글 자모 분리 현상(macOS 등 NFD 인코딩)을 방지하기 위해 NFC 유니코드 정규화를 적용합니다."""
        if not text:
            return ""
        if self.normalize_unicode:
            return unicodedata.normalize("NFC", text)
        return text

    def extract_text(
        self, layout: bool = True, start_page: int | None = None, end_page: int | None = None
    ) -> ExtractionResult:
        """
        PDF 문서의 텍스트를 무손실로 파싱 및 추출합니다.
        선호 엔진 작동 실패 시, 차선 엔진으로 자동 Fallback 처리를 개시합니다.

        Args:
            layout: 참(True)인 경우 시각적 표/컬럼 구조 보존 모드, 거짓(False)인 경우 단순 텍스트 모드
            start_page: 추출 범위 시작 페이지 번호 (1-indexed, inclusive)
            end_page: 추출 범위 종료 페이지 번호 (1-indexed, inclusive)

        Returns:
            ExtractionResult 객체
        """
        # engine_preference에 따라 실행 분기 기동
        if self.engine_preference == "pymupdf":
            # 1차 시도: PyMuPDF
            result = self._extract_via_pymupdf(layout, start_page, end_page)
            if result.success:
                return result

            # 1차 실패 시 자동 Fallback: pdfplumber
            fallback_result = self._extract_via_pdfplumber(layout, start_page, end_page)
            if fallback_result.success:
                return fallback_result

            # 둘 다 실패 시 마지막 에러 결과 반환
            return fallback_result
        else:
            # 1차 시도: pdfplumber
            result = self._extract_via_pdfplumber(layout, start_page, end_page)
            if result.success:
                return result

            # 1차 실패 시 자동 Fallback: PyMuPDF
            fallback_result = self._extract_via_pymupdf(layout, start_page, end_page)
            if fallback_result.success:
                return fallback_result

            # 둘 다 실패 시 마지막 에러 결과 반환
            return fallback_result

    def _extract_via_pymupdf(self, layout: bool, start_page: int | None, end_page: int | None) -> ExtractionResult:
        """PyMuPDF(fitz) 라이브러리를 사용해 텍스트를 추출하는 프라이빗 메서드입니다."""
        try:
            if isinstance(self.file_source, str):
                doc = fitz.open(self.file_source)
            elif isinstance(self.file_source, bytes):
                doc = fitz.open(stream=self.file_source, filetype="pdf")
            elif isinstance(self.file_source, BytesIO):
                doc = fitz.open(stream=self.file_source.getvalue(), filetype="pdf")
            else:
                raise ValueError("지원하지 않는 file_source 타입입니다.")
        except Exception as e:
            err_msg = str(e).lower()
            exc_name = e.__class__.__name__.lower()
            is_enc = (
                "encrypted" in err_msg
                or "password" in err_msg
                or "password" in exc_name
                or "incorrect" in exc_name
                or "pdfminer" in exc_name
                or "decrypt" in err_msg
            )
            return ExtractionResult(
                success=False,
                raw_text="",
                page_texts={},
                extracted_pages=0,
                used_engine="pymupdf",
                is_encrypted=is_enc,
                has_text_layer=False,
                error_message=f"PyMuPDF PDF 로드 실패: {str(e)} (암호화)"
                if is_enc
                else f"PyMuPDF PDF 로드 실패: {str(e)}",
            )

        # 로드 후 암호화 여부 감지 필터
        if doc.is_encrypted:
            doc.close()
            return ExtractionResult(
                success=False,
                raw_text="",
                page_texts={},
                extracted_pages=0,
                used_engine="pymupdf",
                is_encrypted=True,
                has_text_layer=False,
                error_message="암호화되어 보호된 PDF 문서입니다.",
            )

        try:
            total_pages = len(doc)
            start_idx = max(0, (start_page - 1) if start_page else 0)
            end_idx = min(total_pages, end_page if end_page else total_pages)

            page_texts = {}
            raw_text_list = []
            extracted_pages_count = 0
            has_text_found = False

            for i in range(start_idx, end_idx):
                page = doc[i]

                # layout=True 시 blocks를 사용해 가로/세로 좌표 정렬을 바탕으로 표 구조 보존
                if layout:
                    blocks = page.get_text("blocks")
                    sorted_blocks = sorted(blocks, key=lambda x: (x[1], x[0]))
                    block_texts = []
                    for b in sorted_blocks:
                        b_text = b[4].strip()
                        if b_text:
                            block_texts.append(b_text)
                    page_text = "\n".join(block_texts)
                else:
                    page_text = page.get_text("text")

                normalized_page_text = self._normalize(page_text)

                page_number = i + 1
                page_texts[page_number] = normalized_page_text
                raw_text_list.append(normalized_page_text)

                if normalized_page_text.strip():
                    has_text_found = True

                extracted_pages_count += 1

            doc.close()
            full_text = "\n\n".join(raw_text_list)

            # 물리적 텍스트 레이어 검증 필터
            if not has_text_found:
                return ExtractionResult(
                    success=False,
                    raw_text=full_text,
                    page_texts=page_texts,
                    extracted_pages=extracted_pages_count,
                    used_engine="pymupdf",
                    is_encrypted=False,
                    has_text_layer=False,
                    error_message="물리적 텍스트 레이어가 PDF 내에 존재하지 않습니다.",
                )

            return ExtractionResult(
                success=True,
                raw_text=full_text,
                page_texts=page_texts,
                extracted_pages=extracted_pages_count,
                used_engine="pymupdf",
                is_encrypted=False,
                has_text_layer=True,
            )
        except Exception as e:
            if "doc" in locals() and not doc.is_closed:
                doc.close()
            return ExtractionResult(
                success=False,
                raw_text="",
                page_texts={},
                extracted_pages=0,
                used_engine="pymupdf",
                is_encrypted=False,
                has_text_layer=False,
                error_message=f"PyMuPDF 텍스트 추출 실패: {str(e)}",
            )

    def _extract_via_pdfplumber(self, layout: bool, start_page: int | None, end_page: int | None) -> ExtractionResult:
        """pdfplumber 라이브러리를 사용해 텍스트를 추출하는 프라이빗 메서드입니다."""
        try:
            if isinstance(self.file_source, str):
                pdf = pdfplumber.open(self.file_source)
            elif isinstance(self.file_source, bytes):
                pdf = pdfplumber.open(BytesIO(self.file_source))
            elif isinstance(self.file_source, BytesIO):
                # BytesIO 원본을 그대로 전달
                pdf = pdfplumber.open(self.file_source)
            else:
                raise ValueError("지원하지 않는 file_source 타입입니다.")
        except Exception as e:
            err_msg = str(e).lower()
            exc_name = e.__class__.__name__.lower()
            is_enc = (
                "encrypted" in err_msg
                or "password" in err_msg
                or "password" in exc_name
                or "incorrect" in exc_name
                or "pdfminer" in exc_name
                or "decrypt" in err_msg
            )
            return ExtractionResult(
                success=False,
                raw_text="",
                page_texts={},
                extracted_pages=0,
                used_engine="pdfplumber",
                is_encrypted=is_enc,
                has_text_layer=False,
                error_message=f"pdfplumber PDF 로드 실패: {str(e)} (암호화)"
                if is_enc
                else f"pdfplumber PDF 로드 실패: {str(e)}",
            )

        try:
            total_pages = len(pdf.pages)
            start_idx = max(0, (start_page - 1) if start_page else 0)
            end_idx = min(total_pages, end_page if end_page else total_pages)

            page_texts = {}
            raw_text_list = []
            extracted_pages_count = 0
            has_text_found = False

            for i in range(start_idx, end_idx):
                page = pdf.pages[i]

                # layout=True 인 경우 pdfplumber의 가로 기하 구조 유지 기능 가동
                if layout:
                    page_text = page.extract_text(layout=True) or ""
                else:
                    page_text = page.extract_text(layout=False) or ""

                normalized_page_text = self._normalize(page_text)

                page_number = i + 1
                page_texts[page_number] = normalized_page_text
                raw_text_list.append(normalized_page_text)

                if normalized_page_text.strip():
                    has_text_found = True

                extracted_pages_count += 1

            pdf.close()
            full_text = "\n\n".join(raw_text_list)

            # 물리적 텍스트 레이어 검증 필터
            if not has_text_found:
                return ExtractionResult(
                    success=False,
                    raw_text=full_text,
                    page_texts=page_texts,
                    extracted_pages=extracted_pages_count,
                    used_engine="pdfplumber",
                    is_encrypted=False,
                    has_text_layer=False,
                    error_message="물리적 텍스트 레이어가 PDF 내에 존재하지 않습니다.",
                )

            return ExtractionResult(
                success=True,
                raw_text=full_text,
                page_texts=page_texts,
                extracted_pages=extracted_pages_count,
                used_engine="pdfplumber",
                is_encrypted=False,
                has_text_layer=True,
            )
        except Exception as e:
            try:
                pdf.close()
            except:
                pass
            return ExtractionResult(
                success=False,
                raw_text="",
                page_texts={},
                extracted_pages=0,
                used_engine="pdfplumber",
                is_encrypted=False,
                has_text_layer=False,
                error_message=f"pdfplumber 텍스트 추출 실패: {str(e)}",
            )

    def extract_text_generator(
        self, layout: bool = True, start_page: int | None = None, end_page: int | None = None
    ) -> Generator[tuple[int, str], None, None]:
        """
        초대형 PDF 처리를 위해, 페이지 번호와 해당 페이지의 추출 텍스트 튜플을
        페이지 단위의 제네레이터(Generator)로 스트리밍 반환하여 메모리 고갈(OOM)을 예방합니다.

        Yields:
            (int, str): (페이지 번호, NFC 정규화 완료된 해당 페이지 텍스트)
        """
        # PyMuPDF를 주력으로 가동 시도
        try:
            if isinstance(self.file_source, str):
                doc = fitz.open(self.file_source)
            elif isinstance(self.file_source, bytes):
                doc = fitz.open(stream=self.file_source, filetype="pdf")
            elif isinstance(self.file_source, BytesIO):
                doc = fitz.open(stream=self.file_source.getvalue(), filetype="pdf")
            else:
                raise ValueError("지원하지 않는 file_source 타입입니다.")

            total_pages = len(doc)
            start_idx = max(0, (start_page - 1) if start_page else 0)
            end_idx = min(total_pages, end_page if end_page else total_pages)

            for i in range(start_idx, end_idx):
                page = doc[i]
                if layout:
                    blocks = page.get_text("blocks")
                    sorted_blocks = sorted(blocks, key=lambda x: (x[1], x[0]))
                    block_texts = []
                    for b in sorted_blocks:
                        b_text = b[4].strip()
                        if b_text:
                            block_texts.append(b_text)
                    page_text = "\n".join(block_texts)
                else:
                    page_text = page.get_text("text")

                yield i + 1, self._normalize(page_text)
            doc.close()
            return
        except Exception:
            pass

        # PyMuPDF 실패 시 pdfplumber로 Fallback 스트리밍
        try:
            if isinstance(self.file_source, str):
                pdf = pdfplumber.open(self.file_source)
            elif isinstance(self.file_source, bytes):
                pdf = pdfplumber.open(BytesIO(self.file_source))
            elif isinstance(self.file_source, BytesIO):
                pdf = pdfplumber.open(self.file_source)
            else:
                return

            total_pages = len(pdf.pages)
            start_idx = max(0, (start_page - 1) if start_page else 0)
            end_idx = min(total_pages, end_page if end_page else total_pages)

            for i in range(start_idx, end_idx):
                page = pdf.pages[i]
                if layout:
                    page_text = page.extract_text(layout=True) or ""
                else:
                    page_text = page.extract_text(layout=False) or ""

                yield i + 1, self._normalize(page_text)
            pdf.close()
        except:
            pass

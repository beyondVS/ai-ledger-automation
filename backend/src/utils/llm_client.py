import base64
import io
import json
import logging
import os

from django.conf import settings
from litellm import Router
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReceiptItemSchema(BaseModel):
    item_name: str = Field(description="상세 품목명")
    unit_price: float = Field(description="품목 단가 (음수 불가)")
    quantity: int = Field(description="수량 (1 이상)")
    total_price: float = Field(description="합계 금액 (단가 * 수량)")


class ReceiptSchema(BaseModel):
    vendor_name: str = Field(description="가맹점명 (상호명)")
    vendor_registration_number: str = Field(description="10자리 사업자등록번호 (하이픈 제외 숫자만)")
    transaction_date: str = Field(description="결제 일시 (ISO 8601 형식: YYYY-MM-DDTHH:MM:SSZ)")
    total_amount: float = Field(description="총 결제 금액")
    items: list[ReceiptItemSchema] = Field(description="상세 품목 리스트")


class ReceiptLLMClient:
    """
    [T013] [US1] LiteLLM Router를 활용하여 로컬 Ollama(gemma4:e4b) 우선 가동 및 프로덕션 Gemini-2.5-Flash 폴백 지원 클래스
    """

    def __init__(self):
        # 1. 설정 및 자격증명 조회
        is_production = not getattr(settings, "DEBUG", True)
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")

        ollama_model = getattr(settings, "OLLAMA_MODEL", "gemma4:e4b")
        if not ollama_model.startswith("ollama/"):
            ollama_model = f"ollama/{ollama_model}"
        ollama_api_base = getattr(settings, "OLLAMA_API_BASE", "http://localhost:11434")

        # 2. 동적 모델 리스트 및 폴백 정의
        if is_production and gemini_api_key:
            logger.info("프로덕션 모드: Gemini-2.5-Flash 우선 적용 및 로컬 Ollama 폴백 가동")
            model_list = [
                {
                    "model_name": "receipt-analyzer",  # 주 모델
                    "litellm_params": {
                        "model": "gemini/gemini-2.5-flash",
                        "api_key": gemini_api_key,
                        "request_timeout": 15.0,
                    },
                },
                {
                    "model_name": "ollama-fallback",  # 폴백 모델
                    "litellm_params": {
                        "model": ollama_model,
                        "api_base": ollama_api_base,
                        "request_timeout": 25.0,
                    },
                },
            ]
            self.router = Router(
                model_list=model_list,
                fallbacks=[{"receipt-analyzer": ["ollama-fallback"]}],
                allowed_fails=1,
            )
        else:
            logger.info(f"로컬 개발 모드: 로컬 Ollama ({ollama_model}) 최우선 적용 및 폴백 구성")
            model_list = [
                {
                    "model_name": "receipt-analyzer",  # 주 모델 (Ollama)
                    "litellm_params": {
                        "model": ollama_model,
                        "api_base": ollama_api_base,
                        "request_timeout": 25.0,
                    },
                }
            ]
            self.router = Router(
                model_list=model_list,
                fallbacks=[{"receipt-analyzer": ["receipt-analyzer"]}],
                allowed_fails=1,
            )

    def parse_receipt(self, file_buffer: io.BytesIO, mime_type: str = "image/webp") -> dict | None:
        """
        LiteLLM Router를 통해 통일된 규격(base64 image_url)으로 영수증 구조화 데이터를 추출합니다.
        """
        try:
            file_bytes = file_buffer.getvalue()
            if not file_bytes:
                logger.error("파일 버퍼 바이트가 비어 있습니다.")
                return None

            # 1. 로컬 Ollama 모델을 가동할 때 PDF 유입 시 PyMuPDF 이미지 렌더링 전처리
            is_ollama_target = self.router.model_list[0]["litellm_params"]["model"].startswith("ollama/")
            if is_ollama_target and mime_type == "application/pdf":
                logger.info("로컬 Ollama 가동 감지: PDF 영수증을 PNG 이미지로 가상 렌더링합니다.")
                try:
                    import fitz  # PyMuPDF

                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    if doc.page_count > 0:
                        page = doc[0]  # 첫 페이지만 추출
                        pix = page.get_pixmap(dpi=150)
                        file_bytes = pix.tobytes("png")
                        mime_type = "image/png"
                    else:
                        logger.error("PDF 파일에 페이지가 존재하지 않습니다.")
                        return None
                except Exception as e:
                    logger.exception(f"PDF 로컬 이미지 변환 중 오류 발생: {str(e)}")
                    return None

            prompt = (
                "제공된 영수증 파일의 정보에서 가맹점명, 10자리 사업자등록번호(하이픈 제외), "
                "결제 일시(날짜와 시간 모두 포함된 ISO 8601 형식), 총 결제 금액, 그리고 세부 품목 목록 "
                "(품목명, 단가, 수량, 합계 금액)을 정확히 추출하여 지정된 JSON 스키마에 맞춰 반환해주세요. "
                "사업자등록번호가 보이지 않는 경우에는 '0000000000'으로 채워주세요."
            )

            # 2. 백엔드 성격에 따른 base64 접두사 동적 조율
            base64_data = base64.b64encode(file_bytes).decode("utf-8")
            if is_ollama_target:
                # 로컬 Ollama는 data url prefix가 있으면 illegal base64 데이터로 판단해 400 에러를 냅니다.
                image_url_value = base64_data
            else:
                image_url_value = f"data:{mime_type};base64,{base64_data}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url_value}},
                    ],
                }
            ]

            # Router.completion 단일 호출을 통해 분기 및 폴백을 라우터에 전면 위임
            response = self.router.completion(
                model="receipt-analyzer",
                messages=messages,
                response_format=ReceiptSchema,
                temperature=0.1,
            )

            response_text = response.choices[0].message.content
            if not response_text:
                logger.error("API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = json.loads(response_text)
            logger.info(f"영수증 파싱 성공: {parsed_data.get('vendor_name')}")
            return parsed_data

        except Exception as e:
            logger.exception(f"영수증 분석 중 오류 발생: {str(e)}")
            return None

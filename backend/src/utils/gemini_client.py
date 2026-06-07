import base64
import io
import json
import logging
import os

import litellm
from django.conf import settings
from google import genai
from google.genai import types
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


class GeminiClient:
    """
    [T013] [US1] google-genai 및 litellm을 활용하여 최신 Gemini API 및 로컬 Ollama 연동 지원 클래스
    """

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not self.api_key:
            self.api_key = os.environ.get("GEMINI_API_KEY")

        # 로컬 Ollama 가동 조건
        self.use_ollama = getattr(settings, "OLLAMA_ENABLED", False) or not self.api_key
        self.ollama_model = getattr(settings, "OLLAMA_MODEL", "ollama/gemma4:e4b")
        self.ollama_api_base = getattr(settings, "OLLAMA_API_BASE", "http://localhost:11434")

        if not self.use_ollama:
            self.client = genai.Client(api_key=self.api_key)
        else:
            logger.info(f"로컬 Ollama 연동 가동 예정 (모델: {self.ollama_model})")

    def parse_receipt(self, file_buffer: io.BytesIO, mime_type: str = "image/webp") -> dict | None:
        """
        MIME 타입에 맞춰 파일 버퍼를 최신 Gemini API 또는 로컬 Ollama 모델로 분석시킵니다.
        """
        try:
            file_bytes = file_buffer.getvalue()
            if not file_bytes:
                logger.error("파일 버퍼 바이트가 비어 있습니다.")
                return None

            prompt = (
                "제공된 영수증 파일의 정보에서 가맹점명, 10자리 사업자등록번호(하이픈 제외), "
                "결제 일시(날짜와 시간 모두 포함된 ISO 8601 형식), 총 결제 금액, 그리고 세부 품목 목록 "
                "(품목명, 단가, 수량, 합계 금액)을 정확히 추출하여 지정된 JSON 스키마에 맞춰 반환해주세요. "
                "사업자등록번호가 보이지 않는 경우에는 '0000000000'으로 채워주세요."
            )

            # 1. 로컬 Ollama 분기 (LiteLLM)
            if self.use_ollama:
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}},
                        ],
                    }
                ]
                response = litellm.completion(
                    model=self.ollama_model,
                    messages=messages,
                    response_format=ReceiptSchema,
                    api_base=self.ollama_api_base,
                    temperature=0.1,
                )
                response_text = response.choices[0].message.content

            # 2. 클라우드 Gemini 분기 (google-genai)
            else:
                part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ReceiptSchema,
                        temperature=0.1,
                    ),
                )
                response_text = response.text

            if not response_text:
                logger.error("API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = json.loads(response_text)
            logger.info(f"영수증 파싱 성공: {parsed_data.get('vendor_name')}")
            return parsed_data

        except Exception as e:
            logger.exception(f"영수증 분석 중 오류 발생: {str(e)}")
            return None

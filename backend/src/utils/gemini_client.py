import io
import json
import logging

import google.generativeai as genai
from django.conf import settings
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
    [T013] [US1] Gemini-2.5-Flash API를 연동하여 영수증 이미지 분석 및 Structured Outputs 수신 클래스
    """

    def __init__(self):
        # base.py에 설정된 API Key 로드
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            import os

            api_key = os.environ.get("GEMINI_API_KEY")

        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY가 설정되어 있지 않습니다.")

    def parse_receipt(self, image_buffer: io.BytesIO) -> dict | None:
        """
        WebP 이미지 버퍼를 수신하여 Gemini-2.5-Flash API로 송신하고,
        강제된 JSON Schema 형식의 영수증 데이터 구조를 반환합니다.
        오류 발생 시 None을 반환합니다.
        """
        try:
            image_bytes = image_buffer.getvalue()
            if not image_bytes:
                logger.error("이미지 버퍼 바이트가 비어 있습니다.")
                return None

            model = genai.GenerativeModel("gemini-2.5-flash")

            prompt = (
                "제공된 영수증 이미지의 텍스트 정보에서 가맹점명, 10자리 사업자등록번호(하이픈 제외), "
                "결제 일시(날짜와 시간 모두 포함된 ISO 8601 형식), 총 결제 금액, 그리고 세부 품목 목록 "
                "(품목명, 단가, 수량, 합계 금액)을 정확히 추출하여 지정된 JSON 스키마에 맞춰 반환해주세요. "
                "사업자등록번호가 보이지 않는 경우에는 '0000000000'으로 채워주세요."
            )

            # Structured Outputs API 호출
            response = model.generate_content(
                [{"mime_type": "image/webp", "data": image_bytes}, prompt],
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=ReceiptSchema,
                    temperature=0.1,  # 정확도 높은 추출을 위해 낮게 설정
                ),
            )

            if not response.text:
                logger.error("Gemini API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = json.loads(response.text)
            logger.info(f"Gemini 영수증 파싱 성공: {parsed_data.get('vendor_name')}")
            return parsed_data

        except Exception as e:
            logger.exception(f"Gemini API 영수증 분석 중 오류 발생: {str(e)}")
            return None

import base64
import io
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
    transaction_date: str = Field(description="결제 일시 (타임존 제외 영수증 상의 로컬 일시: YYYY-MM-DDTHH:MM:SS)")
    total_amount: float = Field(description="총 결제 금액")
    category: str = Field(description="지출 카테고리 (예: 식비, 생활용품, 쇼핑, 문화/여가, 교통, 기타 등)")
    items: list[ReceiptItemSchema] = Field(description="상세 품목 리스트")
    proposed_date_pattern: str = Field(
        default="",
        description="제공된 영수증 원본 텍스트 내에서 본 결제 일시(이메일 시각 등 상세 시간 포함 구절 최우선 매칭)를 가장 정확히 캡처할 수 있는 정적 정규식 패턴",
    )
    proposed_amount_pattern: str = Field(
        default="",
        description="제공된 영수증 원본 텍스트 내에서 총 결제 금액을 가장 정확히 캡처할 수 있는 정적 정규식 패턴",
    )


class ReceiptLLMClient:
    """
    [T013] [US1] LiteLLM Router를 활용하여 로컬 Ollama 우선 가동 및 프로덕션 Gemini 폴백 지원 클래스
    """

    def __init__(self):
        # 1. 설정 및 자격증명 조회
        gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
        gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

        ollama_model = getattr(settings, "OLLAMA_MODEL", "gemma4:e4b")
        ollama_api_base = getattr(settings, "OLLAMA_API_BASE", "http://localhost:11434")

        # LiteLLM 형식 명세 보정
        gemini_model_param = f"gemini/{gemini_model}" if not gemini_model.startswith("gemini/") else gemini_model
        ollama_model_param = f"ollama/{ollama_model}" if not ollama_model.startswith("ollama/") else ollama_model

        # 2. 동적 모델 리스트 구성
        active_models = []

        if gemini_enabled and gemini_api_key:
            active_models.append(
                {
                    "model_name": "receipt-analyzer-gemini",
                    "litellm_params": {
                        "model": gemini_model_param,
                        "api_key": gemini_api_key,
                        "request_timeout": 15.0,
                    },
                }
            )

        # Ollama 모델은 항상 fallback용 혹은 로컬 전용으로 활성화해 둡니다.
        active_models.append(
            {
                "model_name": "receipt-analyzer-ollama",
                "litellm_params": {
                    "model": ollama_model_param,
                    "api_base": ollama_api_base,
                    "request_timeout": 90.0,
                },
            }
        )

        # Router 구성용 모델 리스트 및 fallbacks 구성
        router_model_list = []
        fallbacks = []

        if len(active_models) >= 2:
            primary = active_models[0]
            fallback = active_models[1]
            primary["model_name"] = "receipt-analyzer"
            fallback["model_name"] = "ollama-fallback"

            router_model_list = [primary, fallback]
            fallbacks = [{"receipt-analyzer": ["ollama-fallback"]}]
            logger.info("LiteLLM Router 구성 완료: Gemini -> Ollama 폴백 체계")
        else:
            single = active_models[0]
            single["model_name"] = "receipt-analyzer"
            router_model_list = [single]
            fallbacks = [{"receipt-analyzer": ["receipt-analyzer"]}]
            logger.info("LiteLLM Router 구성 완료: 단일 모델 체계")

        self.router = Router(
            model_list=router_model_list,
            fallbacks=fallbacks,
            allowed_fails=1,
        )

    def parse_receipt(self, file_buffer: io.BytesIO, mime_type: str = "image/webp") -> ReceiptSchema | None:
        """
        LiteLLM Router를 통해 통일된 규격(base64 image_url)으로 영수증 구조화 데이터를 추출합니다.
        """
        try:
            file_bytes = file_buffer.getvalue()
            if not file_bytes:
                logger.error("파일 버퍼 바이트가 비어 있습니다.")
                return None

            # 1. 대상 식별 (GEMINI_ENABLED 스위치 및 API KEY의 존재 여부 기준)
            gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
            gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
            is_ollama_target = not (gemini_enabled and gemini_api_key)

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
                "제공된 영수증 파일의 비주얼 정보로부터 가맹점명, 사업자등록번호, 결제 일시, "
                "총 결제 금액, 카테고리, 세부 품목 목록을 정확히 추출하여 지정된 JSON 스키마에 맞춰 반환해주세요.\n\n"
                "### 반드시 준수해야 할 데이터 포맷 규칙:\n"
                "1. **사업자등록번호 (vendor_registration_number)**:\n"
                "   - 하이픈(-)이나 공백 등 일체의 구분기호를 생략하고 오직 '10자리의 순수한 숫자 문자열'만 출력하세요. (예: '1208612345')\n"
                "   - **중요**: 영수증 내에 'VAT Registration Number', 'VAT Reg No', 'VAT No' 등으로 표기된 10자리 형식의 등록번호(예: 502-80-25057) 역시 사업자등록번호로 정확히 매핑하여 추출해야 합니다.\n"
                "   - 사업자등록번호가 보이지 않거나 식별 불가능할 경우 반드시 '0000000000'으로 채우세요.\n"
                "2. **결제 일시 (transaction_date)**:\n"
                "   - 타임존 정보가 배제된 영수증 상의 결제 로컬 시각을 YYYY-MM-DDTHH:MM:SS 형식 문자열로 출력하세요. (예: 'YYYY-MM-DDTHH:MM:SS')\n"
                "   - **중요**: 만약 영수증 본문에는 날짜(예: '2026-06-11' 또는 '06/11/2026')만 적혀 있고 구체적인 결제 시간 정보가 없으나, 이메일 헤더 영역에 구체적인 수신 시각(예: '날짜: 2026년 6월 11일 오후 3:45')이 명시되어 있는 경우, 영수증의 날짜와 메일 헤더의 시간 정보(오전/오후 시:분을 24시간 형식 HH:MM:SS로 변환)를 지능적으로 병합하여 최종 결제 일시를 완성하세요.\n"
                "   - 텍스트 전체에서 상세 결제/수신 시각 정보를 전혀 식별할 수 없는 경우에만 시간 부분을 '00:00:00'으로 채우세요. 시간대(Z 또는 +09:00 등)는 절대 문자열 끝에 추가하지 마십시오.\n"
                "3. **지출 카테고리 (category)**:\n"
                "   - 가맹점명과 상세 품목 목록을 분석하여 한국 가계부에서 널리 쓰이는 대분류 카테고리 중 가장 적합한 하나를 매핑하십시오.\n"
                "   - 카테고리 목록 기준: **'식비'**, **'생활용품'**, **'쇼핑'**, **'교통'**, **'문화/여가'**, **'주거/통신'**, **'의료/건강'**, **'교육'**, **'기타'** 중 정확히 하나만 반환하세요.\n"
                "     - 예: 스타벅스/식당 등 -> '식비'\n"
                "     - 예: 에픽게임즈/넷플릭스 등 게임, OTT 결제 -> '문화/여가'\n"
                "     - 예: 마트/편의점 생필품 결제 -> '생활용품'\n"
                "     - 예: 의류/뷰티 몰 등 -> '쇼핑'\n"
                "   - **중요**: '미분류'라는 단어는 절대 사용하거나 생성하지 마십시오. 카테고리를 특정하기 곤란할 경우 반드시 **'기타'**를 반환하십시오.\n"
                "4. **수치 데이터 (total_amount, unit_price, total_price)**:\n"
                "   - 쉼표(,), 원화 기호(₩, 원), 달러 기호($) 등 일체의 통화 서식이나 특수문자를 배제하고 오직 '순수한 숫자(float 또는 int)'로만 출력하세요. (예: 15000.00)\n"
                "5. **세부 품목 (items)**:\n"
                "   - 각 품목별 item_name(상세 품목명), unit_price(단가), quantity(수량, 1 이상의 정수), total_price(합계 금액, 단가 * 수량과 일치해야 함)를 정확히 누락 없이 매핑하세요.\n"
                "6. **동적 정규식 패턴 생성 (proposed_date_pattern, proposed_amount_pattern)**:\n"
                "   - 제공받은 영수증 원본 텍스트 레이아웃을 기반으로, 추후 LLM 호출 없이 원본 텍스트에서 결제 일시(시간 정보가 있을 경우 가장 먼저 매칭되도록 파이프 '|' 연산자로 묶음)와 총 결제 금액을 정확히 추출해낼 수 있는 맞춤형 정규식 패턴을 지능적으로 설계하여 반환하세요.\n"
                "   - 예 (proposed_date_pattern): `(?:날짜:\\s*\\d{4}년\\s*\\d{1,2}월\\s*\\d{1,2}일\\s*오[전후]\\s*\\d{1,2}:\\d{2}|주문일자:\\s*[0-9\\-]{10})`\n"
                "   - 예 (proposed_amount_pattern): `(?:합계\\s*([0-9,]+)|금액:\\s*([0-9,]+))`"
            )

            base64_data = base64.b64encode(file_bytes).decode("utf-8")

            # 2. Gemini가 활성화된 경우 우선 시도
            if not is_ollama_target:
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
                try:
                    logger.info("Gemini API를 통해 영수증 분석 시도 중...")
                    response = self.router.completion(
                        model="receipt-analyzer",
                        messages=messages,
                        response_format=ReceiptSchema,
                        temperature=0.1,
                    )
                    response_text = response.choices[0].message.content
                    if response_text:
                        parsed_data = ReceiptSchema.model_validate_json(response_text)
                        logger.info(f"Gemini 영수증 파싱 성공: {parsed_data.vendor_name}")
                        return parsed_data
                except Exception as gemini_err:
                    logger.warning(f"Gemini API 분석 실패로 로컬 Ollama 폴백을 기동합니다. 사유: {str(gemini_err)}")

            # 3. 로컬 Ollama 단독 기동 혹은 Gemini 실패 시의 폴백 기동
            # Ollama는 접두사(prefix)가 없어야 디코딩 오류가 발생하지 않습니다.
            image_url_value = base64_data
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url_value}},
                    ],
                }
            ]

            target_model = "ollama-fallback" if not is_ollama_target else "receipt-analyzer"
            logger.info(f"Ollama API ({target_model})를 통해 영수증 분석 시도 중...")

            response = self.router.completion(
                model=target_model,
                messages=messages,
                response_format=ReceiptSchema,
                temperature=0.1,
            )

            response_text = response.choices[0].message.content
            if not response_text:
                logger.error("API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = ReceiptSchema.model_validate_json(response_text)
            logger.info(f"Ollama 영수증 파싱 성공: {parsed_data.vendor_name}")
            return parsed_data

        except Exception as e:
            logger.exception(f"영수증 분석 중 오류 발생: {str(e)}")
            return None

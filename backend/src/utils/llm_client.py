import base64
import io
import logging
import os

from django.conf import settings
from litellm import Router
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


COMMON_RECEIPT_PROMPT = (
    "제공된 영수증 정보로부터 가맹점명, 사업자등록번호, 결제 일시, "
    "총 결제 금액, 카테고리, 세부 품목 목록을 정확히 추출하여 지정된 JSON 스키마에 맞춰 반환해주세요.\n\n"
    "### 반드시 준수해야 할 데이터 포맷 규칙:\n"
    "1. **사업자등록번호 (vendor_registration_number)**:\n"
    "   - 하이픈(-)이나 공백 등 일체의 구분기호를 생략하고 오직 '10자리의 순수한 숫자 문자열'만 출력하세요. (예: '1208612345')\n"
    "   - **중요**: 해외 및 국외 상점(예: Epic Games, Apple, Steam 등)의 인보이스/영수증 본문이나 최하단에 표기된 'VAT Registration Number', 'VAT Reg No', 'VAT ID', 'Tax ID', 'GSTIN' 형식의 10자리 번호(예: '502-80-25057' 또는 'CHE-502.802.505' 등의 유사 패턴) 역시 국외 가맹점 사업자등록번호로 완벽하게 인식하고, 문자만 골라내어 10자리 숫자(예: '5028025057')로 변환해 추출해야 합니다.\n"
    "   - 영수증 전체 영역에서 사업자등록번호 및 해외 VAT 등록번호가 완전히 보이지 않거나 식별 불가능할 경우에만 반드시 '0000000000'으로 채우세요.\n"
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
    "   - 각 품목별 item_name(상세 품목명), unit_price(단가), quantity(수량, 1 이상의 정수), total_price(합계 금액, 단가 * 수량과 일치해야 함)를 정확히 누락 없이 매핑하세요."
)

LOCAL_TEXT_PROMPT_EXTENSION = (
    "6. **동적 정규식 패턴 생성 (proposed_date_pattern, proposed_amount_pattern)**:\n"
    "   - 제공받은 영수증 원본 텍스트 레이아웃을 기반으로, 추후 LLM 호출 없이 원본 텍스트에서 결제 일시(시간 정보가 있을 경우 가장 먼저 매칭되도록 파이프 '|' 연산자로 묶음)와 총 결제 금액을 정확히 추출해낼 수 있는 맞춤형 정규식 패턴을 지능적으로 설계하여 반환하세요.\n"
    "   - 예 (proposed_date_pattern): `(?:날짜:\\s*\\d{4}년\\s*\\d{1,2}월\\s*\\d{1,2}일\\s*오[전후]\\s*\\d{1,2}:\\d{2}|주문일자:\\s*[0-9\\-]{10})`\n"
    "   - 예 (proposed_amount_pattern): `(?:합계\\s*([0-9,]+)|금액:\\s*([0-9,]+))`"
)


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
    approval_number: str | None = Field(default=None, description="결제 승인번호 (카드 승인번호 등, 없을 시 null)")
    order_id: str | None = Field(default=None, description="주문번호 또는 인보이스 ID, 없을 시 null")


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

    def parse_receipt_local(self, raw_ocr_text: str) -> ReceiptSchema | None:
        """
        로컬 OCR 텍스트를 입력받아 로컬 Ollama 모델(gemma4:e4b)을 호출해 JSON 스키마로 구조화하고,
        상세 품목 금액 합산 정합성을 검증한 뒤 결과를 반환합니다.
        """
        try:
            if not raw_ocr_text or not raw_ocr_text.strip():
                logger.error("입력 OCR 텍스트가 비어 있습니다.")
                return None

            # 1. 대상 식별 (GEMINI_ENABLED 스위치 및 API KEY의 존재 여부 기준)
            gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
            gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
            is_ollama_target = not (gemini_enabled and gemini_api_key)
            target_model = "ollama-fallback" if not is_ollama_target else "receipt-analyzer"

            prompt = (
                COMMON_RECEIPT_PROMPT + "\n\n"
                f"### OCR 텍스트:\n{raw_ocr_text}\n\n"
                f"### 추가 포맷 규칙:\n{LOCAL_TEXT_PROMPT_EXTENSION}"
            )

            messages = [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]

            logger.info(f"로컬 Ollama API ({target_model})를 통해 OCR 텍스트 분석 시도 중...")
            response = self.router.completion(
                model=target_model,
                messages=messages,
                response_format=ReceiptSchema,
                temperature=0.1,
            )

            response_text = response.choices[0].message.content
            if not response_text:
                logger.error("로컬 Ollama API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = ReceiptSchema.model_validate_json(response_text)

            # [Q1 반영] 상세 품목의 합산 금액 정합성(오차 0원) 검증
            items_sum = sum(item.total_price for item in parsed_data.items)
            if round(items_sum, 2) != round(parsed_data.total_amount, 2):
                logger.warning(
                    f"로컬 Ollama 파싱 실패: 상세 품목 합산 금액({items_sum})과 총액({parsed_data.total_amount})이 일치하지 않습니다."
                )
                return None

            logger.info(f"로컬 Ollama 영수증 파싱 성공: {parsed_data.vendor_name}")
            return parsed_data

        except Exception as e:
            logger.exception(f"로컬 Ollama 영수증 분석 중 오류 발생: {str(e)}")
            return None

    def parse_receipt_cloud_text(self, raw_ocr_text: str) -> ReceiptSchema | None:
        """
        로컬 OCR 텍스트를 입력받아 Gemini-2.5-Flash Text-only API를 호출해 JSON 스키마로 구조화하고,
        상세 품목 금액 합산 정합성을 검증한 뒤 결과를 반환합니다.
        """
        try:
            if not raw_ocr_text or not raw_ocr_text.strip():
                logger.error("입력 OCR 텍스트가 비어 있습니다.")
                return None

            gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
            gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
            if not gemini_enabled or not gemini_api_key:
                logger.warning(
                    "Gemini API가 활성화되어 있지 않거나 API 키가 없어 2단계 클라우드 텍스트 파싱을 건너뜁니다."
                )
                return None

            prompt = (
                COMMON_RECEIPT_PROMPT + "\n\n"
                f"### OCR 텍스트:\n{raw_ocr_text}\n\n"
                f"### 추가 포맷 규칙:\n{LOCAL_TEXT_PROMPT_EXTENSION}"
            )

            messages = [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]

            logger.info("Gemini API (Text-only)를 통해 OCR 텍스트 분석 시도 중...")
            response = self.router.completion(
                model="receipt-analyzer",
                messages=messages,
                response_format=ReceiptSchema,
                temperature=0.1,
            )

            response_text = response.choices[0].message.content
            if not response_text:
                logger.error("Gemini API가 빈 응답을 반환했습니다.")
                return None

            parsed_data = ReceiptSchema.model_validate_json(response_text)

            # 상세 품목의 합산 금액 정합성(오차 0원) 검증
            items_sum = sum(item.total_price for item in parsed_data.items)
            if round(items_sum, 2) != round(parsed_data.total_amount, 2):
                logger.warning(
                    f"Gemini Text-only 파싱 실패: 상세 품목 합산 금액({items_sum})과 총액({parsed_data.total_amount})이 일치하지 않습니다."
                )
                return None

            logger.info(f"Gemini Text-only 영수증 파싱 성공: {parsed_data.vendor_name}")
            return parsed_data

        except Exception as e:
            logger.exception(f"Gemini Text-only 영수증 분석 중 오류 발생: {str(e)}")
            return None

    def parse_receipt_cloud_vision(self, file_buffer: io.BytesIO, mime_type: str) -> ReceiptSchema | None:
        """
        영수증 파일(WebP 이미지 또는 PDF)의 원본 바이트 버퍼를 입력받아
        Gemini-2.5-Flash Vision API를 호출해 JSON 스키마로 구조화하고,
        금액 검증 통과 시 결과를 반환합니다. PDF인 경우 이미지 변환 없이 그대로 API로 전송합니다.
        """
        try:
            file_bytes = file_buffer.getvalue()
            if not file_bytes:
                logger.error("비전 파싱 대상 파일 버퍼가 비어 있습니다.")
                return None

            gemini_enabled = getattr(settings, "GEMINI_ENABLED", False)
            gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")

            prompt = COMMON_RECEIPT_PROMPT
            parsed_data = None

            # base64 인코딩
            base64_data = base64.b64encode(file_bytes).decode("utf-8")

            # 1. Gemini가 활성화된 경우 우선 시도 (접두사 포함하여 송신)
            if gemini_enabled and gemini_api_key:
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
                    logger.info("Gemini API (Vision)를 통해 멀티모달 영수증 분석 시도 중...")
                    response = self.router.completion(
                        model="receipt-analyzer",
                        messages=messages,
                        response_format=ReceiptSchema,
                        temperature=0.1,
                    )
                    response_text = response.choices[0].message.content
                    if response_text:
                        parsed_data = ReceiptSchema.model_validate_json(response_text)
                        logger.info(f"Gemini Vision 영수증 파싱 성공: {parsed_data.vendor_name}")
                except Exception as gemini_err:
                    logger.warning(
                        f"Gemini Vision API 분석 실패로 로컬 Ollama 폴백을 기동합니다. 사유: {str(gemini_err)}"
                    )

            # 2. 로컬 Ollama 단독 기동 혹은 Gemini 실패 시의 폴백 기동 (접두사 제거하여 송신)
            if not parsed_data:
                # Ollama는 접두사(prefix)가 없어야 디코딩 오류가 발생하지 않습니다.
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": base64_data}},
                        ],
                    }
                ]
                target_model = "ollama-fallback" if (gemini_enabled and gemini_api_key) else "receipt-analyzer"
                logger.info(f"Ollama API ({target_model})를 통해 멀티모달 영수증 분석 시도 중...")
                response = self.router.completion(
                    model=target_model,
                    messages=messages,
                    response_format=ReceiptSchema,
                    temperature=0.1,
                )
                response_text = response.choices[0].message.content
                if response_text:
                    parsed_data = ReceiptSchema.model_validate_json(response_text)
                    logger.info(f"Ollama Vision 영수증 파싱 성공: {parsed_data.vendor_name}")

            if not parsed_data:
                logger.error("비전 분석 결과 획득 실패")
                return None

            # 상세 품목의 합산 금액 정합성(오차 0원) 검증
            items_sum = sum(item.total_price for item in parsed_data.items)
            if round(items_sum, 2) != round(parsed_data.total_amount, 2):
                logger.warning(
                    f"비전 파싱 실패: 상세 품목 합산 금액({items_sum})과 총액({parsed_data.total_amount})이 일치하지 않습니다."
                )
                return None

            return parsed_data

        except Exception as e:
            logger.exception(f"비전 영수증 분석 중 오류 발생: {str(e)}")
            return None

import pytest
from apps.ledgers.models import MerchantTemplate

@pytest.mark.django_db
def test_merchant_template_verification_query_isolation():
    """
    미검증 템플릿(is_verified: False)이 VerifiedTemplateManager에 의해
    바이패스 조회 필터에서 철저히 차단 격리되며, 오직 검증 승인 템플릿만
    성공적으로 추출되는지 검증합니다.
    """
    # 1. 2개의 가맹점 캐시 템플릿 적재
    # - Template A: 수동 검증 완료 승인 상태 (is_verified: True)
    template_verified = MerchantTemplate.objects.create(
        vendor_registration_number="1234500001",
        vendor_name="커피빈 강남점",
        parsing_rules={"date_regex": r"\d{4}-\d{2}-\d{2}", "amount_regex": r"\d+원"},
        is_verified=True
    )
    
    # - Template B: 자율 자동 수집 제안 상태 (is_verified: False 기본 격리 보존)
    template_unverified = MerchantTemplate.objects.create(
        vendor_registration_number="9876500002",
        vendor_name="메가커피",
        parsing_rules={"date_regex": r"\d{2}/\d{2}/\d{2}", "amount_regex": r"\d+원"},
        is_verified=False
    )
    
    # 2. [기본 objects 매니저 스캔]: 전체 등록 템플릿 접근 검증 (개수 2개여야 함)
    assert MerchantTemplate.objects.count() == 2
    
    # 3. [Verified custom 매니저 스캔]: 헌법 III조 비용 최적화 필터 검증
    # - 커피빈 (Verified: True) -> 정상 획득 계약 만족
    rule_verified = MerchantTemplate.verified_objects.get_bypass_rule("1234500001")
    assert rule_verified is not None
    assert rule_verified.vendor_name == "커피빈 강남점"
    
    # - 메가커피 (Verified: False) -> 획득 결과 None 격리 통제 필터 계약 만족
    rule_unverified = MerchantTemplate.verified_objects.get_bypass_rule("9876500002")
    assert rule_unverified is None

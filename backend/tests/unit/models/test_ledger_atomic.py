import pytest
from django.db import transaction
from apps.accounts.models import User
from apps.ledgers.models import Ledger, LedgerItem
from apps.ledgers.services import create_ledger_transactional

@pytest.mark.django_db
def test_create_ledger_transactional_success():
    """
    정상적인 가계부 마스터 정보와 세부 품목 3개가 주어졌을 때,
    단일 트랜잭션 블록 내에서 1:N 원자적 일괄 인서트가 정상 완수되고 커밋되는지 검증합니다.
    """
    user = User.objects.create(email="customer@example.com")
    
    ledger_data = {
        "vendor_registration_number": "1234567890",
        "vendor_name": "스타벅스 강남점",
        "transaction_date": "2026-05-29",
        "total_amount": 15000.00,
        "supply_value": 13636.36,
        "vat_amount": 1363.64,
        "raw_llm_response": {"parsing_speed": "120ms"}
    }
    
    items_data = [
        {"item_name": "카페 아메리카노", "quantity": 2, "unit_price": 4500.00, "total_price": 9000.00},
        {"item_name": "자바칩 프라푸치노", "quantity": 1, "unit_price": 6000.00, "total_price": 6000.00}
    ]
    
    result = create_ledger_transactional(str(user.id), ledger_data, items_data)
    
    assert result["status"] == "SUCCESS"
    assert Ledger.objects.filter(id=result["ledger_id"]).exists()
    
    ledger = Ledger.objects.get(id=result["ledger_id"])
    assert ledger.items.count() == 2
    assert ledger.vendor_registration_number == "1234567890"


@pytest.mark.django_db
def test_create_ledger_transactional_rollback_on_item_failure():
    """
    마스터 영수증 정보는 완전히 유효하나, 자식 품목을 적재하는 도중
    세부 제약 위배(예: null 품목명 또는 의도적 예외)가 유발되었을 때
    부모 Ledger 레코드까지 깨끗하게 자동 롤백되어 DB에 찌꺼기가 남지 않는지 검증합니다.
    """
    user = User.objects.create(email="customer_fail@example.com")
    user_id_str = str(user.id)
    
    ledger_data = {
        "vendor_registration_number": "9876543210",
        "vendor_name": "투썸플레이스",
        "transaction_date": "2026-05-29",
        "total_amount": 8000.00,
        "supply_value": 7272.73,
        "vat_amount": 727.27,
    }
    
    # item_name이 누락되어 DB IntegrityError(NOT NULL Constraint)를 유발시키는 비정상 품목 리스트
    bad_items_data = [
        {"item_name": None, "quantity": 1, "unit_price": 8000.00, "total_price": 8000.00}
    ]
    
    # 실행 시 자식 제약 오류로 예외가 전파되어야 함
    with pytest.raises(Exception):
        create_ledger_transactional(user_id_str, ledger_data, bad_items_data)
        
    # [ACID 수호 검증]: 롤백 작동으로 인해 부모 Ledger조차 DB에 생성되어 있으면 안 됨!
    assert not Ledger.objects.filter(user=user, vendor_name="투썸플레이스").exists()

import json
import traceback
from django.db import transaction, IntegrityError
from apps.accounts.models import User
from apps.ledgers.models import Ledger, LedgerItem
from apps.tasks.models import FailedTask

def create_ledger_transactional(user_id: str, ledger_data: dict, items_data: list) -> dict:
    """
    [T011, T015] create_ledger_transactional 서비스 함수
    - Ledger 마스터 레코드와 LedgerItem 상세 배열을 단일 원자적 데이터베이스 트랜잭션 세션 내에서 일괄 생성합니다.
    - 데이터 적재 도중 예외나 데이터베이스 연결 장해 등 오류 발생 시 전역 롤백을 수행하여 파편화를 기계적으로 방지합니다.
    - UNIQUE 제약조건 위배(IntegrityError) 발생 시, 작업을 큐의 낭비 없이 강제 중단하고 
      FailedTask 모델에 입력 페이로드와 에러 콜스택을 안전 격리 적재(DLQ)합니다.
    """
    try:
        with transaction.atomic():
            # 1. 연관 사용자(User) 존재 여부 확보
            user = User.objects.get(id=user_id)
            
            # 2. Ledger 마스터 레코드 삽입
            # (vendor_registration_number가 공백이거나 누락된 상태일 경우, 모델 내 save() 필터에 의해 '0000000000' 자동 치환 적재)
            ledger = Ledger.objects.create(
                user=user,
                vendor_registration_number=ledger_data.get('vendor_registration_number', '0000000000'),
                vendor_name=ledger_data['vendor_name'],
                transaction_date=ledger_data['transaction_date'],
                total_amount=ledger_data['total_amount'],
                supply_value=ledger_data['supply_value'],
                vat_amount=ledger_data['vat_amount'],
                raw_llm_response=ledger_data.get('raw_llm_response')
            )
            
            # 3. LedgerItem 상세 자식 레코드 벌크(bulk_create) 삽입
            ledger_items = []
            for item in items_data:
                ledger_items.append(
                    LedgerItem(
                        ledger=ledger,
                        item_name=item['item_name'],
                        quantity=item.get('quantity', 1),
                        unit_price=item['unit_price'],
                        total_price=item['total_price']
                    )
                )
            
            LedgerItem.objects.bulk_create(ledger_items)
            
            return {
                "status": "SUCCESS",
                "ledger_id": str(ledger.id),
                "items_count": len(ledger_items)
            }
            
    except IntegrityError as ie:
        # 중복 영수증 유입 또는 고유성 위배 발생 시 Dead Letter Queue 격리 적재 분기 실행
        raw_payload_dict = {
            "user_id": user_id,
            "ledger_data": ledger_data,
            "items_data": items_data
        }
        
        FailedTask.objects.create(
            user=user if 'user' in locals() else None,
            task_type="API_LEDGER_INGEST_DUPLICATE",
            raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
            error_message=str(ie),
            error_stacktrace=traceback.format_exc()
        )
        # 상위 라우터나 Celery 태스크에서 409 Conflict 등의 응답을 할 수 있도록 예외 재전파
        raise ie
        
    except Exception as e:
        # 데이터베이스 강제 단절 등 예기치 않은 시스템 장해 발생 시 전격 자동 롤백 및 에러 적재
        raw_payload_dict = {
            "user_id": user_id,
            "ledger_data": ledger_data,
            "items_data": items_data
        }
        
        FailedTask.objects.create(
            user=user if 'user' in locals() else None,
            task_type="API_LEDGER_INGEST_SYSTEM_ERROR",
            raw_payload=json.dumps(raw_payload_dict, default=str, ensure_ascii=False),
            error_message=str(e),
            error_stacktrace=traceback.format_exc()
        )
        raise e

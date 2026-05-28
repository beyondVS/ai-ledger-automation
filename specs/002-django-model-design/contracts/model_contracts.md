# Interface Contract Specification: Django Models & Database Operations

본 계약 명세서는 가계부 자동화 시스템의 백엔드 비즈니스 로직(API View, Celery Task)과 6대 Django Model 간에 충족되어야 하는 런타임 동작 정합성, 트랜잭션 수명 주기, 예외 처리 파이프라인, 그리고 인프라 리소스 제약에 대한 기계적 계약을 규정합니다.

---

## 1. 1:N 원자적 트랜잭션 적재 계약 (Ledgers & LedgerItems Atomicity Contract)

### 1.1 개요
단일 영수증 데이터 적재 시, 부모 가계부 레코드(`Ledger`)와 그에 속한 상세 품목 레코드 배열(`LedgerItem`)은 반드시 단 하나의 원자적 데이터베이스 트랜잭션 내에서 처리되어야 합니다.

### 1.2 계약 인터페이스 스펙
```python
# Django ORM 트랜잭션 무결성 가상 스펙 명세
from django.db import transaction
from django.db import IntegrityError
from typing import Dict, List, Any

def create_ledger_transactional(user_id: str, ledger_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    [CRITICAL CONTRACT]
    - 반드시 transaction.atomic() 컨텍스트 내에서 실행되어야 합니다.
    - Ledgers 및 LedgerItems 인서트 연산 중 단 하나의 필드라도 제약조건(예: 음수 단가, null 누락 등)에 위배되는 경우
      전역 롤백을 수행하여 데이터 파편화(Dirty State)를 100% 방지합니다.
    """
    try:
        with transaction.atomic():
            # 1. 부모 Ledger 생성
            ledger = Ledger.objects.create(
                user_id=user_id,
                vendor_registration_number=ledger_data.get('vendor_registration_number', '0000000000'),
                vendor_name=ledger_data['vendor_name'],
                transaction_date=ledger_data['transaction_date'],
                total_amount=ledger_data['total_amount'],
                supply_value=ledger_data['supply_value'],
                vat_amount=ledger_data['vat_amount'],
                raw_llm_response=ledger_data.get('raw_llm_response')
            )
            
            # 2. 자식 LedgerItem 배열 일괄 생성
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
            
            # bulk_create를 사용한 대역폭 절감 및 원자적 인서트
            LedgerItem.objects.bulk_create(ledger_items)
            
            return {"status": "SUCCESS", "ledger_id": str(ledger.id)}
            
    except IntegrityError as ie:
        # DB 제약조건 위배 (복합 UNIQUE 위배 등) 발생 시 런타임 예외를 상위로 전파
        raise ie
    except Exception as e:
        # 데이터베이스 연결 유실 등 기타 장해 발생 시 전격 자동 롤백 후 예외 전파
        raise RuntimeError(f"Atomic Transaction Failed, Rolling back: {str(e)}")
```

---

## 2. 복합 UNIQUE 위배 중복 차단 계약 (Ledger Duplicate Prevention Contract)

### 2.1 개요
가계부 테이블은 `UNIQUE (user_id, vendor_registration_number, transaction_date, total_amount)` 복합 고유 제약을 갖습니다.

### 2.2 계약 인터페이스 스펙
- **중복 탐지 및 차단 스키마**:
  - 이미 적재된 결제 내역과 `(user_id, vendor_registration_number, transaction_date, total_amount)`가 100% 일치하는 데이터로 인서트 호출 시, 데이터베이스 레이어에서 `IntegrityError`를 반환합니다.
- **예외 처리 & FailedTask 로깅 분기 계약**:
  - API 서버 단에서 중복 입력이 감지되면 HTTP 409 Conflict 응답을 즉시 디스패치합니다.
  - 비동기 Celery 메일 인바운드 웹훅이나 백그라운드 파서 실행 도중 중복 제약에 위배되는 경우, 무작정 재시도하여 큐를 고갈시키지 않고 해당 페이로드 및 상세 장해 로그를 즉시 **`FailedTask` (Dead Letter Queue)**에 영구 격리 적재하고 Celery 작업을 안전하게 종료 처리합니다.

---

## 3. 정규식 캐시 검증 바이패스 계약 (MerchantTemplate Bypass Isolation Contract)

### 3.1 개요
비용 최적화를 위해 유료 LLM 파싱을 건너뛰는 바이패스 규칙 쿼리 시, 오직 관리자 수동 검증이 완료된 검증 템플릿만 필터링하여 반영합니다.

### 3.2 계약 인터페이스 스펙
```python
# Django Manager 또는 쿼리 스펙 계약
from django.db import models

class VerifiedTemplateManager(models.Manager):
    def get_bypass_rule(self, vendor_registration_number: str):
        """
        [CRITICAL CONTRACT]
        - 오직 is_verified: True 상태의 템플릿만 획득합니다.
        - is_verified: False인 미검증 템플릿은 우회 바이패스에 절대 반영되지 못하도록 사전에 차단합니다.
        """
        return self.get_queryset().filter(
            vendor_registration_number=vendor_registration_number,
            is_verified=True
        ).first()
```
- **자율 진화 생성 계약**:
  - Gemini LLM 파싱 완료 데이터 기반으로 자동 제안되어 적재되는 템플릿은 **반드시 기본값 `is_verified: False`**를 유지한 상태로 인서트되어야 합니다.

---

## 4. Supabase DB 커넥션 풀 가용한계 계약 (Resource Pooling Constraints Contract)

### 4.1 개요
Supabase Free Tier 및 AWS RDS 무료 등급 인프라 붕괴를 원천 예방하기 위해 전체 컨테이너 아키텍처의 DB Connection 개수를 엄격히 고정합니다.

### 4.2 계약 사양 명세
- **Django Settings DB Connection 관리**:
  - api_server 컨테이너 및 Celery 비동기 워커가 유입 시 무차별적인 풀 확장을 금지합니다.
  - `CONN_MAX_AGE` 값을 적정선으로 튜닝하고, 최대 풀 크기를 다음과 같이 물리적으로 제한합니다:
    - **api_server 최대 커넥션 풀 크기**: `5` 개 이하
    - **async_worker 최대 커넥션 풀 크기**: `3` 개 이하
    - **전체 합산 가용 한계**: `8` 개 이하
  - 이 제약을 위반할 경우, 동시성 스레스홀드를 초과하기 전에 기계적인 웹 요청 대기 지연(Queueing)을 수행하여 데이터베이스 락다운 장해를 완전히 방어해야 합니다.

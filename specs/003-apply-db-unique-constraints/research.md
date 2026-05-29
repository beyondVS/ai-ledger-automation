# Research & Decisions: DB Migration and Unique Constraints

**Feature**: Database Migration and Unique Constraints
**Branch**: `003-apply-db-unique-constraints`
**Date**: 2026-05-29

## 1. 결정사항 1: 복합 고유 제약조건 구현 표준 규격 확정

- **선택된 방안 (Decision)**: **`models.UniqueConstraint`** 표준 스펙 사용
- **선택 이유 (Rationale)**: 
  장고 레거시 메타 속성인 `unique_together` 대신 최신의 `models.UniqueConstraint`를 사용하면 아래와 같은 명확한 이점을 지닙니다:
  1. **인덱스 명칭 세밀화**: DB 엔진 단의 복합 인덱스 이름을 `name` 옵션을 통해 정교하게 명시하여 관리할 수 있습니다.
  2. **확장 조건 지원**: 특정 필드가 NULL이 아니거나 조건부 필터를 부여하는 `condition`을 장착할 수 있는 등 현대적 기능 확장에 매우 탁월합니다.
  3. **장고 미래 규격 수호**: Django 장기 로드맵 상 향후 `unique_together`가 사장되고 `UniqueConstraint` 단일 체계로 통합될 예정이므로 아키텍처 수명 정합성을 극대화합니다.
- **고려된 대안 (Alternatives considered)**: 
  - `unique_together` 메타 클래스 속성: 설정 방식이 비교적 짧고 직관적이나, 정교한 DB 제약조건 이름 부여나 조건부 제약 장착이 불가하여 기각했습니다.

---

## 2. 결정사항 2: 사업자등록번호 결락(null) 시 고유 제약조건 우회 차단 전략

- **선택된 방안 (Decision)**: **`'0000000000'`** 문자열 기본 폴백 값 강제 적용
- **선택 이유 (Rationale)**:
  관계형 데이터베이스(PostgreSQL 포함) 표준에 따르면, 복합 UNIQUE 인덱스에 포함된 컬럼 중 어느 하나가 `NULL` 값을 가질 경우, `NULL` 간의 동등 비교는 `False`로 판단되어 중복 적재 방어가 무력화됩니다.
  간이 영수증 등으로 10자리 사업자등록번호가 없는 거래 정보가 다중 유입될 때 중복 삽입을 완벽히 막으려면 스키마 상 `vendor_registration_number` 필드에 기본값인 `'0000000000'`을 강제 보정하여 인서트함으로써, 빈 번호의 영수증이 유입되어도 복합 UNIQUE 제약조건이 100% 정상 작동하도록 방어망을 견고히 보강합니다.
- **고려된 대안 (Alternatives considered)**:
  - `null` 허용 및 애플리케이션 단의 검증: 동시성 유입 상황이나 런타임 경쟁 조건(Race Condition) 하에서 DB 무결성을 지키지 못하므로 영구 기각했습니다.

# Research Report: 로컬 통합 개발 환경 및 PostgreSQL v18+ 인프라 선정

## 1. 로컬 볼륨 마운트 경로 정책

### 결정사항 (Decision)
* **도커 네임드 볼륨 (Docker Named Volume) `postgres_data` 적용**

### 타당성 (Rationale)
1. **OS 권한 충돌 완벽 방어**: Windows 호스트 PC 디렉터리(예: `./pgdata`)를 직접 바인딩할 경우, Windows(NTFS)와 WSL 2 가상 환경(POSIX) 간의 파일 퍼미션 및 소유권(`chown`) 모델 불일치로 인해 PostgreSQL 기동 시 `Permission Denied` 오류와 함께 컨테이너가 무한 크래시에 빠지는 고질적 이슈를 원천 차단합니다.
2. **성능 극대화 (DoD 충족)**: 번역 레이어를 통과하는 Windows 드라이브 마운트와 달리 도커 엔진 가상 영역 내부 I/O를 활용하므로, 성공 기준(`SC-002`)인 **"50ms 이내 쿼리 응답"**을 달성하기에 압도적으로 유리합니다.

### 고려된 대안 (Alternatives considered)
* **호스트 디렉터리 상대 경로 바인딩 (`./pgdata`)**: 로컬 파일 백업/관리가 직관적이라는 장점이 있으나, Windows 환경에서의 극심한 보안/퍼미션 충돌 가능성 및 성능 저하 리스크로 최종 기각되었습니다.

---

## 2. PostgreSQL 버전 선정

### 결정사항 (Decision)
* **`postgres:18-alpine` 공식 이미지 채택**

### 타당성 (Rationale)
1. **시계열 정렬형 UUIDv7 지원**: PostgreSQL 18에 내장된 `uuidv7()` 함수를 PK로 활용하여, 가계부 원장(`ledgers`)과 상세 품목(`ledger_items`)의 시계열 순서 쓰기 성능을 극대화하고 B-tree 인덱스 캐싱 효율을 확보합니다.
2. **비동기 I/O (AIO) 및 Skip Scan 지원**: 대량 거래 내역 집계(Aggregation) 속도를 비약적으로 향상시키고 다중 컬럼 인덱스 조회의 유연성을 확보하여 상시 성능 임계치를 100ms 이내로 방어합니다.
3. **최소 경량화 (Alpine)**: 빌드 및 디스크 자원 소모를 최소화하여 로컬 인스턴스 부팅 소요 시간을 15초 이내로 압축합니다.

### 고려된 대안 (Alternatives considered)
* **PostgreSQL v15/v16**: 안정성이 검증되었으나, 시계열 기반 UUIDv7 네이티브 내장 함수가 존재하지 않고 비동기 I/O 아키텍처 도입 혜택을 누릴 수 없어 최종 기각되었습니다.

export class VirtualPollingManager {
  static activePolls = new Map();

  /**
   * 가상 폴링 루프 개시
   * @param {string} jobId 작업 식별자 UUID
   * @param {string} initialStatus 초기 상태 (PENDING, PROCESSING, COMPLETED)
   * @param {function} onSuccess 분석 성공 시 콜백
   * @param {function} onError 분석 실패 또는 네트워크 에러 시 콜백
   * @param {number} intervalMs 폴링 주기 (기본값: 1000ms)
   */
  static async startPolling(jobId, initialStatus, onSuccess, onError, intervalMs = 1000) {
    // 이미 해당 jobId에 대한 폴링이 활성화된 경우 중복 실행을 피하기 위해 기존 타이머 강제 해제
    this.stopPolling(jobId);

    // 1단계: 초기 상태가 이미 COMPLETED 이면 백엔드에 1차 즉각 조회를 수행하여 콜백 완료 처리
    if (initialStatus === 'COMPLETED') {
      try {
        const response = await this.fetchStatus(jobId);
        if (response.status === 'COMPLETED') {
          onSuccess(response.data);
          return;
        }
      } catch (err) {
        onError(err);
        return;
      }
    }

    // 2단계: PENDING 혹은 PROCESSING 상태인 경우 타이머 가동하여 비동기 추적 개시
    const timerId = setInterval(async () => {
      try {
        const response = await this.fetchStatus(jobId);
        
        if (response.status === 'COMPLETED') {
          this.stopPolling(jobId);
          onSuccess(response.data);
        } else if (response.status === 'FAILED') {
          this.stopPolling(jobId);
          onError(new Error('영수증 분석 처리 중 백엔드 에러가 발생했습니다.'));
        }
        // PENDING, PROCESSING 상태일 때는 다음 인터벌을 대기
      } catch (err) {
        this.stopPolling(jobId);
        onError(err);
      }
    }, intervalMs);

    this.activePolls.set(jobId, timerId);
  }

  /**
   * 폴링 루프 강제 정지 및 메모리 해제
   * @param {string} jobId 
   */
  static stopPolling(jobId) {
    if (this.activePolls.has(jobId)) {
      clearInterval(this.activePolls.get(jobId));
      this.activePolls.delete(jobId);
    }
  }

  /**
   * 백엔드 API 상태 조회 래퍼
   * @param {string} jobId 
   * @returns {Promise<object>}
   */
  static async fetchStatus(jobId) {
    // 헌법 제V조에 명시된 로컬 호스트 및 HTTPS 실서버 환경 라우트 구조 준수
    const response = await fetch(`/api/v1/receipts/status/${jobId}/`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`상태 조회 HTTP 에러: ${response.status}`);
    }

    return await response.json();
  }
}

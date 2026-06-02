import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { VirtualPollingManager } from '../services/pollingService'

// fetch API 모킹
const createFetchResponse = (data) => {
  return {
    ok: true,
    json: () => Promise.resolve(data),
  }
}

describe('VirtualPollingManager [T018] 테스트', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('상태가 COMPLETED이면 즉시 완료 콜백을 가동하고 폴링 루프를 시작하지 않아야 합니다.', async () => {
    const successCb = vi.fn()
    const errorCb = vi.fn()

    // 초기 상태가 COMPLETED이며, 첫 API 조회 시 COMPLETED 반환
    const mockData = { ledger_id: '123', total_amount: 15000 }
    global.fetch.mockResolvedValueOnce(createFetchResponse({
      status: 'COMPLETED',
      data: mockData
    }))

    await VirtualPollingManager.startPolling('job_123', 'COMPLETED', successCb, errorCb)
    
    // 비동기 microtask 실행을 위해 시간을 조금 진행하거나 프라미스 해제
    await vi.runAllTicks()

    expect(successCb).toHaveBeenCalledWith(mockData)
    expect(errorCb).not.toHaveBeenCalled()
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('상태가 PROCESSING이면 주기적으로 폴링하며 COMPLETED 수신 시 폴링 루프를 정지해야 합니다.', async () => {
    const successCb = vi.fn()
    const errorCb = vi.fn()

    // 1차 조회: PROCESSING, 2차 조회: COMPLETED
    global.fetch
      .mockResolvedValueOnce(createFetchResponse({ status: 'PROCESSING', data: null }))
      .mockResolvedValueOnce(createFetchResponse({
        status: 'COMPLETED',
        data: { ledger_id: '123', total_amount: 15000 }
      }))

    // 폴링 인터벌을 1초라고 가정하고 호출
    await VirtualPollingManager.startPolling('job_123', 'PROCESSING', successCb, errorCb)
    
    // 최초 상태가 PROCESSING이면 즉시 api fetch는 하지 않고 인터벌 대기
    expect(global.fetch).not.toHaveBeenCalled()

    // 1초 진행 -> 1차 조회 (PROCESSING)
    await vi.advanceTimersByTimeAsync(1000)
    expect(global.fetch).toHaveBeenCalledTimes(1)
    expect(successCb).not.toHaveBeenCalled()

    // 1초 더 진행 -> 2차 조회 (COMPLETED)
    await vi.advanceTimersByTimeAsync(1000)
    expect(global.fetch).toHaveBeenCalledTimes(2)
    expect(successCb).toHaveBeenCalledWith({ ledger_id: '123', total_amount: 15000 })
    expect(errorCb).not.toHaveBeenCalled()

    // 루프가 정지되었으므로 1초 더 진행해도 조회가 추가로 발생하지 않아야 함
    await vi.advanceTimersByTimeAsync(1000)
    expect(global.fetch).toHaveBeenCalledTimes(2)
  })

  it('API 응답이 실패(status가 FAILED)하거나 네트워크 에러 시 에러 콜백을 호출하고 정지해야 합니다.', async () => {
    const successCb = vi.fn()
    const errorCb = vi.fn()

    // 1차 조회 시 FAILED 수신
    global.fetch.mockResolvedValueOnce(createFetchResponse({ status: 'FAILED', data: null }))

    await VirtualPollingManager.startPolling('job_123', 'PROCESSING', successCb, errorCb)

    // 1초 진행 -> 1차 조회 실행하여 FAILED 감지
    await vi.advanceTimersByTimeAsync(1000)
    expect(global.fetch).toHaveBeenCalledTimes(1)
    expect(successCb).not.toHaveBeenCalled()
    expect(errorCb).toHaveBeenCalled()

    // 루프가 정지되어 추가 조회가 발생하지 않아야 함
    await vi.advanceTimersByTimeAsync(1000)
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })
})

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import DashboardView from '../components/DashboardView.vue'
import Dropzone from '../components/Dropzone.vue'
import ReceiptList from '../components/ReceiptList.vue'
import router from '../router/index'

// 1. 이미지 압축 및 API 전송 서비스 모킹
vi.mock('../services/uploadService', () => ({
  compressImage: vi.fn((file) => Promise.resolve(file)),
  uploadReceiptApi: vi.fn((file, filename) => Promise.resolve({
    job_id: '019e8a8f-d2c6-704e-9403-45493c5cf4d9',
    status: 'COMPLETED',
    data: {
      ledger_id: '019e8a8f-d2c6-704e-9403-45493c5cf4d9',
      merchant_name: '스타벅스',
      vendor_registration_number: '1208612345',
      total_amount: 15000.00,
      items: []
    }
  }))
}))

// 2. 가상 폴링 서비스 모킹
vi.mock('../services/pollingService', () => ({
  VirtualPollingManager: {
    startPolling: vi.fn()
  }
}))

// 3. 로그아웃 API 호출을 포함하는 authService 모킹
vi.mock('../services/authService', () => ({
  logout: vi.fn()
}))

describe('DashboardView.vue - TDD Integration Tests', () => {
  
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('should create object URL on file-detected and revoke it on file-removed', async () => {
    // LocalStorage 세션 주입하여 닉네임 파싱 가능하도록 보장
    const mockSession = {
      accessToken: 'valid_token',
      refreshToken: 'valid_refresh',
      username: '테스터',
      loginTimestamp: Date.now()
    }
    localStorage.setItem('ai_ledger_auth_session', JSON.stringify(mockSession))

    const wrapper = mount(DashboardView, {
      global: {
        plugins: [router]
      }
    })
    
    // 1) 초기 상태: ReceiptList는 화면에 노출되지 않아야 하고 Dropzone만 노출
    expect(wrapper.findComponent(Dropzone).exists()).toBe(true)
    expect(wrapper.findComponent(ReceiptList).exists()).toBe(false)
    
    // 2) Dropzone에서 file-detected 이벤트 모의 트리거
    const mockFile = new File(['receipt-body'], 'test_receipt.jpg', { type: 'image/jpeg' })
    const dropzone = wrapper.findComponent(Dropzone)
    dropzone.vm.$emit('file-detected', mockFile)
    
    // 비동기 작업(compressImage 및 uploadReceiptApi)의 완료를 위해 프라미스 풀기
    await flushPromises()
    
    // URL.createObjectURL이 1회 안전하게 호출되었는지 감시
    expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1)
    
    // Dashboard의 currentFile 반응형 데이터가 매핑되어 ReceiptList 컴포넌트가 노출되는지 확인
    const receiptList = wrapper.findComponent(ReceiptList)
    expect(receiptList.exists()).toBe(true)
    expect(receiptList.props('file')).toBeTruthy()
    expect(receiptList.props('file').name).toBe('test_receipt.jpg')
    
    // 3) ReceiptList에서 file-removed 이벤트 모의 트리거 (삭제 액션)
    receiptList.vm.$emit('file-removed')
    await flushPromises()
    
    // 메모리 누수 방지를 위한 URL.revokeObjectURL 호출 검증
    expect(window.URL.revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost:5173/mock-preview-url')
    
    // Dashboard의 currentFile 상태가 null로 깨끗이 초기화되어 ReceiptList가 언마운트 되었는지 검증
    expect(wrapper.findComponent(ReceiptList).exists()).toBe(false)
  })
})

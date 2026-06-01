import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '../App.vue'
import Dropzone from '../components/Dropzone.vue'
import ReceiptList from '../components/ReceiptList.vue'

describe('App.vue - TDD Integration Tests', () => {
  
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // T014: 파일 감지 시 Object URL 매핑 및 삭제 시 revokeObjectURL 실행 검증
  it('should create object URL on file-detected and revoke it on file-removed', async () => {
    const wrapper = mount(App)
    
    // 1) 초기 상태: ReceiptList는 화면에 노출되지 않아야 하고 Dropzone만 노출
    expect(wrapper.findComponent(Dropzone).exists()).toBe(true)
    expect(wrapper.findComponent(ReceiptList).exists()).toBe(false)
    
    // 2) Dropzone에서 file-detected 이벤트 모의 트리거
    const mockFile = new File(['receipt-body'], 'test_receipt.jpg', { type: 'image/jpeg' })
    const dropzone = wrapper.findComponent(Dropzone)
    await dropzone.vm.$emit('file-detected', mockFile)
    
    // URL.createObjectURL이 1회 안전하게 호출되었는지 감시
    expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(window.URL.createObjectURL).toHaveBeenCalledWith(mockFile)
    
    // App의 currentFile 반응형 데이터가 매핑되어 ReceiptList 컴포넌트가 노출되는지 확인
    const receiptList = wrapper.findComponent(ReceiptList)
    expect(receiptList.exists()).toBe(true)
    expect(receiptList.props('file')).toBeTruthy()
    expect(receiptList.props('file').name).toBe('test_receipt.jpg')
    
    // 3) ReceiptList에서 file-removed 이벤트 모의 트리거 (삭제 액션)
    await receiptList.vm.$emit('file-removed')
    
    // 메모리 누수 방지를 위한 URL.revokeObjectURL 호출 검증
    expect(window.URL.revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:http://localhost:5173/mock-preview-url')
    
    // App의 currentFile 상태가 null로 깨끗이 초기화되어 ReceiptList가 언마운트 되었는지 검증
    expect(wrapper.findComponent(ReceiptList).exists()).toBe(false)
  })
})

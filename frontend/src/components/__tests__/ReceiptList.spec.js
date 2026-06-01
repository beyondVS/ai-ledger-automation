import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReceiptList from '../ReceiptList.vue'

describe('ReceiptList.vue - TDD Unit Tests', () => {

  // T013: 영수증 목록 표시 및 삭제 클릭 시 file-removed 이벤트 송출 검증
  it('should render receipt details and emit "file-removed" event when delete is clicked', async () => {
    // 임의의 가상 영수증 감지 객체 props 모킹
    const mockFile = {
      id: '018fe670-8b1d-7a6c-94eb-f072bbab4567',
      name: 'receipt_test.png',
      size: 1048576, // 1MB
      type: 'image/png',
      previewUrl: 'blob:http://localhost:5173/mock-preview-url'
    }

    const wrapper = mount(ReceiptList, {
      props: {
        file: mockFile
      }
    })

    // 1) 파일 이름 및 썸네일 렌더링 상태 확인
    expect(wrapper.text()).toContain('receipt_test.png')
    
    // 파일 용량 가독성 텍스트 확인 (1MB 또는 1,024 KB 또는 1.00 MB 로 변환 렌더링 권장)
    expect(wrapper.text()).toContain('1.00 MB')

    // 썸네일 src 바인딩 확인
    const img = wrapper.find('img')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('blob:http://localhost:5173/mock-preview-url')

    // 2) 삭제 액션 시뮬레이션
    const deleteButton = wrapper.find('button.delete-btn')
    expect(deleteButton.exists()).toBe(true)
    await deleteButton.trigger('click')

    // file-removed 이벤트 발생 여부 확인
    const emitted = wrapper.emitted('file-removed')
    expect(emitted).toBeTruthy()
  })
})

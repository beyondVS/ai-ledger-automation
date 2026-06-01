import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Dropzone from '../Dropzone.vue'

describe('Dropzone.vue - Validation TDD Unit Tests', () => {

  // T018-1: 10MB 초과 대용량 파일 차단 및 validation-error 이벤트 송출 검증
  it('should block file upload and emit "validation-error" when file size exceeds 10MB', async () => {
    const wrapper = mount(Dropzone)
    
    // 10MB + 1 바이트의 가상 파일 모킹 (10 * 1024 * 1024 = 10485760 bytes)
    const largeFile = new File(['a'.repeat(10485761)], 'huge_receipt.png', { type: 'image/png' })
    
    const fileInput = wrapper.find('input[type="file"]')
    expect(fileInput.exists()).toBe(true)

    // 파일 감입 후 change 이벤트 시뮬레이션
    Object.defineProperty(fileInput.element, 'files', {
      value: [largeFile],
      writable: true
    })
    await fileInput.trigger('change')

    // validation-error 에러 이벤트 감지 확인
    const validationError = wrapper.emitted('validation-error')
    expect(validationError).toBeTruthy()
    expect(validationError[0][0]).toBe('최대 파일 용량(10MB)을 초과하는 파일은 업로드할 수 없습니다.')

    // file-detected 이벤트는 발생하지 않았어야 함
    const fileDetected = wrapper.emitted('file-detected')
    expect(fileDetected).toBeFalsy()
  })

  // T018-2: 미지원 확장자 파일 차단 및 validation-error 이벤트 송출 검증
  it('should block file upload and emit "validation-error" when file format is not supported', async () => {
    const wrapper = mount(Dropzone)
    
    // 미지원 확장자인 .txt 임의 파일 모킹
    const txtFile = new File(['receipt-raw-text'], 'receipt.txt', { type: 'text/plain' })
    
    const fileInput = wrapper.find('input[type="file"]')
    expect(fileInput.exists()).toBe(true)

    // 파일 감입
    Object.defineProperty(fileInput.element, 'files', {
      value: [txtFile],
      writable: true
    })
    await fileInput.trigger('change')

    // validation-error 에러 이벤트 감지 확인
    const validationError = wrapper.emitted('validation-error')
    expect(validationError).toBeTruthy()
    expect(validationError[0][0]).toBe('지원하지 않는 파일 형식입니다. 이미지(JPG, PNG) 또는 PDF 파일만 업로드할 수 있습니다.')

    // file-detected 이벤트는 발생하지 않았어야 함
    const fileDetected = wrapper.emitted('file-detected')
    expect(fileDetected).toBeFalsy()
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import Dropzone from '../Dropzone.vue'

describe('Dropzone.vue - TDD Unit Tests', () => {
  beforeEach(() => {
    class MockFileReader {
      readAsDataURL(file) {
        setTimeout(() => {
          if (this.onload) {
            this.onload({ target: { result: 'data:image/jpeg;base64,dummy' } });
          }
        }, 0);
      }
    }
    vi.stubGlobal('FileReader', MockFileReader);

    const mockCanvasContext = {
      drawImage: vi.fn(),
    };

    const mockCanvas = {
      getContext: vi.fn().mockReturnValue(mockCanvasContext),
      toDataURL: vi.fn().mockReturnValue('data:image/jpeg;base64,compressed-dummy-data'),
      toBlob: vi.fn().mockImplementation((callback) => {
        const blob = new Blob(['compressed-dummy-data'], { type: 'image/jpeg' });
        callback(blob);
      }),
    };

    vi.stubGlobal('HTMLCanvasElement', vi.fn());
    
    class MockImage {
      constructor() {
        this.onload = null;
        this.onerror = null;
        this.width = 0;
        this.height = 0;
      }
      set src(val) {
        setTimeout(() => {
          this.width = 2000;
          this.height = 1200;
          if (this.onload) this.onload();
        }, 0);
      }
      get src() {
        return '';
      }
    }
    vi.stubGlobal('Image', MockImage);

    const originalCreateElement = document.createElement;
    vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'canvas') {
        return mockCanvas;
      }
      return originalCreateElement.call(document, tagName);
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });
  
  // T008: 드래그앤드롭 및 파일 선택 시 file-detected 이벤트 송출 검증
  it('should emit "file-detected" event when a valid file is dropped or selected', async () => {
    const wrapper = mount(Dropzone)
    
    // 유효한 가상 영수증 파일 객체 모킹
    const mockFile = new File(['receipt-content'], 'receipt.png', { type: 'image/png' })
    
    // 1) 파일 선택 시뮬레이션
    const fileInput = wrapper.find('input[type="file"]')
    expect(fileInput.exists()).toBe(true)
    
    // input 객체에 파일 강제 바인딩 후 change 이벤트 발생
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: true
    })
    await fileInput.trigger('change')
    
    // 비동기 Canvas 압축 완료 대기
    await new Promise((resolve) => setTimeout(resolve, 50))
    
    // file-detected 이벤트가 정상적으로 발생했고 페이로드로 mockFile이 전달되었는지 검사
    const emitted = wrapper.emitted('file-detected')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toBeInstanceOf(File)
  })

  // T009: 헌법 제V조 PWA 네이티브 카메라 다이렉트 연동 속성 검증
  it('should strictly follow Constitution Article V for PWA mobile camera capture', () => {
    const wrapper = mount(Dropzone)
    const fileInput = wrapper.find('input[type="file"]')
    
    expect(fileInput.exists()).toBe(true)
    
    // 헌법 규격 V조 강제 속성 교차 확인
    const acceptAttr = fileInput.attributes('accept')
    const captureAttr = fileInput.attributes('capture')
    
    expect(acceptAttr).toBe('image/png, image/jpeg, application/pdf')
    expect(captureAttr).toBe('environment')
  })
})

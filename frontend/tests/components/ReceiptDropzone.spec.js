import { mount } from '@vue/test-utils';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Dropzone from '../../src/components/Dropzone.vue';

// Canvas 및 FileReader API 모킹
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

describe('Dropzone.vue - Image Compression', () => {
  it('드롭 또는 파일 선택으로 이미지 파일 감지 시, 가로 1000px로 1차 압축 인코딩을 수행한다', async () => {
    const wrapper = mount(Dropzone);
    const mockFile = new File(['dummy content'], 'receipt.jpg', { type: 'image/jpeg' });

    // input 파일 체인지 이벤트 시뮬레이션
    const input = wrapper.find('input[type="file"]');
    Object.defineProperty(input.element, 'files', {
      value: [mockFile],
      writable: true
    });
    
    await input.trigger('change');

    // 비동기 Canvas 압축 대기
    await new Promise((resolve) => setTimeout(resolve, 50));

    // 압축 완료 후 file-detected 이벤트 방출 검증
    const emittedEvents = wrapper.emitted('file-detected');
    expect(emittedEvents).toBeTruthy();
    expect(emittedEvents[0][0]).toBeInstanceOf(File);
    expect(emittedEvents[0][0].type).toBe('image/jpeg');
  });
});

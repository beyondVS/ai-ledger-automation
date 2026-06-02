import { describe, it, expect, vi } from 'vitest'
import { compressImage } from '../services/uploadService'

describe('Image Compression Service (HTML5 Canvas)', () => {
  it('should compress image to max width of 1000px and output jpeg blob', async () => {
    // 1. mock File & Image API
    const mockBlob = new Blob(['dummy_image_data'], { type: 'image/jpeg' })
    const mockFile = new File([mockBlob], 'test.jpg', { type: 'image/jpeg' })

    // JSDOM 환경에서 Canvas 및 FileReader 동작 모킹
    const mockCanvas = {
      getContext: () => ({
        drawImage: vi.fn(),
      }),
      toBlob: (callback) => {
        // 압축 후 Blob 생성 콜백 호출 모방
        callback(new Blob(['compressed_data'], { type: 'image/jpeg' }))
      },
      width: 0,
      height: 0,
    }

    vi.stubGlobal('document', {
      createElement: (tag) => {
        if (tag === 'canvas') return mockCanvas
        return {}
      }
    })

    // Image API 모킹 (onload 자동 트리거)
    class ImageMock {
      constructor() {
        this.width = 1200; // 1000px 초과 사이즈 주입
        this.height = 800;
        this.onload = null;
        this.onerror = null;
      }
      set src(val) {
        // src 세팅 시 onload 이벤트 즉시 디스패치
        setTimeout(() => {
          if (this.onload) this.onload()
        }, 0)
      }
    }
    vi.stubGlobal('Image', ImageMock)

    // 2. 압축 함수 구동
    const resultBlob = await compressImage(mockFile)

    // 3. 검증: 압축된 Blob 객체 리턴 여부
    expect(resultBlob).toBeInstanceOf(Blob)
    expect(resultBlob.type).toBe('image/jpeg')
    // Canvas 가로 크기가 MAX_WIDTH(1000px)로 조정되었는지 확인
    expect(mockCanvas.width).toBe(1000)
    expect(mockCanvas.height).toBe(667) // 1200x800 -> 1000x667 비율 유지
  })
})

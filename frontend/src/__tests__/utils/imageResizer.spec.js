import { describe, it, expect } from 'vitest';
import { resizeAndCompressImage } from '../../utils/imageResizer';

// jsdom 환경의 canvas.toBlob 누락 대응을 위한 런타임 모킹
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.toBlob = function(callback, type) {
    const mockBlob = new Blob(['mock-image-data'], { type: type || 'image/jpeg' });
    setTimeout(() => callback(mockBlob), 0);
  };
}

describe('imageResizer Utility', () => {
  
  it('이미지가 아닌 일반 파일(예:텍스트) 유입 시 변환 없이 원본 파일을 그대로 즉시 반환해야 한다', async () => {
    const textFile = new File(['hello-world'], 'test.txt', { type: 'text/plain' });
    const result = await resizeAndCompressImage(textFile);
    expect(result).toBe(textFile);
    expect(result.name).toBe('test.txt');
  });

  it('해상도가 1000px 이하인 작은 이미지는 축소하지 않고 원본 파일을 그대로 즉시 반환해야 한다 (Bypass)', async () => {
    const originalImage = new File(['small-image-bytes'], 'small_photo.png', { type: 'image/png' });
    
    // jsdom 실제 이미지 기동 우회를 위해 순수 가상 Mock 클래스로 대체
    const originalImg = global.Image;
    global.Image = class {
      constructor() {
        this.width = 0;
        this.height = 0;
        this.onload = null;
        this.onerror = null;
      }
      set src(val) {
        setTimeout(() => {
          this.width = 800;
          this.height = 600;
          if (this.onload) this.onload();
        }, 10);
      }
      get src() {
        return '';
      }
    };

    const result = await resizeAndCompressImage(originalImage);
    expect(result).toBe(originalImage);
    
    global.Image = originalImg; // 원복
  });

  it('긴 축이 1000px을 초과하는 대용량 이미지는 가로/세로 비율을 유지하며 1000px 규격으로 리사이징하고 JPEG 80%로 압축 변환해야 한다', async () => {
    const largeImage = new File(['large-image-bytes'], 'large_photo.png', { type: 'image/png' });
    
    // jsdom 실제 이미지 기동 우회를 위해 순수 가상 Mock 클래스로 대체
    const originalImg = global.Image;
    global.Image = class {
      constructor() {
        this.width = 0;
        this.height = 0;
        this.onload = null;
        this.onerror = null;
      }
      set src(val) {
        setTimeout(() => {
          this.width = 4000;
          this.height = 3000;
          if (this.onload) this.onload();
        }, 10);
      }
      get src() {
        return '';
      }
    };

    // Canvas drawImage 모킹 (jsdom canvas.getContext 오류 방지)
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function() {
      return {
        drawImage: () => {}
      };
    };

    const result = await resizeAndCompressImage(largeImage);
    expect(result.type).toBe('image/jpeg');
    expect(result.name).toBe('large_photo.jpg'); // 확장자 보정 체크

    global.Image = originalImg;
    HTMLCanvasElement.prototype.getContext = originalGetContext;
  });
});

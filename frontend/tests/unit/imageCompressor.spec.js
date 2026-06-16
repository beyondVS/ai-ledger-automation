import { describe, it, expect, vi, beforeEach } from "vitest";
import { compressImage } from "../../src/utils/imageCompressor";

describe("imageCompressor.js", () => {
  beforeEach(() => {
    // jsdom 환경에서 Canvas API 모킹 설정
    global.HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
      drawImage: vi.fn()
    });

    global.HTMLCanvasElement.prototype.toBlob = vi.fn().mockImplementation((callback) => {
      // 1MB 크기의 Mock JPEG Blob 반환 시뮬레이션
      const mockBlob = new Blob([new ArrayBuffer(1024 * 1024)], { type: "image/jpeg" });
      callback(mockBlob);
    });

    global.Image = class {
      constructor() {
        // 이미지 로딩 비동기 완료 및 해상도(4000x3000) 모킹 시뮬레이션
        setTimeout(() => {
          this.width = 4000;
          this.height = 3000;
          if (this.onload) this.onload();
        }, 10);
      }
    };
  });

  it("대용량 이미지 데이터가 유입되면 긴 축이 1920px 크기로 변환되고 JPEG Blob으로 압축되어야 한다", async () => {
    const mockFile = new File([new ArrayBuffer(10 * 1024 * 1024)], "receipt.jpg", { type: "image/jpeg" });

    // URL 객체 라이프사이클 API 모킹
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/mock-url");
    global.URL.revokeObjectURL = vi.fn();

    const resultBlob = await compressImage(mockFile);

    expect(resultBlob).not.toBeNull();
    expect(resultBlob.size).toBeLessThanOrEqual(1.5 * 1024 * 1024); // 1.5MB 이하 타겟 준수 검증
    expect(resultBlob.type).toBe("image/jpeg");
  });
});

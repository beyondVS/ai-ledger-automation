/**
 * Canvas API를 이용하여 이미지를 최대 1920px 비율로 리사이징하고, 80% 화질의 JPEG로 압축합니다.
 * @param {File} file 원본 이미지 파일 객체
 * @returns {Promise<Blob>} 압축 가공된 JPEG Blob 데이터
 */
export function compressImage(file) {
  return new Promise((resolve, reject) => {
    // 이미지 타입이 아니면 압축을 건너뛰고 그대로 원본 반환 (Fallback)
    if (!file.type.startsWith("image/")) {
      resolve(file);
      return;
    }

    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        let width = img.width;
        let height = img.height;
        const maxDimension = 1920;

        // 1920px 크기 제한 비례 축소 계산
        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas context 2D를 획득하지 못했습니다."));
          return;
        }

        // 이미지 드로잉 (리사이징 처리)
        ctx.drawImage(img, 0, 0, width, height);

        // JPEG 80% 품질로 Blob 변환
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("Canvas toBlob 변환에 실패했습니다."));
            }
          },
          "image/jpeg",
          0.8
        );
      };

      img.onerror = (err) => {
        reject(err);
      };
    };

    reader.onerror = (err) => {
      reject(err);
    };
  });
}

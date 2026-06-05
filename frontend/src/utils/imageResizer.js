/**
 * HTML5 Canvas API를 이용하여 이미지를 리사이징하고 압축합니다.
 * @param {File} file - 원본 File 객체
 * @param {number} maxDimension - 최대 긴 축 해상도 (기본값: 1000px)
 * @param {number} quality - 압축 품질 (0.0 ~ 1.0, 기본값: 0.8)
 * @returns {Promise<File>} - 압축/리사이징이 완료된 새로운 File 객체
 */
export function resizeAndCompressImage(file, maxDimension = 1000, quality = 0.8) {
  return new Promise((resolve, reject) => {
    // 이미지 파일이 아니면 원본 그대로 즉시 승인 반환
    if (!file.type.startsWith('image/')) {
      return resolve(file);
    }

    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        // 1000px 이하 저해상도 이미지는 업사이징 방지를 위해 바로 원본 리턴
        if (width <= maxDimension && height <= maxDimension) {
          return resolve(file);
        }

        // 비율 유지 다운사이징 계산
        if (width > height) {
          if (width > maxDimension) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          }
        } else {
          if (height > maxDimension) {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
        }

        // Canvas 버퍼를 JPEG 80% 압축 Blob으로 추출
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              return reject(new Error('Canvas to Blob conversion failed'));
            }
            // 기존 파일명 확장자를 .jpg로 보정 및 새로운 File 객체 래핑
            const newName = file.name.replace(/\.[^/.]+$/, "") + ".jpg";
            const compressedFile = new File([blob], newName, {
              type: 'image/jpeg',
              lastModified: Date.now()
            });
            resolve(compressedFile);
          },
          'image/jpeg',
          quality
        );
      };
      img.onerror = (err) => reject(err);
    };
    reader.onerror = (err) => reject(err);
  });
}

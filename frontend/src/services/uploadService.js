/**
 * HTML5 Canvas를 이용해 이미지를 가로 최대 1000px로 축소하고 JPEG Blob으로 변환합니다.
 * - 헌법 제V조 PWA 사양 수호: 전송 대역폭 절감 및 서버 리사이징 연산 부하 경감을 위해
 *   업로드 직전 클라이언트단 Canvas API를 통해 가로 최대 1000px 1차 압축을 강제합니다.
 * @param {File} file - 업로드할 원본 이미지 파일
 * @returns {Promise<Blob|File>} - 압축된 이미지 Blob (PDF 등은 원본 파일 그대로 반환)
 */
import { resizeAndCompressImage } from '../utils/imageResizer';

/**
 * HTML5 Canvas를 이용해 이미지를 가로 최대 1000px로 축소하고 JPEG Blob으로 변환합니다.
 * - 헌법 제V조 PWA 사양 수호: 전송 대역폭 절감 및 서버 리사이징 연산 부하 경감을 위해
 *   업로드 직전 클라이언트단 Canvas API를 통해 가로 최대 1000px 1차 압축을 강제합니다.
 * @param {File} file - 업로드할 원본 이미지 파일
 * @returns {Promise<File|Blob>} - 압축된 이미지 파일
 */
export async function compressImage(file) {
  return resizeAndCompressImage(file);
}

/**
 * 압축된 영수증 파일을 API 서버에 동기 POST 업로드 요청합니다.
 * @param {File|Blob} file - 압축 처리된 영수증 파일/Blob
 * @param {string} fileName - 원본 파일명
 * @returns {Promise<Object>} - API 응답 JSON
 */
export async function uploadReceiptApi(file, fileName) {
  const formData = new FormData()
  formData.append('file', file, fileName)

  // Django CORS 헤더 및 세션 세팅 연동 통신
  const response = await fetch('/api/v1/receipts/upload/', {
    method: 'POST',
    body: formData,
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.message || '영수증 업로드 처리 중 에러가 발생했습니다.')
  }

  return response.json()
}

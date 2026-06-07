import io

from django.core.files.uploadedfile import UploadedFile
from PIL import Image


class ImageProcessor:
    """
    [T012] [US1] Pillow 모듈을 활용한 WebP 2차 이미지 변환 및 압축 유틸리티
    """

    @staticmethod
    def process_image_to_webp(image_file: UploadedFile, quality: int = 80) -> io.BytesIO:
        """
        수신된 이미지 파일을 WebP 포맷(지정된 quality)으로 변환하여 메모리 버퍼로 반환합니다.
        RGBA/투명도 모드 이미지가 들어올 경우를 대비해 RGB로 변환 후 압축합니다.
        """
        # 1. Pillow Image로 로드
        img = Image.open(image_file)

        # 2. 투명도 채널(RGBA, LA, P)이 있을 경우 흰색 배경의 RGB로 변환하여 에러 방어
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGB", img.size, (255, 255, 255))
            # 알파 채널 분리 후 마스크로 활용하여 합성
            alpha = img.convert("RGBA").split()[3]
            background.paste(img.convert("RGBA"), mask=alpha)
            img = background
        else:
            img = img.convert("RGB")

        # 3. 메모리 내에서 WebP 포맷으로 압축 저장
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="WEBP", quality=quality)
        output_buffer.seek(0)

        return output_buffer


"""이미지에서 한국어와 영어 텍스트를 추출한다."""

import easyocr
import numpy as np
import torch

from PIL import Image, ImageOps


class OCRExtractor:
    def __init__(self, gpu=None, min_confidence=0.3):
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence는 0~1 사이여야 합니다.")

        if gpu is None:
            gpu = torch.cuda.is_available()

        self.min_confidence = min_confidence

        self.reader = easyocr.Reader(
            ['ko', 'en'],
            gpu=gpu
        )

    def extract(self, image):
        """PIL 이미지에서 텍스트를 추출하여 문자열로 반환한다."""
        if not isinstance(image, Image.Image):
            raise TypeError("PIL Image 객체가 필요합니다.")

        image = ImageOps.exif_transpose(image)
        image = image.convert('RGB')

        # EasyOCR의 NumPy 컬러 이미지 입력 형식에 맞춰 BGR로 변환
        image_array = np.asarray(image)[:, :, ::-1].copy()

        results = self.reader.readtext(
            image_array,
            detail=1,
            paragraph=False
        )

        texts = []

        for _, text, confidence in results:
            text = text.strip()

            if text and confidence >= self.min_confidence:
                texts.append(text)

        return '\n'.join(texts)

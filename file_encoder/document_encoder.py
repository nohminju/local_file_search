
from file_encoder.image_encoder import ImageEncoder


class DocumentEncoder:
    """PDF 페이지와 PPT 슬라이드의 이미지 임베딩"""

    def __init__(self, image_encoder=None):
        self.image_encoder = image_encoder or ImageEncoder()

    def encode(self, image):
        """페이지 또는 슬라이드 한 장 임베딩"""
        return self.image_encoder.encode(image)

    def encode_batch(self, images):
        """여러 페이지 또는 슬라이드 임베딩"""
        return self.image_encoder.encode_batch(images)

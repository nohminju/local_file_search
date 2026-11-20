
from file_encoder.image_encoder import ImageEncoder


class DocumentEncoder:
    """문서 내부에서 추출한 그림에 공통 ImageEncoder를 연결하는 호환 래퍼"""

    def __init__(self, image_encoder=None):
        self.image_encoder = image_encoder or ImageEncoder()

    def encode(self, image):
        """문서 내부 그림 한 장 임베딩"""
        return self.image_encoder.encode(image)

    def encode_batch(self, images):
        """문서 내부 그림 여러 장 임베딩"""
        return self.image_encoder.encode_batch(images)

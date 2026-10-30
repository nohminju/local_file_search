
import numpy as np
import open_clip
import torch
from PIL import Image, ImageOps


class ImageEncoder:
    """PIL 이미지를 OpenCLIP으로 512차원 벡터로 변환"""

    def __init__(
        self,
        model_name="xlm-roberta-base-ViT-B-32",
        pretrained="laion5b_s13b_b90k",
        device=None,
        batch_size=8
    ):
        if batch_size < 1:
            raise ValueError("batch_size는 1 이상이어야 합니다.")

        # CPU 또는 GPU 설정
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model_name = model_name
        self.pretrained = pretrained
        self.batch_size = batch_size

        # OpenCLIP 모델과 전처리 기능 불러오기
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
            device=self.device
        )

        self.model.eval()
        self.embedding_dim = self.model.visual.output_dim

        if self.embedding_dim != 512:
            raise ValueError(
                f"512차원 모델이 필요합니다. 현재 모델: {self.embedding_dim}차원"
            )

    def _preprocess_image(self, image):
        """PIL 이미지를 OpenCLIP 입력 형태로 전처리"""
        if not isinstance(image, Image.Image):
            raise TypeError("PIL 이미지 객체를 전달해야 합니다.")

        # 이미지 방향 보정 및 RGB 변환
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")

        return self.preprocess(image)

    def encode(self, image):
        """이미지 한 장을 512차원 float32 벡터로 변환"""
        image_tensor = self._preprocess_image(image)
        image_tensor = image_tensor.unsqueeze(0).to(self.device)

        with torch.inference_mode():
            embedding = self.model.encode_image(
                image_tensor,
                normalize=True
            )

        return embedding.squeeze(0).cpu().numpy().astype(np.float32)

    def encode_batch(self, images):
        """여러 PIL 이미지를 Batch로 임베딩"""
        images = list(images)
        vectors = []

        for start in range(0, len(images), self.batch_size):
            batch_images = images[start:start + self.batch_size]

            # 여러 이미지를 전처리한 뒤 하나의 Batch로 묶기
            batch_tensors = [
                self._preprocess_image(image)
                for image in batch_images
            ]

            batch = torch.stack(batch_tensors).to(self.device)

            with torch.inference_mode():
                embeddings = self.model.encode_image(
                    batch,
                    normalize=True
                )

            vectors.append(
                embeddings.cpu().numpy().astype(np.float32)
            )

        if vectors:
            return np.concatenate(vectors, axis=0)

        return np.empty((0, 512), dtype=np.float32)
        
    def encode_with_crops(self, image): ##테스트 필요
        """전체 이미지와 4개 영역을 각각 임베딩"""
        if not isinstance(image, Image.Image):
            raise TypeError("PIL 이미지 객체를 전달해야 합니다.")

        width, height = image.size

        if width < 2 or height < 2:
            return self.encode_batch([image])

        mid_x = width // 2
        mid_y = height // 2

        images = [
            image,  # 전체 이미지
            image.crop((0, 0, mid_x, mid_y)),        # 왼쪽 위
            image.crop((mid_x, 0, width, mid_y)),     # 오른쪽 위
            image.crop((0, mid_y, mid_x, height)),    # 왼쪽 아래
            image.crop((mid_x, mid_y, width, height)) # 오른쪽 아래
        ]

        return self.encode_batch(images)


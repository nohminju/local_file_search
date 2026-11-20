"""전체·부분 이미지 벡터의 형태와 FAISS 연결 검증. 실제 모델 가중치는 사용하지 않는다."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np
import torch
from PIL import Image

from database.faiss import FaissManager
from file_encoder.image_encoder import ImageEncoder


class ImageCropTests(unittest.TestCase):
    def make_encoder(self):
        encoder = object.__new__(ImageEncoder)
        encoder.device = torch.device('cpu')
        encoder.batch_size = 2
        encoder.preprocess = Mock(side_effect=lambda image: torch.ones(3, 2, 2))
        encoder.model = Mock()
        encoder.model.encode_image.side_effect = lambda batch, normalize: torch.ones(len(batch), 512) / (512 ** 0.5)
        return encoder

    def test_odd_size_crops_keep_original_and_cover_all_quadrants(self):
        encoder = self.make_encoder()
        encoder.encode_batch = Mock(return_value=np.zeros((5, 512), dtype=np.float32))
        image = Image.new('RGB', (5, 7))
        image.putpixel((4, 6), (255, 0, 0))
        vectors = encoder.encode_with_crops(image)
        views = encoder.encode_batch.call_args.args[0]
        self.assertIs(views[0], image)
        self.assertEqual([view.size for view in views], [(5, 7), (2, 3), (3, 3), (2, 4), (3, 4)])
        self.assertEqual(views[-1].getpixel((2, 3)), (255, 0, 0))
        self.assertEqual(vectors.shape, (5, 512))

    def test_tiny_images_keep_only_one_vector(self):
        encoder = self.make_encoder()
        for size in [(1, 1), (1, 7), (7, 1)]:
            with self.subTest(size=size):
                vectors = encoder.encode_with_crops(Image.new('RGB', size))
                self.assertEqual(vectors.shape, (1, 512))
                self.assertEqual(vectors.dtype, np.float32)

    def test_non_image_input_is_rejected(self):
        encoder = self.make_encoder()
        with self.assertRaises(TypeError):
            encoder.encode_with_crops('photo.jpg')

    def test_crop_vectors_index_with_matching_metadata_count(self):
        encoder = self.make_encoder()
        vectors = encoder.encode_with_crops(Image.new('RGB', (5, 7)))
        self.assertEqual(vectors.shape, (5, 512))
        self.assertEqual(vectors.dtype, np.float32)
        self.assertEqual(encoder.model.encode_image.call_count, 3)
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-6)
        chunk = SimpleNamespace(file_name='cat.jpg', file_path='/cat.jpg', page_number=1)
        index = FaissManager()
        with self.assertRaises(ValueError):
            index.add_images(vectors, [chunk])
        index.add_images(vectors, [chunk] * len(vectors))
        self.assertEqual(index.indices['img'].ntotal, 5)
        hits = index.search_images(vectors[0], top_k=5)
        self.assertEqual({hit['chunk']['file_path'] for hit in hits}, {'/cat.jpg'})

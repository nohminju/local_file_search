"""최신 main의 OpenCLIP·FAISS·파일명 규격을 검증한다. 가중치는 받지 않는다."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import torch

from database.faiss import FaissManager
from file_loader.document_loader import DocumentLoader
from similarity.document_embedder import DocumentEmbedder


class MainIntegrationTests(unittest.TestCase):
    def test_original_text_api_preserves_rows_and_query_dimension(self):
        model = Mock()
        model.encode_text.side_effect = lambda tokens: tokens.float()
        tokenizer = Mock(side_effect=lambda texts: torch.tensor([[3., 4.]] * len(texts)))
        with patch('similarity.document_embedder.torch.cuda.is_available', return_value=False), \
             patch('similarity.document_embedder.open_clip.create_model_and_transforms') as load:
            embedder = DocumentEmbedder(model=model, tokenizer=tokenizer)
            chunks = [SimpleNamespace(text=f'page {i}') for i in range(5)]
            vectors = embedder.embed_chunks(chunks)
            self.assertEqual([len(call.args[0]) for call in tokenizer.call_args_list], [5])
            self.assertEqual(vectors.shape, (5, 2))
            self.assertEqual(vectors.dtype, np.float32)
            np.testing.assert_allclose(vectors, [[0.6, 0.8]] * 5)
            self.assertEqual(embedder.encode_query('query').shape, (1, 2))
            self.assertIsNone(embedder.encode_query(' '))
            self.assertIsNone(embedder.embed_chunks([SimpleNamespace(text=' ')]))
            load.assert_not_called()


    def test_faiss_optional_floor_preserves_raw_scores_for_both_indices(self):
        index = FaissManager(2, 2)
        chunks = [SimpleNamespace(file_name='a', file_path='/a', page_number=1),
                  SimpleNamespace(file_name='b', file_path='/b', page_number=1)]
        for add, search in ((index.add_documents, index.search_documents),
                            (index.add_images, index.search_images)):
            add([[1., 0.], [0., 1.]], chunks)
            self.assertEqual(len(search([[1., 0.]], min_score=None)), 2)
            hits = search([[1., 0.]], min_score=0.5)
            self.assertEqual(len(hits), 1)
            self.assertAlmostEqual(hits[0]['score'], 1.)

    def test_loader_normalizes_url_encoded_decomposed_korean_name(self):
        self.assertEqual(DocumentLoader()._get_clean_filename('%E1%84%80%E1%85%A1.pdf'), '가.pdf')

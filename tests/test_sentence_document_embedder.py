"""문장 모델 주입·정규화·검색어 일치 규격을 가중치 없이 확인한다."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np

from connection.sentence_document_embedder import SentenceDocumentEmbedder


class SentenceDocumentEmbedderTests(unittest.TestCase):
    def test_same_model_encodes_body_and_query_with_normalization(self):
        model = Mock()
        model.encode.side_effect = [np.array([[1., 0.], [0., 1.]]), np.array([[0., 1.]])]
        with patch('connection.sentence_document_embedder.SentenceTransformer') as load:
            encoder = SentenceDocumentEmbedder(model=model, batch_size=4)
            chunks = [SimpleNamespace(text=' first '), SimpleNamespace(text=' '),
                      SimpleNamespace(text='second')]
            vectors = encoder.embed_chunks(chunks)
            results = encoder.search(' second ', top_k=1)
            self.assertEqual(vectors.shape, (2, 2))
            self.assertEqual(vectors.dtype, np.float32)
            self.assertIs(results[0]['chunk'], chunks[2])
            self.assertAlmostEqual(results[0]['score'], 1.)
            self.assertEqual(model.encode.call_args_list[0].args[0], ['first', 'second'])
            model.encode.assert_called_with(['second'], batch_size=4, convert_to_numpy=True,
                                            normalize_embeddings=True, show_progress_bar=False)
            load.assert_not_called()
            model.eval.assert_called_once()

    def test_empty_input_does_not_call_model(self):
        encoder = SentenceDocumentEmbedder(model=Mock())
        self.assertIsNone(encoder.embed_chunks([SimpleNamespace(text=' ')]))
        self.assertIsNone(encoder.encode_query(' '))
        self.assertEqual(encoder.search('query'), [])
        encoder.model.encode.assert_not_called()

    def test_invalid_batch_size_does_not_load_model(self):
        with patch('connection.sentence_document_embedder.SentenceTransformer') as load:
            with self.assertRaises(ValueError):
                SentenceDocumentEmbedder(batch_size=0)
            load.assert_not_called()

"""모델 재로딩 방지와 새 입력 인코더의 2차원 반환 규격을 확인한다."""
import unittest
from unittest.mock import Mock, patch

import torch

from app import build_service
from query_encoder.text_encoder import KoreanTextEncoder


class SharedTextEncoderTests(unittest.TestCase):
    def test_injected_model_handles_single_and_multiple_texts(self):
        model = Mock()
        model.encode_text.side_effect = lambda tokens: tokens.float()
        tokenizer = Mock(side_effect=lambda texts: torch.tensor([[3, 4]] * len(texts)))
        with patch('query_encoder.text_encoder.torch.cuda.is_available', return_value=False), \
             patch('query_encoder.text_encoder.open_clip.create_model_and_transforms') as load:
            encoder = KoreanTextEncoder(model=model, tokenizer=tokenizer)
            single = encoder.encode_text('고양이')
            batch = encoder.encode_text(['고양이', '강아지'])

        self.assertIs(encoder.model, model)
        self.assertEqual(single.shape, (1, 2))
        self.assertEqual(batch.shape, (2, 2))
        torch.testing.assert_close(torch.from_numpy(single), torch.tensor([[0.6, 0.8]]))
        load.assert_not_called()
        model.eval.assert_called_once()

    def test_factory_passes_image_model_and_tokenizer_to_query_encoder(self):
        with patch('app.ImageEncoder') as image_class, \
             patch('app.KoreanTextEncoder') as text_class, \
             patch('app.open_clip.get_tokenizer') as tokenizer, \
             patch('app.OpenCLIPDocumentEmbedder') as document_class, patch('app.Repository'), patch('app.FaissManager') as index_class:
            service = build_service(document_backend='openclip')
            try:
                text_class.assert_called_once_with(
                    model=image_class.return_value.model,
                    tokenizer=tokenizer.return_value,
                )
                self.assertIs(service.document_encoder.image_encoder, service.image_encoder)
                self.assertIs(service.query_encoder, text_class.return_value)
                image_class.assert_called_once()
                self.assertIs(service.vector_index, index_class.return_value)
                document_class.assert_called_once_with(
                    model=image_class.return_value.model,
                    tokenizer=text_class.return_value.tokenizer,
                )
                index_class.assert_called_once_with(doc_dim=512, img_dim=512)
            finally:
                service.session_directory.cleanup()


    def test_default_factory_uses_separate_sentence_model_and_matching_dimensions(self):
        with patch('app.ImageEncoder') as image_class, \
             patch('app.KoreanTextEncoder'), patch('app.open_clip.get_tokenizer'), \
             patch('app.DocumentEmbedder') as sentence_class, \
             patch('app.DocumentTextPreparer') as prepare_class, \
             patch('app.OpenCLIPDocumentEmbedder') as clip_class, \
             patch('app.Repository'), patch('app.FaissManager') as index_class:
            service = build_service()
            try:
                sentence_class.assert_called_once_with()
                clip_class.assert_not_called()
                self.assertIs(service.document_embedder, sentence_class.return_value)
                self.assertIsNot(service.document_embedder.model, image_class.return_value.model)
                index_class.assert_called_once_with(doc_dim=768, img_dim=512)
                prepare_class.assert_called_once_with(sentence_class.return_value.model.tokenizer,
                                                       sentence_class.return_value.model.max_seq_length)
                self.assertIs(service.text_preparer, prepare_class.return_value)
            finally:
                service.session_directory.cleanup()

    def test_invalid_text_backend_is_rejected_before_loading_models(self):
        with patch('app.ImageEncoder') as load:
            with self.assertRaises(ValueError):
                build_service(document_backend='unknown')
            load.assert_not_called()

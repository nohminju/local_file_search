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

    def test_factory_shares_image_model_and_keeps_body_model_separate(self):
        with patch('app.ImageEncoder') as image_class, \
             patch('app.KoreanTextEncoder') as text_class, \
             patch('app.open_clip.get_tokenizer') as tokenizer, \
             patch('app.SentenceDocumentEmbedder') as sentence_class, \
             patch('app.DocumentTextPreparer') as prepare_class, \
             patch('app.Repository'), patch('app.FaissManager') as index_class:
            service = build_service()
            try:
                text_class.assert_called_once_with(model=image_class.return_value.model,
                                                   tokenizer=tokenizer.return_value)
                sentence_class.assert_called_once_with()
                self.assertIs(service.document_embedder, sentence_class.return_value)
                self.assertIsNot(service.document_embedder.model, image_class.return_value.model)
                self.assertIs(service.document_encoder.image_encoder, service.image_encoder)
                self.assertIs(service.query_encoder, text_class.return_value)
                image_class.assert_called_once()
                index_class.assert_called_once_with(doc_dim=768, img_dim=512)
                prepare_class.assert_called_once_with(sentence_class.return_value.model.tokenizer,
                                                       sentence_class.return_value.model.max_seq_length)
                self.assertIs(service.text_preparer, prepare_class.return_value)
                from app import translate_ko_to_en
                self.assertIs(service.image_query_translator, translate_ko_to_en)
                self.assertIsNone(service.document_query_translator)
            finally:
                service.session_directory.cleanup()

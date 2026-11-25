"""검색 모드별 번역 주입과 원문 대체를 검증한다."""
import unittest
from unittest.mock import Mock
from connection.service import DocumentSearch


class ImageTranslationTests(unittest.TestCase):
    def make_service(self, translator, document_translator=None):
        index=Mock()
        index.chunk_metas={'doc':[{}],'img':[{}]}
        index.search_documents.return_value=[]
        index.search_images.return_value=[]
        body=Mock()
        image_query=Mock()
        return DocumentSearch(Mock(),Mock(),Mock(),body,image_query,Mock(),index,
                              image_query_translator=translator,
                              document_query_translator=document_translator)

    def test_document_mode_encodes_korean_translation(self):
        translate=Mock(return_value='고양이')
        service=self.make_service(None, translate)
        service.search(' cat ',mode='documents')
        translate.assert_called_once_with('cat')
        service.document_embedder.encode_query.assert_called_once_with('고양이')
        service.query_encoder.encode_text.assert_not_called()

    def test_hybrid_uses_independent_translators_once(self):
        image=Mock(return_value='cat')
        body=Mock(return_value='고양이')
        service=self.make_service(image, body)
        service.search('cat')
        image.assert_called_once_with('cat')
        body.assert_called_once_with('cat')
        service.document_embedder.encode_query.assert_called_once_with('고양이')
        service.query_encoder.encode_text.assert_called_once_with('cat')

    def test_document_translation_failure_or_invalid_result_uses_original(self):
        for translator in (Mock(side_effect=RuntimeError('offline')),
                           *(Mock(return_value=value) for value in ('', ' ', None, 123))):
            with self.subTest(translator=translator):
                service=self.make_service(None, translator)
                service.search('cat',mode='documents')
                service.document_embedder.encode_query.assert_called_once_with('cat')

    def test_empty_document_index_query_and_limit_skip_translation(self):
        translate=Mock()
        service=self.make_service(None, translate)
        service.search('',mode='documents')
        service.search('cat',top_k=0,mode='documents')
        service.vector_index.chunk_metas['doc']=[]
        service.search('cat',mode='documents')
        translate.assert_not_called()

    def test_image_mode_encodes_translation(self):
        translate=Mock(return_value='a lying cat')
        service=self.make_service(translate)
        service.search(' 누워있는 고양이 ',mode='images')
        translate.assert_called_once_with('누워있는 고양이')
        service.query_encoder.encode_text.assert_called_once_with('a lying cat')
        service.document_embedder.encode_query.assert_not_called()

    def test_document_mode_preserves_korean_and_never_translates(self):
        translate=Mock(return_value='persona')
        service=self.make_service(translate)
        service.search('페르소나 경로맵',mode='documents')
        translate.assert_not_called()
        service.document_embedder.encode_query.assert_called_once_with('페르소나 경로맵')
        service.query_encoder.encode_text.assert_not_called()

    def test_hybrid_sends_original_to_body_and_english_only_to_image(self):
        translate=Mock(return_value='cat')
        service=self.make_service(translate)
        service.search('고양이')
        translate.assert_called_once_with('고양이')
        service.document_embedder.encode_query.assert_called_once_with('고양이')
        service.query_encoder.encode_text.assert_called_once_with('cat')

    def test_translation_exception_falls_back_to_original(self):
        service=self.make_service(Mock(side_effect=RuntimeError('offline')))
        service.search('고양이',mode='images')
        service.query_encoder.encode_text.assert_called_once_with('고양이')

    def test_blank_or_invalid_translation_falls_back(self):
        for value in ('', '   ', None, 123):
            with self.subTest(value=value):
                service=self.make_service(Mock(return_value=value))
                service.search('고양이',mode='images')
                service.query_encoder.encode_text.assert_called_once_with('고양이')

    def test_empty_query_limit_and_empty_image_index_never_translate(self):
        translate=Mock(return_value='cat')
        service=self.make_service(translate)
        service.search('',mode='images')
        service.search('고양이',top_k=0,mode='images')
        service.vector_index.chunk_metas['img']=[]
        service.search('고양이',mode='images')
        translate.assert_not_called()

    def test_no_translator_preserves_raw_query(self):
        service=self.make_service(None)
        service.search('고양이',mode='images')
        service.query_encoder.encode_text.assert_called_once_with('고양이')


if __name__=='__main__': unittest.main()

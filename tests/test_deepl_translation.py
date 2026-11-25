"""팀원 번역기는 수정하지 않고 외부 요청 없이 양방향 계약을 검증한다."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from connection import translator


class DeepLTranslationTests(unittest.TestCase):
    def setUp(self):
        translator.translate_ko_to_en.cache_clear()
        translator.translate_en_to_ko.cache_clear()
        self.addCleanup(translator.translate_ko_to_en.cache_clear)
        self.addCleanup(translator.translate_en_to_ko.cache_clear)

    def test_korean_to_english_and_cache(self):
        client = Mock()
        client.translate_text.return_value = SimpleNamespace(text='cat')
        with patch.object(translator, '_get_translator', return_value=client):
            self.assertEqual(translator.translate_ko_to_en('고양이'), 'cat')
            self.assertEqual(translator.translate_ko_to_en('고양이'), 'cat')
        client.translate_text.assert_called_once_with('고양이', source_lang='KO', target_lang='EN-US')

    def test_english_to_korean_and_single_word_retry(self):
        client = Mock()
        client.translate_text.side_effect = [SimpleNamespace(text='CAT'), SimpleNamespace(text='고양이')]
        with patch.object(translator, '_get_translator', return_value=client):
            self.assertEqual(translator.translate_en_to_ko('CAT'), '고양이')
        self.assertEqual(client.translate_text.call_args_list[0].args, ('cat',))
        client.translate_text.assert_called_with('a cat', source_lang='EN', target_lang='KO')

    def test_already_target_language_or_blank_skips_api(self):
        with patch.object(translator, '_get_translator') as get_client:
            self.assertEqual(translator.translate_ko_to_en(' cat '), 'cat')
            self.assertEqual(translator.translate_en_to_ko(' 고양이 '), '고양이')
            self.assertEqual(translator.translate_ko_to_en(''), '')
            self.assertEqual(translator.translate_en_to_ko(' '), ' ')
        get_client.assert_not_called()

    def test_missing_key_or_request_failure_preserves_original(self):
        for function, query in ((translator.translate_ko_to_en, '고양이'),
                                (translator.translate_en_to_ko, 'cat')):
            with self.subTest(query=query), patch.object(
                    translator, '_get_translator', side_effect=RuntimeError('unavailable')):
                self.assertEqual(function(query), query)

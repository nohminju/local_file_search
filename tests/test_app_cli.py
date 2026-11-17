"""콘솔에서 모드 질문 없이 기본 검색을 호출하는지 검증한다."""
import unittest
from unittest.mock import Mock, patch

from app import main


class ConsoleSearchTests(unittest.TestCase):
    def test_query_searches_without_mode_prompt(self):
        service = Mock()
        service.analyze.return_value = ([], [])
        service.search.return_value = []
        with patch('app.Path.is_dir', return_value=True), \
             patch('app.build_service', return_value=service), \
             patch('builtins.input', side_effect=['files', '찾을 내용', '']) as read, \
             patch('builtins.print'):
            main()
        self.assertEqual(read.call_count, 3)
        service.analyze.assert_called_once_with('files')
        service.search.assert_called_once_with('찾을 내용')

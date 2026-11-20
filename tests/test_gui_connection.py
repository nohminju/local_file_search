"""창을 띄우지 않고 GUI의 작업 큐와 결과 처리를 검증한다."""
from types import SimpleNamespace
import queue
import unittest
from unittest.mock import Mock, patch

from connection.service import SearchResult

from gui.window import DocumentSearchApp


class GuiConnectionTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(DocumentSearchApp)
        app.folder = 'documents'
        app.busy = False
        app.service = None
        app.messages = queue.Queue()
        app.tasks = queue.Queue()
        for name in ('service_factory', 'status', 'folder_button', 'analyze_button',
                     'search_button', 'show_message', 'show_results', 'after',
                     'query_entry'):
            setattr(app, name, Mock())
        app.query_entry.get.return_value = '검색 문장'
        return app

    def test_successful_analysis_keeps_same_service_for_search(self):
        app = self.make_app()
        service = Mock()
        service.analyze.return_value = ([], [])
        app.service_factory.return_value = service
        app.analyze()
        self.assertTrue(app.busy)
        self.assertIsNone(app.service)
        job, args = app.tasks.get_nowait()
        app.messages.put((job, job(*args), None))
        app.poll_messages()
        self.assertIs(app.service, service)
        self.assertFalse(app.busy)
        service.analyze.assert_called_once_with('documents')
        app.search_button.configure.assert_called_with(state='normal')

    def test_failed_analysis_discards_previous_service(self):
        app = self.make_app()
        app.service = Mock()
        app.analyze()
        job, _ = app.tasks.get_nowait()
        app.messages.put((job, None, RuntimeError('model failed')))
        app.poll_messages()
        self.assertIsNone(app.service)
        self.assertFalse(app.busy)
        app.search_button.configure.assert_called_with(state='disabled')
        app.status.configure.assert_called_with(text='오류: model failed')

    def test_search_without_mode_displays_worker_results(self):
        app = self.make_app()
        app.service = Mock()
        app.service.search.return_value = []
        app.search()
        job, args = app.tasks.get_nowait()
        self.assertEqual(args, ('검색 문장',))
        self.assertTrue(app.busy)
        app.messages.put((job, job(*args), None))
        app.poll_messages()
        app.service.search.assert_called_once_with('검색 문장')
        app.show_results.assert_called_once_with([])
        self.assertFalse(app.busy)

    def test_busy_state_blocks_duplicate_jobs(self):
        app = self.make_app()
        app.service = Mock()
        app.busy = True
        app.analyze()
        app.search()
        self.assertTrue(app.tasks.empty())

    def test_result_card_shows_original_score_and_source(self):
        app = self.make_app()
        app.results_frame = Mock()
        app.clear_results = Mock()
        info = SimpleNamespace(file_name='cat.jpg', file_path='/cat.jpg')
        result = SearchResult(info, 0.260748, 'images', 0.075935, None, 0.260748)
        with patch('gui.window.ctk.CTkFrame'), patch('gui.window.ctk.CTkLabel') as label, \
             patch('gui.window.ctk.CTkButton'), patch('gui.window.ctk.CTkFont'):
            DocumentSearchApp.show_results(app, [result])
        texts = [call.kwargs.get('text', '') for call in label.call_args_list]
        self.assertTrue(any('이미지 유사도 0.2607' in text for text in texts))
        self.assertFalse(any('0.0759' in text for text in texts))

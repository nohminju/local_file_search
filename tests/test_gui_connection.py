"""창을 띄우지 않고 GUI의 작업 큐와 결과 처리를 검증한다."""
from types import SimpleNamespace
import queue
import unittest
from unittest.mock import Mock, patch

from connection.service import SearchResult, ScoredFile

from gui.window import DocumentSearchApp


class GuiConnectionTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(DocumentSearchApp)
        app.folder = 'documents'
        app.active_search_mode = 'hybrid'
        app.busy = False
        app.service = None
        app.messages = queue.Queue()
        app.tasks = queue.Queue()
        for name in ('service_factory', 'status', 'folder_button', 'analyze_button',
                     'search_button', 'show_message', 'show_results', 'after',
                     'query_entry', 'mode_selector'):
            setattr(app, name, Mock())
        app.query_entry.get.return_value = '검색 문장'
        app.mode_selector.get.return_value = '통합검색'
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
        self.assertEqual(args, ('검색 문장', 'hybrid'))
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
        result = SearchResult(info, 0.260748, 'images', None, 0.260748)
        with patch('gui.window.ctk.CTkFrame'), patch('gui.window.ctk.CTkLabel') as label, \
             patch('gui.window.ctk.CTkButton'), patch('gui.window.ctk.CTkFont'):
            DocumentSearchApp.show_results(app, [result])
        texts = [call.kwargs.get('text', '') for call in label.call_args_list]
        self.assertTrue(any('이미지 유사도 0.2607' in text for text in texts))
        self.assertFalse(any('0.0759' in text for text in texts))


    def test_individual_modes_are_captured_on_main_thread_and_passed_to_worker(self):
        for label, mode in [('이미지 검색', 'images'), ('본문 검색', 'documents')]:
            with self.subTest(mode=mode):
                app = self.make_app()
                app.service = Mock()
                app.service.search.return_value = []
                app.mode_selector.get.return_value = label
                app.search()
                job, args = app.tasks.get_nowait()
                self.assertEqual(args, ('검색 문장', mode))
                app.messages.put((job, job(*args), None))
                app.poll_messages()
                app.service.search.assert_called_once_with('검색 문장', mode=mode)
                self.assertIn('하한 미적용', app.status.configure.call_args.kwargs['text'])

    def test_filename_is_displayed_but_score_source_is_body(self):
        app = self.make_app()
        app.results_frame = Mock()
        app.clear_results = Mock()
        info = SimpleNamespace(file_name='persona.pptx', file_path='/persona.pptx')
        with patch('gui.window.ctk.CTkFrame'), patch('gui.window.ctk.CTkLabel') as label, \
             patch('gui.window.ctk.CTkButton'), patch('gui.window.ctk.CTkFont'):
            DocumentSearchApp.show_results(app, [ScoredFile(info, 0.9, 'documents')])
        texts = [call.kwargs.get('text', '') for call in label.call_args_list]
        self.assertIn('persona.pptx', texts)
        self.assertTrue(any('본문 유사도 0.9000' in text for text in texts))
        self.assertFalse(any('파일명 유사도' in text or '재정렬' in text for text in texts))

    def test_busy_state_disables_mode_switch(self):
        app = self.make_app()
        app.set_busy(True)
        app.mode_selector.configure.assert_called_with(state='disabled')

"""창을 띄우지 않고 GUI의 작업 큐와 결과 처리를 검증한다."""
import queue
import unittest
from unittest.mock import Mock

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
                     'query_entry', 'mode'):
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

    def test_search_passes_selected_mode_and_displays_worker_results(self):
        app = self.make_app()
        app.service = Mock()
        app.service.search.return_value = []
        for label, mode in [('문서', 'documents'), ('이미지', 'images')]:
            app.mode.get.return_value = label
            app.search()
            job, args = app.tasks.get_nowait()
            self.assertTrue(app.busy)
            app.messages.put((job, job(*args), None))
            app.poll_messages()
            app.service.search.assert_called_with('검색 문장', mode=mode)
            app.show_results.assert_called_with([])
            self.assertFalse(app.busy)

    def test_busy_state_blocks_duplicate_jobs(self):
        app = self.make_app()
        app.service = Mock()
        app.busy = True
        app.analyze()
        app.search()
        self.assertTrue(app.tasks.empty())

import unittest
from unittest.mock import Mock

from gui.window import DocumentSearchApp


class GuiConnectionTests(unittest.TestCase):
    def make_app(self):
        app = object.__new__(DocumentSearchApp)
        app.root, app.folder, app.query, app.mode = Mock(), Mock(), Mock(), Mock()
        app.folder.get.return_value = 'documents'
        app.query.get.return_value = '검색 문장'
        app.service_factory, app.status, app.search_button, app.show_text = Mock(), Mock(), Mock(), Mock()
        app.service = None
        return app

    def test_successful_analysis_keeps_same_service_for_search(self):
        app = self.make_app()
        service = Mock()
        service.analyze.return_value = ([], [])
        app.service_factory.return_value = service
        app.analyze()
        self.assertIs(app.service, service)
        app.search_button.configure.assert_called_with(state='normal')

    def test_failed_analysis_discards_previous_service(self):
        app = self.make_app()
        app.service = Mock()
        app.service_factory.side_effect = RuntimeError('model failed')
        app.analyze()
        self.assertIsNone(app.service)
        app.search_button.configure.assert_called_with(state='disabled')

    def test_search_passes_selected_mode(self):
        app = self.make_app()
        app.service = Mock()
        app.service.search.return_value = []
        for label, mode in [('문서 본문', 'documents'), ('이미지 유사도 검색(임시 구현)', 'images')]:
            app.mode.get.return_value = label
            app.search()
            app.service.search.assert_called_with('검색 문장', mode=mode)

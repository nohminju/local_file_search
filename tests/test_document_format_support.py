"""지원 형식을 소스와 맞춰 확인한다. 미지원 형식을 지원한다고 표시하지 않는다."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from file_loader.document_loader import DocumentLoader, DocumentScanner


class DocumentFormatSupportTests(unittest.TestCase):
    def test_scanner_includes_pdf_pptx_but_not_ppt_hangul(self):
        with TemporaryDirectory() as folder:
            for suffix in ('.pdf', '.pptx', '.ppt', '.hwp', '.hwpx'):
                (Path(folder) / ('sample' + suffix)).write_bytes(b'extension check')
            suffixes = {Path(path).suffix for path in DocumentScanner(folder).scan_files()}
            self.assertEqual(suffixes, {'.pdf', '.pptx'})

    def test_unsupported_formats_do_not_call_pdf_or_pptx_parser(self):
        with TemporaryDirectory() as folder:
            loader = DocumentLoader()
            with patch.object(loader, 'load_pdf') as pdf, patch.object(loader, 'load_pptx') as pptx:
                for suffix in ('.ppt', '.hwp', '.hwpx'):
                    path = Path(folder) / ('sample' + suffix)
                    path.write_bytes(b'unsupported format')
                    self.assertEqual(loader.process_file(str(path)), [])
                pdf.assert_not_called()
                pptx.assert_not_called()

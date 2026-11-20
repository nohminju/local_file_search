from pathlib import Path
from types import SimpleNamespace
import unittest
from connection.text_preparation import DocumentTextPreparer
from file_loader.document_loader import DocumentChunk


class WordTokenizer:
    def num_special_tokens_to_add(self, pair=False):
        return 2

    def encode(self, text, **kwargs):
        return text.split()

    def decode(self, ids, **kwargs):
        return ' '.join(ids)


class TextPreparationTests(unittest.TestCase):
    def test_long_page_tail_is_indexed_with_overlap_and_page_preserved(self):
        text = ' '.join(f'word{i}' for i in range(19))
        chunk = DocumentChunk('a.pdf', '/a.pdf', 3, text, 'pdf')
        pieces = DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([chunk], [])
        self.assertEqual([len(c.text.split()) for c in pieces], [8, 8, 7])
        self.assertEqual(pieces[0].text.split()[-2:], pieces[1].text.split()[:2])
        self.assertIn('word18', pieces[-1].text)
        self.assertEqual(set(' '.join(c.text for c in pieces).split()), set(text.split()))
        self.assertTrue(all(c.page_number == 3 and c.file_path == '/a.pdf' and c.chunk_type == 'pdf' for c in pieces))
        self.assertEqual(chunk.text, text)

    def test_short_chunk_is_not_rewritten(self):
        chunk = DocumentChunk('a.pdf', '/a.pdf', 1, ' original text ', 'pdf')
        self.assertIs(DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([chunk], [])[0], chunk)

    def test_only_pdf_pptx_names_are_indexed_and_normalized(self):
        docs = [SimpleNamespace(file_path='/x/%E1%84%80%E1%85%A1_%ED%8E%98%EB%A5%B4%EC%86%8C%EB%82%98.pptx'),
                SimpleNamespace(file_path='/x/database.pdf'), SimpleNamespace(file_path='/x/cat.jpg')]
        chunks = DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([], docs)
        self.assertEqual([c.text for c in chunks], ['가 페르소나', 'database'])
        self.assertTrue(all(c.chunk_type == 'filename' and c.page_number == 0 for c in chunks))

    def test_invalid_window_or_overlap_is_rejected(self):
        for size, overlap in [(2, 0), (10, 8), (10, -1)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                DocumentTextPreparer(WordTokenizer(), size, overlap)

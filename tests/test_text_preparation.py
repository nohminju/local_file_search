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
        pieces = DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([chunk])
        self.assertEqual([len(c.text.split()) for c in pieces], [8, 8, 7])
        self.assertEqual(pieces[0].text.split()[-2:], pieces[1].text.split()[:2])
        self.assertIn('word18', pieces[-1].text)
        self.assertEqual(set(' '.join(c.text for c in pieces).split()), set(text.split()))
        self.assertTrue(all(c.page_number == 3 and c.file_path == '/a.pdf' and c.chunk_type == 'pdf' for c in pieces))
        self.assertEqual(chunk.text, text)

    def test_short_chunk_is_not_rewritten(self):
        chunk = DocumentChunk('a.pdf', '/a.pdf', 1, ' original text ', 'pdf')
        self.assertIs(DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([chunk])[0], chunk)

    def test_filename_and_path_never_enter_prepared_text(self):
        chunk = DocumentChunk('apple_persona.pptx', '/private/secret/apple_persona.pptx', 1, 'banana', 'pptx')
        chunks = DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([chunk])
        self.assertEqual([c.text for c in chunks], ['banana'])
        self.assertEqual(DocumentTextPreparer(WordTokenizer(), 10, overlap=2).prepare([]), [])
        self.assertNotIn('apple', chunks[0].text)

    def test_invalid_window_or_overlap_is_rejected(self):
        for size, overlap in [(2, 0), (10, 8), (10, -1)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                DocumentTextPreparer(WordTokenizer(), size, overlap)

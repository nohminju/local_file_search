"""실제 로더·SQLite와 팀원 검색 수식으로 연결을 검증한다. 모델 출력만 대역이다."""
from io import BytesIO
from pathlib import Path
import gc
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from pptx import Presentation
from pptx.util import Inches

from connection.service import DocumentSearch
from database.manager import Repository
from database.faiss import FaissManager
from file_loader.document_loader import DocumentLoader
from file_encoder.document_encoder import DocumentEncoder
from connection.sentence_document_embedder import SentenceDocumentEmbedder


class ModelOutput:
    def eval(self):
        return self

    def encode(self, texts, **kwargs):
        return np.array([[1., 0.] if 'apple' in text else [0., 1.] for text in texts])





class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(gc.collect)  # 팀원 DB의 원본 연결은 GC 전까지 남을 수 있다.
        self.folder = Path(self.directory.name)
        self.image_encoder = Mock()
        self.image_encoder.encode_batch.side_effect = lambda images: np.array([[0., 1.]] * len(images))
        self.document_encoder = Mock(wraps=DocumentEncoder(self.image_encoder))
        self.query_encoder = Mock()
        self.query_encoder.encode_text.return_value = np.array([[0., 1.]])
        self.embedder = SentenceDocumentEmbedder(model=Mock(wraps=ModelOutput()))
        self.repository = Repository(str(self.folder / 'metadata.db'))
        self.vector_index = FaissManager(doc_dim=2, img_dim=2)
        self.service = DocumentSearch(DocumentLoader(), self.image_encoder, self.document_encoder,
                                      self.embedder, self.query_encoder, self.repository, self.vector_index)

    def make_documents(self):
        writer = PdfWriter()
        for text in ('apple first page', 'apple second page'):
            page = writer.add_blank_page(width=300, height=300)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode())
            page[NameObject('/Contents')] = writer._add_object(stream)
        with (self.folder / 'apple.pdf').open('wb') as output:
            writer.write(output)
        picture = Image.new('RGB', (12, 12), 'yellow')
        picture.save(self.folder / 'photo.png')
        memory = BytesIO()
        picture.save(memory, format='PNG')
        memory.seek(0)
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'banana slide'
        slide.shapes.add_picture(memory, Inches(1), Inches(3), width=Inches(1))
        presentation.save(self.folder / 'banana.pptx')

    def test_routes_loaders_and_encoders_and_saves_each_file_once(self):
        self.make_documents()
        documents, failures = self.service.analyze(self.folder)
        self.assertEqual({d.file_name for d in documents}, {'apple.pdf', 'banana.pptx', 'photo.png'})
        self.assertEqual(failures, [])
        self.assertEqual(len(self.service.file_ids), 3)
        self.assertEqual(len(self.embedder.chunks), 3)
        self.document_encoder.encode_batch.assert_called_once()
        self.assertEqual(self.image_encoder.encode_batch.call_count, 2)
        self.assertEqual(self.vector_index.indices['doc'].ntotal, 3)
        self.assertEqual(self.vector_index.indices['img'].ntotal, 2)
        for file_id in self.service.file_ids.values():
            self.assertIsNotNone(self.repository.find_by_id(file_id))

    def test_document_search_deduplicates_pages_and_does_not_use_clip_query(self):
        self.make_documents()
        self.service.analyze(self.folder)
        results = self.service.search('apple query', mode='documents')
        self.assertEqual(results[0][0].file_name, 'apple.pdf')
        self.assertEqual(len([r for r in results if r[0].file_name == 'apple.pdf']), 1)
        self.query_encoder.encode_text.assert_not_called()
        self.embedder.model.encode.assert_called_with(['apple query'], batch_size=8, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        self.assertEqual(len(self.service.search('apple query', top_k=2, mode='documents')), 2)

    def test_image_search_uses_clip_query_and_returns_file_info(self):
        self.make_documents()
        self.service.analyze(self.folder)
        self.embedder.model.encode.reset_mock()
        results = self.service.search('yellow image', mode='images')
        self.assertEqual({info.file_name for info, score in results}, {'photo.png', 'banana.pptx'})
        self.assertTrue(all(abs(score - 1.0) < 1e-6 for info, score in results))
        self.query_encoder.encode_text.assert_called_once_with('yellow image')
        self.embedder.model.encode.assert_not_called()

    def test_image_search_deduplicates_chunks_before_limiting_files(self):
        self.make_documents()
        self.service.analyze(self.folder)
        chunk = next(c for c in self.vector_index.chunk_metas['img'] if c['file_name'] == 'photo.png')
        self.vector_index.add_images(
            [[1., 0.], [1., 0.]],
            [SimpleNamespace(**chunk), SimpleNamespace(**chunk)],
        )
        self.query_encoder.encode_text.return_value = np.array([[1., 0.]])
        results = self.service.search('yellow image', top_k=2, mode='images')
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0].file_name, 'photo.png')
        self.assertEqual([score for _, score in results], [1., 0.])

    def test_default_limit_is_five_files_and_can_be_overridden(self):
        for number in range(7):
            Image.new('RGB', (8, 8)).save(self.folder / f'photo{number}.png')
        self.service.analyze(self.folder)
        self.assertEqual(len(self.service.search('photo', mode='images')), 5)
        self.assertEqual(len(self.service.search('photo', top_k=7, mode='images')), 7)

    def test_image_only_analysis_leaves_document_index_empty(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'photo.png')
        self.service.analyze(self.folder)
        self.assertEqual(self.service.search('text', mode='documents'), [])
        self.assertEqual(len(self.service.search('photo', mode='images')), 1)

    def test_text_only_analysis_leaves_image_index_empty(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'apple'
        presentation.save(self.folder / 'text.pptx')
        self.service.analyze(self.folder)
        self.assertEqual(self.service.search('image', mode='images'), [])
        self.assertEqual(len(self.service.search('apple', mode='documents')), 1)

    def test_broken_file_is_reported_without_stopping_other_files(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'valid.png')
        (self.folder / 'empty.pdf').write_bytes(b'')
        documents, failures = self.service.analyze(self.folder)
        self.assertEqual([d.file_name for d in documents], ['valid.png'])
        self.assertEqual([p.name for p, reason in failures], ['empty.pdf'])
        self.assertEqual(self.service.search('본문 없음', mode='documents'), [])

    def test_model_error_is_not_saved_as_success(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'photo.png')
        self.image_encoder.encode_batch.side_effect = RuntimeError('model failed')
        self.repository.save = Mock(wraps=self.repository.save)
        with self.assertRaisesRegex(RuntimeError, 'model failed'):
            self.service.analyze(self.folder)
        self.repository.save.assert_not_called()

    def test_loader_permission_error_is_reported_and_other_files_continue(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'blocked.png')
        Image.new('RGB', (8, 8)).save(self.folder / 'valid.png')
        loader = self.service.loader

        def read_file(path):
            if Path(path).name == 'blocked.png':
                raise PermissionError('access denied')
            return loader.process_file(path)

        self.service.loader = Mock()
        self.service.loader.process_file.side_effect = read_file
        documents, failures = self.service.analyze(self.folder)
        self.assertEqual([info.file_name for info in documents], ['valid.png'])
        self.assertEqual([(path.name, reason) for path, reason in failures],
                         [('blocked.png', 'access denied')])
        self.assertEqual(self.vector_index.indices['img'].ntotal, 1)

    def test_pptx_multiple_images_use_document_encoder_and_one_file_result(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'apple slide'
        for index, color in enumerate(('red', 'blue')):
            picture = BytesIO()
            Image.new('RGB', (120, 120), color).save(picture, format='PNG')
            picture.seek(0)
            slide.shapes.add_picture(picture, Inches(index + 1), Inches(3), width=Inches(1))
        presentation.save(self.folder / 'pictures.pptx')
        documents, failures = self.service.analyze(self.folder)
        self.assertEqual(len(documents), 1)
        self.assertEqual(failures, [])
        self.assertEqual(len(self.embedder.chunks), 1)
        self.assertEqual(self.document_encoder.encode_batch.call_count, 1)
        self.assertEqual(len(self.document_encoder.encode_batch.call_args.args[0]), 2)
        self.assertEqual(self.vector_index.indices['doc'].ntotal, 1)
        self.assertEqual(self.vector_index.indices['img'].ntotal, 2)
        hits = self.service.search('picture', mode='images')
        self.assertEqual([info.file_name for info, _ in hits], ['pictures.pptx'])

    def test_pdf_embedded_image_uses_document_encoder(self):
        Image.new('RGB', (120, 120), 'blue').save(self.folder / 'scan.pdf', format='PDF')
        documents, failures = self.service.analyze(self.folder)
        self.assertEqual([info.file_name for info in documents], ['scan.pdf'])
        self.assertEqual(failures, [])
        self.document_encoder.encode_batch.assert_called_once()
        self.assertEqual(self.vector_index.indices['img'].ntotal, 1)
        self.assertEqual(self.service.search('text', mode='documents'), [])
        hits = self.service.search('blue image', mode='images')
        self.assertEqual([info.file_name for info, _ in hits], ['scan.pdf'])

    def test_empty_query_and_invalid_mode(self):
        self.assertEqual(self.service.search('   '), [])
        with self.assertRaises(ValueError):
            self.service.search('query', mode='unknown')


    def mock_hit(self, number, path, file_hash=None):
        return SimpleNamespace(file_id=number, file_path=path, file_hash=file_hash)













    def test_default_search_connects_real_loader_database_and_both_indices(self):
        self.make_documents()
        self.service.analyze(self.folder)
        results = self.service.search('apple query')
        self.assertEqual(results[0].file.file_name, 'apple.pdf')
        self.assertEqual({r.file.file_name for r in results}, {'apple.pdf', 'banana.pptx', 'photo.png'})
        self.assertTrue(all(r.score == 1.0 for r in results))
        self.assertEqual(results[0].source, 'documents')

    def test_hybrid_image_only_folder(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'photo.png')
        self.service.analyze(self.folder)
        results = self.service.search('photo')
        self.assertEqual([r.file.file_name for r in results], ['photo.png'])
        self.assertAlmostEqual(results[0].score, 1.0)

    def test_hybrid_text_only_folder(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'apple'
        presentation.save(self.folder / 'text.pptx')
        self.service.analyze(self.folder)
        self.assertEqual([r.file.file_name for r in self.service.search('apple')], ['text.pptx'])

    def test_empty_inputs_and_indices(self):
        self.assertEqual(self.service.search('query'), [])
        self.assertEqual(self.service.search_hybrid('   '), [])
        self.assertEqual(self.service.search_hybrid('query', top_k=0), [])


    def test_repeated_text_encoded_once_with_both_file_metadata_preserved(self):
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'apple same text'
        presentation.save(self.folder / 'a.pptx')
        presentation.save(self.folder / 'b.pptx')
        self.service.analyze(self.folder)
        self.embedder.model.encode.assert_called_once_with(['apple same text'], batch_size=8, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
        self.assertEqual(self.vector_index.indices['doc'].ntotal, 2)
        self.assertEqual({m['file_name'] for m in self.vector_index.chunk_metas['doc']}, {'a.pptx', 'b.pptx'})
        self.assertEqual(len(self.service.search('apple', mode='documents')), 2)

    def test_wrong_batch_count_is_not_associated_with_file_metadata(self):
        Image.new('RGB', (8, 8)).save(self.folder / 'photo.png')
        self.image_encoder.encode_batch.side_effect = lambda images: np.zeros((0, 2))
        self.repository.save = Mock(wraps=self.repository.save)
        with self.assertRaisesRegex(ValueError, '벡터 수와 청크 수'):
            self.service.analyze(self.folder)
        self.repository.save.assert_not_called()
        self.assertIsNone(self.vector_index.indices['img'])


    def test_filename_does_not_create_a_body_vector_or_change_raw_similarity(self):
        from connection.text_preparation import DocumentTextPreparer
        tokenizer = Mock()
        tokenizer.num_special_tokens_to_add.return_value = 2
        tokenizer.encode.side_effect = lambda text, **kwargs: text.split()
        tokenizer.decode.side_effect = lambda ids, **kwargs: ' '.join(ids)
        self.service.text_preparer = DocumentTextPreparer(tokenizer, 10, overlap=2)
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1)).text = 'banana'
        presentation.save(self.folder / 'apple_persona.pptx')
        self.service.analyze(self.folder)
        raw = self.service.search('apple', mode='documents')[0]
        self.assertEqual(raw.source, 'documents')
        self.assertEqual(raw[1], 0.)
        self.assertEqual(self.vector_index.indices['doc'].ntotal, 1)
        self.assertEqual([m['text'] for m in self.vector_index.chunk_metas['doc']], ['banana'])
        self.assertTrue(all(m.get('chunk_type') != 'filename' for m in self.vector_index.chunk_metas['doc']))

    def test_image_filename_does_not_create_a_fake_body_match(self):
        from connection.text_preparation import DocumentTextPreparer
        tokenizer = Mock()
        tokenizer.num_special_tokens_to_add.return_value = 2
        self.service.text_preparer = DocumentTextPreparer(tokenizer, 10, overlap=2)
        Image.new('RGB', (8, 8)).save(self.folder / 'apple.jpg')
        self.service.analyze(self.folder)
        self.assertIsNone(self.vector_index.indices['doc'])
        self.assertEqual(self.service.search('apple', mode='documents'), [])
        self.assertEqual(self.service.search('apple')[0].source, 'images')

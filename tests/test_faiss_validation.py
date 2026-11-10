"""FAISS 입력 개수 검증과 저장 데이터 복원 회귀 테스트."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from database.faiss import FaissManager


class FaissValidationTests(unittest.TestCase):
    def chunk(self, name='sample.pdf'):
        return SimpleNamespace(file_name=name, file_path=name, page_number=1, text='sample')

    def test_mismatched_counts_raise_without_changing_index(self):
        for key, method in (('doc', 'add_documents'), ('img', 'add_images')):
            for vectors, chunks in (([], [self.chunk()]), ([[1., 0.]], []),
                                    ([[1., 0.], [0., 1.]], [self.chunk()])):
                with self.subTest(key=key, vectors=len(vectors), chunks=len(chunks)):
                    manager = FaissManager(2, 2)
                    with self.assertRaises(ValueError):
                        getattr(manager, method)(vectors, chunks)
                    self.assertIsNone(manager.indices[key])
                    self.assertEqual(manager.chunk_metas[key], [])

    def test_both_empty_inputs_are_allowed(self):
        manager = FaissManager(2, 2)
        manager.add_documents([], [])
        manager.add_images([], [])
        self.assertEqual(manager.indices, {'doc': None, 'img': None})

    def test_save_and_load_preserve_search_results(self):
        with TemporaryDirectory() as folder:
            manager = FaissManager(2, 2)
            manager.add_documents([[1., 0.]], [self.chunk()])
            manager.add_images([[0., 1.]], [self.chunk('image.png')])
            manager.save(folder)
            restored = FaissManager()
            restored.load(folder)
            self.assertEqual(restored.search_documents([[1., 0.]])[0]['chunk']['file_path'], 'sample.pdf')
            self.assertEqual(restored.search_images([[0., 1.]])[0]['chunk']['file_path'], 'image.png')

    def test_save_removes_obsolete_index(self):
        with TemporaryDirectory() as folder:
            old = FaissManager(2, 2)
            old.add_images([[1., 0.]], [self.chunk('old.png')])
            old.save(folder)
            new = FaissManager(2, 2)
            new.add_documents([[1., 0.]], [self.chunk()])
            new.save(folder)
            self.assertFalse((Path(folder) / 'images.faiss').exists())
            restored = FaissManager()
            restored.load(folder)
            self.assertEqual(restored.search_images([[1., 0.]]), [])

    def test_invalid_load_preserves_previous_search_state(self):
        for problem in ('count', 'missing_index', 'dimension'):
            with self.subTest(problem=problem), TemporaryDirectory() as folder:
                saved = FaissManager(2, 2)
                saved.add_documents([[1., 0.]], [self.chunk('new.pdf')])
                saved.add_images([[1., 0.]], [self.chunk('new.png')])
                saved.save(folder)
                metadata_path = Path(folder) / 'metadata.json'
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                if problem == 'count':
                    metadata['chunk_metas']['img'] = []
                elif problem == 'missing_index':
                    (Path(folder) / 'images.faiss').unlink()
                else:
                    metadata['dims']['img'] = 3
                metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
                current = FaissManager(2, 2)
                current.add_documents([[1., 0.]], [self.chunk('original.pdf')])
                with self.assertRaises(ValueError):
                    current.load(folder)
                self.assertEqual(current.dims, {'doc': 2, 'img': 2})
                hit = current.search_documents([[1., 0.]])[0]
                self.assertEqual(hit['chunk']['file_path'], 'original.pdf')
                self.assertIsNone(current.indices['img'])

"""문서 파일 정보의 실제 SQLite 저장·조회와 중복 처리 확인."""
from pathlib import Path
import sqlite3
import gc
from tempfile import TemporaryDirectory
import unittest

from database.db_info import DocumentInfo
from database.db_manager import Repository


class DocumentDatabaseTests(unittest.TestCase):
    def test_metadata_for_target_extensions_round_trips(self):
        # 파일 본문 지원 테스트가 아니다. DB는 확장자별 메타데이터를 보관할 수 있다.
        with TemporaryDirectory() as folder:
            repository = Repository(str(Path(folder) / 'documents.db'))
            for suffix in ('.pdf', '.pptx', '.ppt', '.hwp', '.hwpx'):
                info = DocumentInfo(str(Path(folder) / ('sample' + suffix)), 'sample' + suffix,
                                    suffix, 10, 'file-hash', '2026-10-30T00:00:00+00:00',
                                    '2026-10-30T00:00:00+00:00')
                file_id = repository.save(info)
                found = repository.find_by_id(file_id)
                self.assertIsInstance(found, DocumentInfo)
                self.assertEqual(found.file_path, info.file_path)
                self.assertEqual(found.file_extension, suffix)
                self.assertEqual(found.file_id, file_id)
            # 함수 밖에서 별도 연결로 조회해도 저장된 내용이 보이는지 확인한다.
            connection = sqlite3.connect(repository.db_path)
            self.assertEqual(connection.execute('SELECT count(*) FROM document_metadata').fetchone()[0], 5)
            connection.close()
            # 팀원 원본은 연결을 명시적으로 닫지 않는다. 테스트 임시 파일 정리만 돕는다.
            gc.collect()

    def test_duplicate_path_does_not_overwrite_saved_row(self):
        with TemporaryDirectory() as folder:
            repository = Repository(str(Path(folder) / 'documents.db'))
            info = DocumentInfo('same.pdf', 'same.pdf', '.pdf', 1, 'hash', 'created', 'updated')
            file_id = repository.save(info)
            with self.assertRaises(sqlite3.IntegrityError):
                repository.save(info)
            self.assertEqual(repository.find_by_id(file_id).file_hash, 'hash')
            gc.collect()

    def test_unknown_id_is_none(self):
        with TemporaryDirectory() as folder:
            repository = Repository(str(Path(folder) / 'documents.db'))
            self.assertIsNone(repository.find_by_id(999))
            gc.collect()

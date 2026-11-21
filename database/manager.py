import sqlite3
from database.db_info import DocumentInfo


class Repository:
    def __init__(self, db_path="document_metadata.db"):
        self.db_path = db_path
        # 객체가 생성될 떄 DB 파일과 테이블이 없으면 자동으로 초기화
        self._init_db()

    def _init_db(self):
        #SQLite 데이터베이스 연결 (파일이 없으면 새로 생성)
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                #문서의 메타데이터를 저장할 테이블 생성
                # 이미 테이블이 존재하면 새로 생성하지 않는다.
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS document_metadata (
                        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_extension TEXT NOT NULL,
                        file_size INTEGER,
                        file_hash TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
        finally:
            conn.close()

    def save(self, document):
        # 데이터베이스 연결
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                # 전달받은 DocumentInfo 객체의 문서 정보를 DB에 저장
                # 이미 동일한 파일 경로가 존재하면 기존 데이터를 업데이트
                conn.execute("""
                    INSERT INTO document_metadata (
                        file_path, file_name, file_extension,
                        file_size, file_hash, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET
                        file_name = excluded.file_name,
                        file_extension = excluded.file_extension,
                        file_size = excluded.file_size,
                        file_hash = excluded.file_hash,
                        updated_at = excluded.updated_at
                """, (
                    document.file_path,
                    document.file_name,
                    document.file_extension,
                    document.file_size,
                    document.file_hash,
                    document.created_at,
                    document.updated_at
                ))

                # 저장된 문서의 file_path를 이용해 DB에 부여된 file_id 조회
                row = conn.execute(
                    "SELECT file_id FROM document_metadata WHERE file_path = ?",
                    (document.file_path,)
                ).fetchone()

                # 조회한 file_id 반환
                return row[0]
        finally:
            conn.close()

    def find_by_id(self, file_id):
        # 전달받은 file_id를 기준으로 데이터베이스에서 문서 정보 조회
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT * FROM document_metadata WHERE file_id = ?",
                (file_id,)
            ).fetchone()

            # 조회 결과가 있으면 DocumentInfo 객체로 변환하여 반환
            return DocumentInfo(*row[1:], file_id=row[0]) if row else None
        finally:
            conn.close()

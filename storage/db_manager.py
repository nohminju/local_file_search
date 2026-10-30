import sqlite3
from .db_info import DocumentInfo


class Repository:
    def __init__(self, db_path="document_metadata.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
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

    def save(self, document):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO document_metadata (
                    file_path, file_name, file_extension,
                    file_size, file_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                document.file_path, document.file_name,
                document.file_extension, document.file_size,
                document.file_hash, document.created_at,
                document.updated_at
            ))
            return cursor.lastrowid

    def find_by_id(self, file_id):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM document_metadata WHERE file_id = ?",
                (file_id,)
            ).fetchone()

        return DocumentInfo(*row[1:], file_id=row[0]) if row else None

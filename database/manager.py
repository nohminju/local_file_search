import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentInfo:
    file_path: str
    file_name: str
    file_extension: str
    file_size: int
    file_hash: str
    created_at: str
    updated_at: str
    file_id: Optional[int] = None


class Repository:
    def __init__(self, db_path: str = "document_metadata.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
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

        conn.commit()
        conn.close()

    def save(self, document: DocumentInfo) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO document_metadata (
                file_path, file_name, file_extension,
                file_size, file_hash, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            document.file_path,
            document.file_name,
            document.file_extension,
            document.file_size,
            document.file_hash,
            document.created_at,
            document.updated_at
        ))

        file_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return file_id

    def find_by_id(self, file_id: int) -> Optional[DocumentInfo]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT file_id, file_path, file_name, file_extension,
                   file_size, file_hash, created_at, updated_at
            FROM document_metadata
            WHERE file_id = ?
        """, (file_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return DocumentInfo(
                file_id=row[0],
                file_path=row[1],
                file_name=row[2],
                file_extension=row[3],
                file_size=row[4],
                file_hash=row[5],
                created_at=row[6],
                updated_at=row[7]
            )

        return None

# 데이터 형식 정의
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

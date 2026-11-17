from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentInfo:
    file_path: str  # 파일이 저장된 전체 경로
    file_name: str  # 파일 이름
    file_extension: str  #파일 확장자
    file_size: int  #파일 크기
    file_hash: str  #파일의 고유 해시값
    created_at: str  # 파일 최초 생성 일시
    updated_at: str  # 파일 최종 수정 일시
    file_id: Optional[int] = None  # 기본값 None

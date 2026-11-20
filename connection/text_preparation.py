"""모델 길이에 맞춰 본문을 나누고 문서 파일명을 별도 검색 근거로 만든다."""
from dataclasses import replace
from pathlib import Path
import unicodedata
from urllib.parse import unquote

from file_loader.document_loader import DocumentChunk


class DocumentTextPreparer:
    def __init__(self, tokenizer, max_seq_length, overlap=32):
        self.tokenizer = tokenizer
        self.limit = max_seq_length - tokenizer.num_special_tokens_to_add(pair=False)
        if self.limit <= 0 or not 0 <= overlap < self.limit:
            raise ValueError('본문 토큰 길이와 겹침 범위를 확인하세요.')
        self.overlap = overlap

    def prepare(self, chunks, documents):
        prepared = []
        for chunk in chunks:
            # 길이 제한을 직접 관리하므로 여기서는 tokenizer의 자동 잘림을 끈다.
            ids = self.tokenizer.encode(chunk.text, add_special_tokens=False, truncation=False)
            if len(ids) <= self.limit:
                prepared.append(chunk)
                continue
            for start in range(0, len(ids), self.limit - self.overlap):
                text = self.tokenizer.decode(ids[start:start + self.limit], skip_special_tokens=True)
                prepared.append(replace(chunk, text=text))
                if start + self.limit >= len(ids):
                    break
        for info in documents:
            path = Path(info.file_path)
            # 이미지 파일명으로 사진 내용 점수를 덮어쓰지 않는다.
            if path.suffix.lower() not in {'.pdf', '.pptx'}:
                continue
            filename = unicodedata.normalize('NFC', unquote(path.name))
            title = Path(filename).stem.replace('_', ' ').replace('+', ' ').strip()
            if title:
                prepared.append(DocumentChunk(filename, info.file_path, 0, title, 'filename'))
        return prepared

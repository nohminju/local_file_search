"""모델 길이에 맞춰 추출 본문만 나눈다. 파일명은 검색 입력으로 사용하지 않는다."""
from dataclasses import replace


class DocumentTextPreparer:
    def __init__(self, tokenizer, max_seq_length, overlap=32):
        self.tokenizer = tokenizer
        self.limit = max_seq_length - tokenizer.num_special_tokens_to_add(pair=False)
        if self.limit <= 0 or not 0 <= overlap < self.limit:
            raise ValueError('본문 토큰 길이와 겹침 범위를 확인하세요.')
        self.overlap = overlap

    def prepare(self, chunks):
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
        return prepared

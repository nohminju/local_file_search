"""본문끼리의 의미 비교에는 한국어 문장 모델을 사용한다."""
import numpy as np
from sentence_transformers import SentenceTransformer

from similarity.document_embedder import DocumentEmbedder


class SentenceDocumentEmbedder(DocumentEmbedder):
    """청크·검색 API는 유지하고 본문/본문 검색어 인코딩만 교체한다."""

    def __init__(self, model=None, model_name='jhgan/ko-sroberta-multitask', batch_size=8):
        if batch_size < 1:
            raise ValueError('batch_size는 1 이상이어야 합니다.')
        self.batch_size = batch_size
        self.model = model if model is not None else SentenceTransformer(model_name)
        self.model.eval()
        self.chunks = []
        self.embeddings = None

    def _encode(self, text_list):
        vectors = self.model.encode(text_list, batch_size=self.batch_size,
                                    convert_to_numpy=True, normalize_embeddings=True,
                                    show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)

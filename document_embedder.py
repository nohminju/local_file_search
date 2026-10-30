from sentence_transformers import SentenceTransformer
import numpy as np

class DocumentEmbedder:
    """
    DocumentLoader에서 추출한 DocumentChunk 텍스트 목록을 받아 
    임베딩을 생성하고 코사인 유사도 검색을 수행하는 클래스
    """
    def __init__(self, model=None, model_name='jhgan/ko-sroberta-multitask'):
        # 공통 모델을 전달받으면 공유 사용하고, 없으면 직접 로딩
        if model is not None:
            self.model = model
        else:
            self.model = SentenceTransformer(model_name)
            
        self.chunks = []
        self.embeddings = None

    def embed_chunks(self, chunks):
        # DocumentChunk 객체 리스트에서 text만 추출하여 임베딩
        self.chunks = chunks
        texts = [chunk.text for chunk in chunks if getattr(chunk, 'text', None)]
        if not texts:
            return
            
        self.embeddings = self.model.encode(texts)

    def search(self, query, top_k=3):
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        query_vec = self.model.encode([query])[0]
        
        # 코사인 유사도 계산
        norm_emb = np.linalg.norm(self.embeddings, axis=1)
        norm_query = np.linalg.norm(query_vec)
        
        sims = np.dot(self.embeddings, query_vec) / (norm_emb * norm_query + 1e-8)
        top_indices = np.argsort(sims)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            results.append({
                "chunk": self.chunks[idx],
                "score": float(sims[idx])
            })
        return results

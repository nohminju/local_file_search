from sentence_transformers import SentenceTransformer
import numpy as np

class DocumentEmbedder:
    """
    추출된 텍스트 조각(Chunk)들을 벡터화(임베딩)하고,
    사용자 질문과 가장 유사한 텍스트를 검색하는 클래스입니다.
    """
    def __init__(self, model_name='jhgan/ko-sroberta-multitask'):
        # 한국어 의미 파악에 특화된 pre-trained 임베딩 모델 로드
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.embeddings = None

    def embed_chunks(self, chunks):
        """
        문서 텍스트 조각(chunks) 리스트를 받아 벡터(숫자)로 변환합니다.
        """
        self.chunks = chunks
        # 각 chunk 객체에서 텍스트 문자열만 추출
        texts = [chunk.text for chunk in chunks]
        if not texts:
            return
        
        # 문장들을 768차원 임베딩 벡터로 변환
        self.embeddings = self.model.encode(texts)

    def search(self, query, top_k=3):
        """
        사용자 질문(query)과 가장 코사인 유사도가 높은 텍스트 조각 상위 top_k개를 검색합니다.
        """
        # 생성된 임베딩 데이터가 없으면 빈 리스트 반환
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        # 사용자 질문 문장도 동일한 모델로 벡터화
        query_vec = self.model.encode([query])[0]
        
        # 코사인 유사도(Cosine Similarity) 계산 (분모: 벡터 크기 L2 norm)
        norm_emb = np.linalg.norm(self.embeddings, axis=1)
        norm_query = np.linalg.norm(query_vec)
        
        # 분자: 내적(dot product) / 분모: 크기 곱 (0 나누기 방지용 1e-8 추가)
        sims = np.dot(self.embeddings, query_vec) / (norm_emb * norm_query + 1e-8)
        
        # 유사도 점수가 높은 순으로 정렬하여 상위 top_k개 인덱스 추출
        top_indices = np.argsort(sims)[::-1][:top_k]
        
        # 최종 결과 반환 (해당 chunk와 유사도 점수)
        results = []
        for idx in top_indices:
            results.append({
                "chunk": self.chunks[idx],
                "score": float(sims[idx])
            })
        return results

import torch
import open_clip
import numpy as np
from Connection.translator import translate_ko_to_en  # ← translator 부분을 실제 번역 파일 이름으로만 바꿔주세요!


class DocumentEmbedder:
    def __init__(self, model=None, tokenizer=None, model_name='xlm-roberta-base-ViT-B-32', pretrained='laion5b_s13b_b90k'):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 공통 OpenCLIP 모델이 전달되면 재사용하고, 없으면 직접 로드
        if model is not None and tokenizer is not None:
            self.model = model
            self.tokenizer = tokenizer
        else:
            self.model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
            self.model = self.model.to(self.device)
            self.model.eval()
            self.tokenizer = open_clip.get_tokenizer(model_name)
            
        # [추가] DocumentTextPreparer 연동 시 토큰 최대 길이를 참조할 수 있도록 속성 추가
        self.max_seq_length = getattr(self.model, 'context_length', 77)
        self.chunks = []         # 임베딩된 원본 DocumentChunk 리스트
        self.embeddings = None   # 생성된 (N, 512) 2차원 벡터 배열

    def _encode(self, text_list):
        tokens = self.tokenizer(text_list).to(self.device)
        with torch.no_grad():
            features = self.model.encode_text(tokens)
            # 코사인 유사도 계산을 위해 벡터 길이를 1로 맞추는 L2 정규화 수행
            features = features / features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().astype(np.float32)

    def embed_chunks(self, chunks):
        # 원본 청크 구조는 유지하고 공백이 아닌 유효한 텍스트만 추출
        self.chunks = [c for c in chunks if getattr(c, 'text', None) and c.text.strip()]
        if not self.chunks:
            self.embeddings = None
            return None
        
        texts = [c.text.strip() for c in self.chunks]
        self.embeddings = self._encode(texts)  # (N, 512) 2차원 배열
        return self.embeddings

    def encode_query(self, query):
        query = query.strip()
        if not query:
            return None
        
        # Connection 폴더의 한영 번역 함수 호출 후 임베딩
        translated_query = translate_ko_to_en(query)
        return self._encode([translated_query])  # FAISS 규격에 맞춰 (1, 512) 2차원 배열로 반환

    def search(self, query, top_k=3, min_score=0.0, debug=False):
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        query_vec = self.encode_query(query)
        if query_vec is None:
            return []
        
        # L2 정규화된 벡터이므로 내적만으로 코사인 유사도 산출
        sims = np.dot(self.embeddings, query_vec.T).flatten()
        top_indices = np.argsort(sims)[::-1][:top_k]
        
        # debug=True일 때 필터링 전 원본 점수 분포 출력
        if debug:
            print(f"\n[문서 검색 원본 점수 - '{query}']")
            for rank, idx in enumerate(top_indices, 1):
                preview = self.chunks[idx].text[:30].replace('\n', ' ')
                print(f"  {rank}위 | 점수: {float(sims[idx]):.4f} | 내용: {preview}...")

        # 기준 점수(min_score) 이상인 결과만 필터링하여 반환
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score >= min_score:
                results.append({
                    "chunk": self.chunks[idx],
                    "score": score
                })
        return results


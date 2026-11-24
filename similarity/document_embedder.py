import torch
import open_clip
import numpy as np

# 파일 위치(Connection 안/밖) 상관없이 번역기 자동 연결
try:
    from Connection.translator import translate_ko_to_en
except ImportError:
    from translator import translate_ko_to_en


class DocumentEmbedder:
    def __init__(self, model=None, tokenizer=None, model_name='xlm-roberta-base-ViT-B-32', pretrained='laion5b_s13b_b90k'):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if model is not None and tokenizer is not None:
            self.model = model
            self.tokenizer = tokenizer
        else:
            self.model, _, _ = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
            self.model = self.model.to(self.device)
            self.model.eval()
            self.tokenizer = open_clip.get_tokenizer(model_name)
            
        self.max_seq_length = getattr(self.model, 'context_length', 77)
        self.chunks = []
        self.embeddings = None

    def _encode(self, text_list):
        tokens = self.tokenizer(text_list).to(self.device)
        with torch.no_grad():
            features = self.model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().astype(np.float32)

    def embed_chunks(self, chunks):
        self.chunks = [c for c in chunks if getattr(c, 'text', None) and c.text.strip()]
        if not self.chunks:
            self.embeddings = None
            return None
        
        texts = [c.text.strip() for c in self.chunks]
        self.embeddings = self._encode(texts)
        return self.embeddings

    def encode_query(self, query):
        query = query.strip()
        if not query:
            return None
        
        translated_query = translate_ko_to_en(query)
        return self._encode([translated_query])

    def search(self, query, top_k=3, min_score=0.0, debug=False):
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        query_vec = self.encode_query(query)
        if query_vec is None:
            return []
        
        sims = np.dot(self.embeddings, query_vec.T).flatten()
        top_indices = np.argsort(sims)[::-1][:top_k]
        
        if debug:
            print(f"\n[문서 검색 원본 점수 - '{query}']")
            for rank, idx in enumerate(top_indices, 1):
                preview = self.chunks[idx].text[:30].replace('\n', ' ')
                print(f"  {rank}위 | 점수: {float(sims[idx]):.4f} | 내용: {preview}...")

        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score >= min_score:
                results.append({
                    "chunk": self.chunks[idx],
                    "score": score
                })
        return results



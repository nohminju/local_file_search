#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from sentence_transformers import SentenceTransformer
import numpy as np

class DocumentEmbedder:
    def __init__(self, model_name='jhgan/ko-sroberta-multitask'):
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.embeddings = None

    def embed_chunks(self, chunks):
        self.chunks = chunks
        texts = [chunk.text for chunk in chunks]
        if not texts:
            return
        self.embeddings = self.model.encode(texts)

    def search(self, query, top_k=3):
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
            
        query_vec = self.model.encode([query])[0]
        
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


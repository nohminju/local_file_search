import json
import os
import faiss
import numpy as np


class FaissManager:
    def __init__(self, doc_dim=768, img_dim=512):
        self.dims = {'doc': doc_dim, 'img': img_dim}
        self.indices = {'doc': None, 'img': None}
        self.file_ids = {'doc': [], 'img': []}

    def _prep_vectors(self, vectors, target_dim):
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != target_dim:
            raise ValueError(f"차원 불일치 (기대: {target_dim}, 입력: {vectors.shape[1]})")
        faiss.normalize_L2(vectors)
        return vectors

    def _add(self, key, vectors, file_ids):
        if len(vectors) == 0:
            return
        vectors = self._prep_vectors(vectors, self.dims[key])
        
        if self.indices[key] is None:
            self.indices[key] = faiss.IndexFlatIP(self.dims[key])
            
        self.indices[key].add(vectors)
        self.file_ids[key].extend(file_ids)

    def add_documents(self, vectors, file_ids):
        self._add('doc', vectors, file_ids)

    def add_images(self, vectors, file_ids):
        self._add('img', vectors, file_ids)

    def _search(self, key, query_vector, top_k=5):
        index = self.indices[key]
        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector, self.dims[key])
        scores, indices = index.search(query, min(top_k, index.ntotal))

        return [(self.file_ids[key][i], float(s)) for s, i in zip(scores[0], indices[0]) if i >= 0]

    def search_documents(self, query_vector, top_k=5):
        return self._search('doc', query_vector, top_k)

    def search_images(self, query_vector, top_k=5):
        return self._search('img', query_vector, top_k)

    def save(self, folder="faiss_data"):
        os.makedirs(folder, exist_ok=True)
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}
        
        for key in ['doc', 'img']:
            if self.indices[key] is not None:
                faiss.write_index(self.indices[key], os.path.join(folder, filenames[key]))

        with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "dimension": self.dims['doc'],
                "image_dimension": self.dims['img'],
                "document_file_ids": self.file_ids['doc'],
                "image_file_ids": self.file_ids['img']
            }, f, ensure_ascii=False)

    def load(self, folder="faiss_data"):
        meta_path = os.path.join(folder, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError("FAISS 메타데이터 파일이 없습니다.")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.dims['doc'] = meta.get("dimension") or meta.get("dims", {}).get("doc")
        self.dims['img'] = meta.get("image_dimension") or meta.get("dims", {}).get("img")
        self.file_ids['doc'] = meta.get("document_file_ids") or meta.get("file_ids", {}).get("doc", [])
        self.file_ids['img'] = meta.get("image_file_ids") or meta.get("file_ids", {}).get("img", [])

        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
      
            if not os.path.exists(idx_path):
                idx_path = os.path.join(folder, f"{key}.faiss")
            self.indices[key] = faiss.read_index(idx_path) if os.path.exists(idx_path) else None

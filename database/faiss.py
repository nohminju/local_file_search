import json
import os
import faiss
import numpy as np


class FaissManager:
    def __init__(self, doc_dim=768, img_dim=512):
        self.dims = {'doc': doc_dim, 'img': img_dim}
        self.indices = {'doc': None, 'img': None}
        self.chunk_metas = {'doc': [], 'img': []}

    def _prep_vectors(self, vectors, target_dim):
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != target_dim:
            raise ValueError(f"차원 불일치 (기대: {target_dim}, 입력: {vectors.shape[1]})")
        faiss.normalize_L2(vectors)
        return vectors

    def add_documents(self, vectors, chunks):
        if len(vectors) == 0 or len(chunks) == 0:
            return
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")

        vectors = self._prep_vectors(vectors, self.dims['doc'])

        if self.indices['doc'] is None:
            self.indices['doc'] = faiss.IndexFlatIP(self.dims['doc'])

        self.indices['doc'].add(vectors)

        for c in chunks:
            self.chunk_metas['doc'].append({
                "file_name": getattr(c, 'file_name', ''),
                "file_path": getattr(c, 'file_path', ''),
                "page_number": getattr(c, 'page_number', 1),
                "text": getattr(c, 'text', '')
            })

    def add_images(self, vectors, chunks):
        if len(vectors) == 0 or len(chunks) == 0:
            return
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")

        vectors = self._prep_vectors(vectors, self.dims['img'])

        if self.indices['img'] is None:
            self.indices['img'] = faiss.IndexFlatIP(self.dims['img'])

        self.indices['img'].add(vectors)

        for c in chunks:
            self.chunk_metas['img'].append({
                "file_name": getattr(c, 'file_name', ''),
                "file_path": getattr(c, 'file_path', ''),
                "page_number": getattr(c, 'page_number', 1)
            })

    def search_documents(self, query_vector, top_k=5):
        index = self.indices['doc']
        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector, self.dims['doc'])
        scores, indices = index.search(query, min(top_k, index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    "chunk": self.chunk_metas['doc'][idx],
                    "score": float(score)
                })
        return results

    def search_images(self, query_vector, top_k=5):
        index = self.indices['img']
        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector, self.dims['img'])
        scores, indices = index.search(query, min(top_k, index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    "chunk": self.chunk_metas['img'][idx],
                    "score": float(score)
                })
        return results

    def save(self, folder="faiss_data"):
        os.makedirs(folder, exist_ok=True)
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}

        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            if self.indices[key] is not None:
                faiss.write_index(self.indices[key], idx_path)
            elif os.path.exists(idx_path):
                os.remove(idx_path)

        with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "dims": self.dims,
                "chunk_metas": self.chunk_metas
            }, f, ensure_ascii=False)

    def load(self, folder="faiss_data"):
        meta_path = os.path.join(folder, "metadata.json")
        if not os.path.exists(meta_path):
            raise FileNotFoundError("FAISS 메타데이터 파일이 없습니다.")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.dims = meta.get("dims", self.dims)
        self.chunk_metas = meta.get("chunk_metas", {'doc': [], 'img': []})

        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            if os.path.exists(idx_path):
                index = faiss.read_index(idx_path)
                meta_len = len(self.chunk_metas.get(key, []))
                if index.ntotal != meta_len:
                    raise ValueError(f"{key} 인덱스 수({index.ntotal})와 메타데이터 수({meta_len})가 일치하지 않습니다.")
                self.indices[key] = index
            else:
                self.indices[key] = None

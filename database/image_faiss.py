import json
import os
import faiss
import numpy as np


class ImageFaiss:
    def __init__(self, img_dim=512):
        # 이미지 임베딩 벡터 차원 설정
        self.dim = img_dim

        # 이미지 검색 인덱스
        self.index = None

        # FAISS 벡터 ID와 원본 이미지 메타데이터 연결
        self.chunk_metas = []

    def _prep_vectors(self, vectors):
        # FAISS 연산을 위한 float32 2차원 배열 변환
        vectors = np.asarray(vectors, dtype=np.float32).copy()

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"차원 불일치 (기대: {self.dim}, 입력: {vectors.shape})"
            )

        # L2 정규화 후 내적을 통해 코사인 유사도 계산
        faiss.normalize_L2(vectors)

        return vectors

    def add_images(self, vectors, chunks):
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")

        if len(vectors) == 0:
            return

        vectors = self._prep_vectors(vectors)

        # 이미지 인덱스 생성
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.dim)

        self.index.add(vectors)

        # 검색 결과와 원본 이미지 정보 연결
        for c in chunks:
            self.chunk_metas.append({
                "file_name": getattr(c, 'file_name', ''),
                "file_path": getattr(c, 'file_path', ''),
                "page_number": getattr(c, 'page_number', 1)
            })

    def search_images(self, query_vector, top_k=5):
        index = self.index

        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector)

        # 저장된 벡터 수를 초과하지 않도록 검색
        scores, indices = index.search(
            query, min(top_k, index.ntotal)
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            results.append({
                "chunk": self.chunk_metas[idx],
                "score": float(score)
            })

        return results

    def save(self, folder="faiss_data/image"):
        os.makedirs(folder, exist_ok=True)

        idx_path = os.path.join(folder, "images.faiss")

        # 이미지 인덱스 저장
        if self.index is not None:
            faiss.write_index(self.index, idx_path)

        elif os.path.exists(idx_path):
            os.remove(idx_path)

        # 이미지 메타데이터 저장
        with open(
            os.path.join(folder, "metadata.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump({
                "dim": self.dim,
                "chunk_metas": self.chunk_metas
            }, f, ensure_ascii=False)

    def load(self, folder="faiss_data/image"):
        meta_path = os.path.join(folder, "metadata.json")

        if not os.path.exists(meta_path):
            raise FileNotFoundError(
                "이미지 FAISS 메타데이터 파일이 없습니다."
            )

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        dim = meta.get("dim", self.dim)
        chunk_metas = meta.get("chunk_metas", [])

        if dim != self.dim:
            raise ValueError("이미지 임베딩 차원이 일치하지 않습니다.")

        idx_path = os.path.join(folder, "images.faiss")

        if os.path.exists(idx_path):
            index = faiss.read_index(idx_path)

            if index.d != dim:
                raise ValueError("이미지 인덱스 차원이 일치하지 않습니다.")

            if index.ntotal != len(chunk_metas):
                raise ValueError("이미지 인덱스와 메타데이터 수가 일치하지 않습니다.")

            self.index = index

        elif chunk_metas:
            raise ValueError("이미지 메타데이터는 있지만 인덱스 파일이 없습니다.")

        else:
            self.index = None

        self.chunk_metas = chunk_metas

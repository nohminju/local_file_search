import json
import os
import faiss
import numpy as np


class FaissManager:
    def __init__(self, doc_dim=768, img_dim=512):
        self.dims = {'doc': doc_dim, 'img': img_dim}    #문서와 이미지 임베딩 모델의 출력 벡터 차원 수 설정
        self.indices = {'doc': None, 'img': None}    #실제 벡터 검색을 수행할 FAISS 인덱스 객체
        self.chunk_metas = {'doc': [], 'img': []}    #각 벡터에 대응하는 원본 메타데이터(파일명, 페이지, 본문 등)를 순서대로 담는 리스트

    def _prep_vectors(self, vectors, target_dim):
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
            # 설정된 임베딩 차원 수와 입력 벡터의 차원 수가 일치하는지 검증
        if vectors.shape[1] != target_dim:
            raise ValueError(f"차원 불일치 (기대: {target_dim}, 입력: {vectors.shape[1]})")
        faiss.normalize_L2(vectors)
        return vectors

    def add_documents(self, vectors, chunks):    # 벡터 개수와 메타데이터 개수가 1:1로 매칭되어야 하므로 개수 검증
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")
        if len(vectors) == 0:
            return

        vectors = self._prep_vectors(vectors, self.dims['doc'])    #벡터 전처리 및 L2 정규화

        if self.indices['doc'] is None:
            self.indices['doc'] = faiss.IndexFlatIP(self.dims['doc'])

        # FAISS 인덱스에 벡터 추가
        self.indices['doc'].add(vectors)

        # FAISS 내부 ID와 동일한 순서(인덱스)가 되도록 메타데이터 리스트에도 추가
        for c in chunks:
            self.chunk_metas['doc'].append({
                "file_name": getattr(c, 'file_name', ''),
                "file_path": getattr(c, 'file_path', ''),
                "page_number": getattr(c, 'page_number', 1),
                "text": getattr(c, 'text', '')
            })

    def add_images(self, vectors, chunks):
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")
        if len(vectors) == 0:
            return

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

        query = self._prep_vectors(query_vector, self.dims['doc']) #검색어 벡터 L2 정규화 수행
        scores, indices = index.search(query, min(top_k, index.ntotal)) #저장된 전체 데이터 수보다 많이 요청하지 않도록 min()으로 제한하여 검색

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
                    "chunk": self.chunk_metas['img'][idx],    #FAISS 가 찾은 번호(idx)로 원본 메타데이터 조회
                    "score": float(score)
                })
        return results

    def save(self, folder="faiss_data"):
        os.makedirs(folder, exist_ok=True)
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}

        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            if self.indices[key] is not None:  #인덱스가 존재하면 바이너리 파일로 저장
                faiss.write_index(self.indices[key], idx_path)
            elif os.path.exists(idx_path):    # 현재 메모리에 인덱스가 비어있는데 과거 파일이 남아있다면 삭제
                os.remove(idx_path)

        # 차원 정보와 메타데이터 리스트를 JSON 파일로 저장
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

        dims = meta.get("dims", self.dims)
        chunk_metas = meta.get("chunk_metas", {'doc': [], 'img': []})
        indices = {'doc': None, 'img': None}

        # 모든 저장 데이터를 검증한 뒤 교체해 복원 실패 시 기존 검색 상태를 유지한다.
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            meta_len = len(chunk_metas.get(key, []))
            if os.path.exists(idx_path):
                index = faiss.read_index(idx_path)
                #검증1: 인덱스 파일의 차원과 메타데이터에 기록된 차원이 같은지 확인
                if index.d != dims[key]:
                    raise ValueError(f"{key} 인덱스 차원({index.d})과 메타데이터 차원({dims[key]})이 일치하지 않습니다.")
                # 검증2: 인덱스에 저장된 벡터 개수와 메타데이터 리스트 길이가 1:1로 맞는지 확인
                if index.ntotal != meta_len:
                    raise ValueError(f"{key} 인덱스 수({index.ntotal})와 메타데이터 수({meta_len})가 일치하지 않습니다.")
                indices[key] = index
            elif meta_len:  # 메타데이터는 있는데 실제 벡터 인덱스 파일이 유실된 경우 예외 발생
                raise ValueError(f"{key} 메타데이터는 있지만 인덱스 파일이 없습니다.")

        #모든 검증을 통과했을 때만 실제 인스턴스 속성을 덮어씀
        self.dims = dims
        self.chunk_metas = chunk_metas
        self.indices = indices

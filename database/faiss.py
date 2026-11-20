import json
import os
import faiss
import numpy as np


class FaissManager:
    def __init__(self, doc_dim=512, img_dim=512):
        # 문서(텍스트)와 이미지 임베딩 모델의 출력 벡터 차원 수 설정
        self.dims = {'doc': doc_dim, 'img': img_dim}
        # 실제 벡터 유사도 검색을 수행하는 FAISS 인덱스 객체
        self.indices = {'doc': None, 'img': None}
        # FAISS 내부 벡터 ID(0, 1, 2...)와 1:1로 매칭되는 원본 청크 메타데이터 리스트
        self.chunk_metas = {'doc': [], 'img': []}

    def _prep_vectors(self, vectors, target_dim):
        # FAISS 연산 규격에 맞게 float32 2차원 배열로 변환
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != target_dim:
            raise ValueError(f"차원 불일치 (기대: {target_dim}, 입력: {vectors.shape[1]})")
        # L2 정규화를 수행해야 내적(IndexFlatIP) 연산 결과가 코사인 유사도(-1.0 ~ 1.0)가 됨
        faiss.normalize_L2(vectors)
        return vectors

    def add_documents(self, vectors, chunks):
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")
        if len(vectors) == 0:
            return

        vectors = self._prep_vectors(vectors, self.dims['doc'])

        # 정규화된 벡터의 내적으로 코사인 유사도를 계산하는 인덱스 생성
        if self.indices['doc'] is None:
            self.indices['doc'] = faiss.IndexFlatIP(self.dims['doc'])

        self.indices['doc'].add(vectors)

        # 검색 결과 인덱스로 바로 조회할 수 있도록 동일한 순서로 메타데이터 저장
        for c in chunks:
            self.chunk_metas['doc'].append({
                "file_name": getattr(c, 'file_name', ''),
                "file_path": getattr(c, 'file_path', ''),
                "page_number": getattr(c, 'page_number', 1),
                "text": getattr(c, 'text', ''),
                "chunk_type": getattr(c, 'chunk_type', 'document')
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

    def search_documents(self, query_vector, top_k=5, min_score=None):
        index = self.indices['doc']
        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector, self.dims['doc'])
        # 저장된 전체 데이터 수보다 많은 top_k를 요청해 에러가 나는 것을 방지
        scores, indices = index.search(query, min(top_k, index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            # FAISS에서 유효한 검색 결과가 부족할 때 채워 넣는 더미 인덱스(-1) 제외
            if idx < 0:
                continue
            score_val = float(score)
            # RRF 결합 전, 설정한 최소 코사인 유사도(min_score) 미만인 무관한 문서 필터링
            if min_score is not None and score_val < min_score:
                continue
            results.append({
                "chunk": self.chunk_metas['doc'][idx],
                "score": score_val
            })
        return results

    def search_images(self, query_vector, top_k=5, min_score=None):
        index = self.indices['img']
        if index is None or index.ntotal == 0 or top_k <= 0:
            return []

        query = self._prep_vectors(query_vector, self.dims['img'])
        scores, indices = index.search(query, min(top_k, index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            score_val = float(score)
            # 이미지 임베딩 모델 특성에 맞는 별도의 최소 유사도 기준으로 필터링
            if min_score is not None and score_val < min_score:
                continue
            results.append({
                "chunk": self.chunk_metas['img'][idx],
                "score": score_val
            })
        return results

    def compare_raw_scores(self, doc_query_vector=None, img_query_vector=None, top_k=5):
        # 문서와 이미지 검색의 원본 코사인 유사도 분포를 비교하기 위한 확인용 함수
        doc_res = self.search_documents(doc_query_vector, top_k=top_k, min_score=None) if doc_query_vector is not None else []
        img_res = self.search_images(img_query_vector, top_k=top_k, min_score=None) if img_query_vector is not None else []

        print(f"=== [원본 유사도 점수 비교 (Top-{top_k})] ===")
        print(f"[문서 검색 결과 ({len(doc_res)}건)]")
        for rank, r in enumerate(doc_res, 1):
            c = r['chunk']
            preview = c.get('text', '')[:30].replace('\n', ' ')
            print(f"  {rank}위 | Score: {r['score']:.4f} | {c['file_name']} (p.{c['page_number']}) | \"{preview}...\"")

        print(f"\n[이미지 검색 결과 ({len(img_res)}건)]")
        for rank, r in enumerate(img_res, 1):
            c = r['chunk']
            print(f"  {rank}위 | Score: {r['score']:.4f} | {c['file_name']} (p.{c['page_number']})")
        print("=" * 45)

        return {"doc": doc_res, "img": img_res}

    def save(self, folder="faiss_data"):
        os.makedirs(folder, exist_ok=True)
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}

        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            if self.indices[key] is not None:
                faiss.write_index(self.indices[key], idx_path)
            # 현재 메모리에 인덱스가 없다면 기존에 저장된 인덱스 파일 삭제
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

        dims = meta.get("dims", self.dims)
        chunk_metas = meta.get("chunk_metas", {'doc': [], 'img': []})
        indices = {'doc': None, 'img': None}

        # 파일 로드 중 오류가 발생해도 기존 검색 상태를 보존하기 위해 임시 변수에 먼저 검증
        filenames = {'doc': 'documents.faiss', 'img': 'images.faiss'}
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            meta_len = len(chunk_metas.get(key, []))
            if os.path.exists(idx_path):
                index = faiss.read_index(idx_path)
                # 인덱스 벡터 차원 및 총 벡터 개수가 메타데이터와 정확히 1:1로 일치하는지 무결성 검증
                if index.d != dims[key]:
                    raise ValueError(f"{key} 인덱스 차원({index.d})과 메타데이터 차원({dims[key]})이 일치하지 않습니다.")
                if index.ntotal != meta_len:
                    raise ValueError(f"{key} 인덱스 수({index.ntotal})와 메타데이터 수({meta_len})가 일치하지 않습니다.")
                indices[key] = index
            elif meta_len:
                raise ValueError(f"{key} 메타데이터는 있지만 인덱스 파일이 없습니다.")

        # 모든 무결성 검증을 통과했을 때만 실제 인스턴스 상태 덮어쓰기
        self.dims = dims
        self.chunk_metas = chunk_metas
        self.indices = indices

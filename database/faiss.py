import json
import os
import faiss
import numpy as np


class FaissManager:
    def __init__(self, doc_dim=512, img_dim=512):
        # 문서와 이미지 임베딩 벡터 차원 설정
        self.dims = {'doc': doc_dim, 'img': img_dim}

        # 문서와 이미지 검색 인덱스 분리
        self.indices = {'doc': None, 'img': None}

        # FAISS 벡터 ID와 원본 메타데이터 연결
        self.chunk_metas = {'doc': [], 'img': []}

    def _prep_vectors(self, vectors, target_dim):
        # FAISS 연산을 위한 float32 2차원 배열 변환
        vectors = np.asarray(vectors, dtype=np.float32)

        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        if vectors.ndim != 2 or vectors.shape[1] != target_dim:
            raise ValueError(
                f"차원 불일치 (기대: {target_dim}, 입력: {vectors.shape})"
            )

        # L2 정규화 후 내적을 통해 코사인 유사도 계산
        faiss.normalize_L2(vectors)

        return vectors

    def add_documents(self, vectors, chunks):
        if len(vectors) != len(chunks):
            raise ValueError("벡터 수와 청크 수가 일치하지 않습니다.")

        if len(vectors) == 0:
            return

        vectors = self._prep_vectors(vectors, self.dims['doc'])

        # 문서 인덱스 생성
        if self.indices['doc'] is None:
            self.indices['doc'] = faiss.IndexFlatIP(
                self.dims['doc']
            )

        self.indices['doc'].add(vectors)

        # 검색 결과와 원본 문서 정보 연결
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

        # 이미지 인덱스 생성
        if self.indices['img'] is None:
            self.indices['img'] = faiss.IndexFlatIP(
                self.dims['img']
            )

        self.indices['img'].add(vectors)

        # 검색 결과와 원본 이미지 정보 연결
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

        # 저장된 벡터 수를 초과하지 않도록 검색
        scores, indices = index.search(
            query, min(top_k, index.ntotal)
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

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

        scores, indices = index.search(
            query, min(top_k, index.ntotal)
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            results.append({
                "chunk": self.chunk_metas['img'][idx],
                "score": float(score)
            })

        return results

    def compare_raw_scores(
        self,
        doc_query_vector=None,
        img_query_vector=None,
        top_k=5
    ):
        # 문서와 이미지의 원본 유사도 점수 확인용 함수
        doc_res = (
            self.search_documents(doc_query_vector, top_k)
            if doc_query_vector is not None else []
        )

        img_res = (
            self.search_images(img_query_vector, top_k)
            if img_query_vector is not None else []
        )

        print(f"=== [원본 유사도 점수 확인 (Top-{top_k})] ===")

        print(f"[문서 검색 결과 ({len(doc_res)}건)]")
        for rank, r in enumerate(doc_res, 1):
            c = r['chunk']
            preview = c.get('text', '')[:30].replace('\n', ' ')

            print(
                f"  {rank}위 | Score: {r['score']:.4f} | "
                f"{c['file_name']} (p.{c['page_number']}) | "
                f"\"{preview}...\""
            )

        print(f"\n[이미지 검색 결과 ({len(img_res)}건)]")
        for rank, r in enumerate(img_res, 1):
            c = r['chunk']

            print(
                f"  {rank}위 | Score: {r['score']:.4f} | "
                f"{c['file_name']} (p.{c['page_number']})"
            )

        print("=" * 45)

        return {"doc": doc_res, "img": img_res}

    def save(self, folder="faiss_data"):
        os.makedirs(folder, exist_ok=True)

        filenames = {
            'doc': 'documents.faiss',
            'img': 'images.faiss'
        }

        # 문서 및 이미지 인덱스 저장
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])

            if self.indices[key] is not None:
                faiss.write_index(self.indices[key], idx_path)

            elif os.path.exists(idx_path):
                os.remove(idx_path)

        # 검색 결과와 연결되는 메타데이터 저장
        with open(
            os.path.join(folder, "metadata.json"),
            "w",
            encoding="utf-8"
        ) as f:
            json.dump({
                "dims": self.dims,
                "chunk_metas": self.chunk_metas
            }, f, ensure_ascii=False)

    def load(self, folder="faiss_data"):
        meta_path = os.path.join(folder, "metadata.json")

        if not os.path.exists(meta_path):
            raise FileNotFoundError(
                "FAISS 메타데이터 파일이 없습니다."
            )

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        dims = meta.get("dims", self.dims)
        chunk_metas = meta.get(
            "chunk_metas",
            {'doc': [], 'img': []}
        )

        indices = {'doc': None, 'img': None}

        filenames = {
            'doc': 'documents.faiss',
            'img': 'images.faiss'
        }

        # 인덱스와 메타데이터의 일치 여부 확인
        for key in ['doc', 'img']:
            idx_path = os.path.join(folder, filenames[key])
            meta_len = len(chunk_metas.get(key, []))

            if os.path.exists(idx_path):
                index = faiss.read_index(idx_path)

                if index.d != dims[key]:
                    raise ValueError(
                        f"{key} 인덱스 차원({index.d})과 "
                        f"메타데이터 차원({dims[key]})이 "
                        "일치하지 않습니다."
                    )

                if index.ntotal != meta_len:
                    raise ValueError(
                        f"{key} 인덱스 수({index.ntotal})와 "
                        f"메타데이터 수({meta_len})가 "
                        "일치하지 않습니다."
                    )

                indices[key] = index

            elif meta_len:
                raise ValueError(
                    f"{key} 메타데이터는 있지만 "
                    "인덱스 파일이 없습니다."
                )

        # 검증 완료 후 인덱스 정보 적용
        self.dims = dims
        self.chunk_metas = chunk_metas
        self.indices = indices

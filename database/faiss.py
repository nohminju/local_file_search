"""기존 서비스 API와 저장 형식을 팀원의 분리된 FAISS 인덱스에 연결한다."""
import json
import os

import faiss

from database.document_faiss import DocumentFaiss
from database.image_faiss import ImageFaiss


class FaissManager:
    def __init__(self, doc_dim=512, img_dim=512):
        self.documents = DocumentFaiss(doc_dim)
        self.images = ImageFaiss(img_dim)

    @property
    def dims(self):
        return {'doc': self.documents.dim, 'img': self.images.dim}

    @property
    def indices(self):
        return {'doc': self.documents.index, 'img': self.images.index}

    @property
    def chunk_metas(self):
        return {'doc': self.documents.chunk_metas, 'img': self.images.chunk_metas}

    def add_documents(self, vectors, chunks):
        self.documents.add_documents(vectors, chunks)

    def add_images(self, vectors, chunks):
        self.images.add_images(vectors, chunks)

    def search_documents(self, query_vector, top_k=5):
        return self.documents.search_documents(query_vector, top_k)

    def search_images(self, query_vector, top_k=5):
        return self.images.search_images(query_vector, top_k)

    def compare_raw_scores(
        self,
        doc_query_vector=None,
        img_query_vector=None,
        top_k=5
    ):
        # 문서와 이미지의 원본 유사도 점수 각각 확인
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
        self.documents = DocumentFaiss(dims['doc'])
        self.images = ImageFaiss(dims['img'])
        self.documents.index = indices['doc']
        self.images.index = indices['img']
        self.documents.chunk_metas = chunk_metas['doc']
        self.images.chunk_metas = chunk_metas['img']

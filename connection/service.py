"""팀원 로더·인코더의 반환값을 파일 ID와 연결한다."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from database.db_info import DocumentInfo
from file_loader.document_loader import DocumentScanner
from similarity.temporary_image_similarity import search_images


class DocumentSearch:
    def __init__(self, loader, image_encoder, document_encoder,
                 document_embedder, query_encoder, repository):
        self.loader = loader
        self.image_encoder = image_encoder
        self.document_encoder = document_encoder
        self.document_embedder = document_embedder
        self.query_encoder = query_encoder
        self.repository = repository
        self.file_ids = {}  # 실제 파일 경로 → DB가 반환한 번호
        self.image_vectors = []  # (파일 번호, OpenCLIP 벡터)
        self.text_chunks = []  # ko-SRoBERTa로 인코딩할 본문 청크

    def analyze(self, folder_path):
        folder = Path(folder_path).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError("존재하는 폴더를 선택하세요.")
        if self.file_ids:
            raise ValueError("재분석은 새 서비스로 시작하세요.")

        documents, failures, pending_images = [], [], []
        for file_path in DocumentScanner(str(folder)).scan_files():
            path = Path(file_path)
            # 팀원 로더가 확장자를 보고 이미지·PDF·PPTX 읽기를 선택한다.
            chunks = self.loader.process_file(str(path))
            if not chunks:
                failures.append((path, "읽을 본문이나 이미지가 없습니다."))
                continue

            # 메타데이터를 DB 자료형에 맞추는 것은 내 연결 역할이다.
            try:
                stat = path.stat()
                # 항목 이름을 적어 DB에 어떤 값을 보내는지 바로 보이게 한다.
                info = DocumentInfo(
                    file_path=str(path),
                    file_name=path.name,
                    file_extension=path.suffix.lower(),
                    file_size=stat.st_size,
                    file_hash=sha256(path.read_bytes()).hexdigest(),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            except OSError as error:
                failures.append((path, str(error)))
                continue

            # 모델 오류는 읽기 실패로 숨기지 않고 호출자에게 전달한다.
            vectors = []
            for chunk in chunks:
                if chunk.image is not None:
                    if chunk.chunk_type == 'image':
                        vectors.append(self.image_encoder.encode(chunk.image))
                    else:
                        vectors.append(self.document_encoder.encode(chunk.image))
            self.text_chunks.extend(chunk for chunk in chunks if chunk.text.strip())
            documents.append(info)
            pending_images.append(vectors)

        # 본문은 원본 DocumentEmbedder가 청크 목록을 한 번에 인코딩한다.
        if self.text_chunks:
            self.document_embedder.embed_chunks(self.text_chunks)

        for info, vectors in zip(documents, pending_images):
            file_id = self.repository.save(info)
            self.file_ids[info.file_path] = file_id
            self.image_vectors.extend((file_id, vector) for vector in vectors)
        return documents, failures

    def encode_query(self, query, mode='documents'):
        query = query.strip()
        if not query:
            raise ValueError("검색 문장을 입력하세요.")
        if mode == 'documents':
            return self.document_embedder.model.encode([query])[0]
        if mode == 'images':
            return self.query_encoder.encode_text(query)
        raise ValueError("검색 대상은 documents 또는 images입니다.")

    def search(self, query, top_k=5, mode='documents'):
        query = query.strip()
        if not query or top_k <= 0:
            return []

        if mode == 'documents':
            if not self.text_chunks:
                return []
            # 원본 search는 입력 문장도 같은 ko-SRoBERTa로 인코딩한다.
            hits = self.document_embedder.search(query, top_k=len(self.text_chunks))
            ranked = []
            seen = set()
            for hit in hits:
                file_id = self.file_ids[hit['chunk'].file_path]
                if file_id not in seen:
                    ranked.append((file_id, hit['score']))
                    seen.add(file_id)
            ranked = ranked[:top_k]
        elif mode == 'images':
            if not self.image_vectors:
                return []
            # 임시 이미지 비교: 문장도 이미지와 같은 OpenCLIP 공간으로 바꾼다.
            query_vector = self.encode_query(query, mode='images')
            ranked = search_images(query_vector, self.image_vectors, top_k)
        else:
            raise ValueError("검색 대상은 documents 또는 images입니다.")

        results = []
        for file_id, score in ranked:
            info = self.repository.find_by_id(file_id)
            if info is None:
                raise LookupError(f"DB에 파일 번호 {file_id}가 없습니다.")
            results.append((info, score))
        return results
